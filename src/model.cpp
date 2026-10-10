#include "model.hpp"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstring>
#include <limits>
#include <set>
#include <stdexcept>

#include "calls.hpp"
#include "openvino/openvino.hpp"
#include "snapshots.hpp"

namespace fs = std::filesystem;

// The graph's contract:
//   inputs   input_ids, position_ids [1,T]; attention_bias [1,1,T,W] (0 = may look, -inf = may not);
//            logit_index [K]; past_key.N / past_value.N [1,2,C,128] (cells computed before, W = C + T)
//   outputs  logits [1,K,2] (tokens "0" and "1" at logit_index); present_key.N / present_value.N
//            [1,2,T,128] (the cells of this call)
// One call reads any number of independent blocks: a state (from its cached cells) and its questions,
// each question seeing its state and itself. Blocks are how several questions share one reading of
// a state, how a state asked again resumes from its snapshot, how a long state is read in pieces, and
// how requests arriving together share one call.
struct Model::Impl {
    // Keys/values of consecutive cells, one buffer per graph input, laid out as the input: [heads][count][dim].
    struct Cells {
        std::vector<std::vector<float>> kv;
        size_t count = 0;
    };
    using Index = SnapshotIndex<Cells>;  // a snapshot's payload: the state's cells
    // One block of a call: the first `past_n` cells of `past`, `shared` state tokens read now (positions
    // from `shared_pos`, causal), then questions (their tokens from `skip` on) as a prefix tree
    // (tree.hpp): each question sees the block's cells, its shared tokens and its own tokens, the ones it
    // has in common with other questions read once. No questions: the logits are read at the last shared
    // token.
    struct Block {
        const Cells* past = nullptr;
        size_t past_n = 0;
        Tokens shared;
        size_t shared_pos = 0;
        std::vector<const Tokens*> pieces;
        size_t skip = 0;
        size_t row = 0;  // set by run(): where `shared` starts in the call
    };

    fs::path dir;
    ov::Core core;
    size_t kv_heads = 0, head_dim = 0;
    std::vector<std::string> kv_names, present_names;
    Index snaps;
    std::vector<bool> seen;  // call lengths T already run: their kernels exist
    std::atomic<size_t> batched{0};
    size_t quantization_group;
    std::string hint;
    int streams;
    ov::CompiledModel compiled;
    ov::InferRequest req;

    Impl(const fs::path& d, int threads, const std::string& hint, int streams, size_t snapshots, size_t snapshot_tokens, size_t quantization_group)
        : dir(d), snaps(snapshots, snapshot_tokens), seen(PIECE_TOKENS + 1, false), quantization_group(quantization_group), hint(hint), streams(streams) {
        auto graph = core.read_model((dir / "openvino_model.xml").string());
        std::set<std::string> names;
        for (auto& in : graph->inputs())
            for (auto& n : in.get_names()) names.insert(n);
        auto refuse = [&](const std::string& why) {
            throw std::runtime_error(dir.string() + ": " + why + "; write the model with export/export_openvino.py");
        };
        for (const char* need : {"input_ids", "position_ids", "attention_bias", "logit_index"})
            if (!names.count(need)) refuse(std::string("no input '") + need + "'");
        if (!graph->get_sinks().empty()) refuse("a stateful graph (its cache kernel costs 3-4x per token when resuming)");
        for (auto& n : names) {
            if (n.rfind("past_key.", 0) == 0 || n.rfind("past_value.", 0) == 0) kv_names.push_back(n);
            else if (n != "input_ids" && n != "position_ids" && n != "attention_bias" && n != "logit_index") refuse("an input this server does not feed: '" + n + "'");
        }
        if (kv_names.empty()) refuse("no past_key.N / past_value.N inputs");
        std::sort(kv_names.begin(), kv_names.end());
        // cells' layout from the graph: past_*.N are [1, kv heads, cells, head dim]
        for (auto& in : graph->inputs()) {
            if (!in.get_names().count(kv_names[0])) continue;
            auto ps = in.get_partial_shape();
            if (ps.rank().get_length() != 4 || ps[1].is_dynamic() || ps[3].is_dynamic()) refuse("past inputs are not [1, heads, cells, dim]");
            kv_heads = static_cast<size_t>(ps[1].get_length());
            head_dim = static_cast<size_t>(ps[3].get_length());
        }
        for (auto& n : kv_names) present_names.push_back("present_" + n.substr(5));  // past_key.N -> present_key.N
        // PERFORMANCE_HINT/NUM_STREAMS are the released defaults (--hint latency, --streams 1); throughput
        // and streams > 1 share a call's work: more decisions a second under concurrent load, slower single
        // requests.
        ov::AnyMap cfg = {{"PERFORMANCE_HINT", hint}, {"NUM_STREAMS", std::to_string(streams)}, {"INFERENCE_NUM_THREADS", threads},
                          // Activations quantized to INT8 in groups of quantization_group values (0: kept f32).
                          // 128 rather than 32: -17% on one question, the same accuracy on the 999 set (0.758 vs
                          // 0.759; mean |dP| 0.008). 256 saves 3% more, max |dP| 0.29.
                          {"DYNAMIC_QUANTIZATION_GROUP_SIZE", quantization_group},
                          // f32 activations on every CPU. Left to OpenVINO, the precision follows the CPU: f16 on
                          // ARM, bf16 where AVX512-BF16 or AMX exist; f16 moved a 5,000-token state's answer by 0.44.
                          {"INFERENCE_PRECISION_HINT", "f32"}};
        compiled = core.compile_model(graph, "CPU", cfg);
        req = compiled.create_infer_request();
    }

    std::vector<std::vector<double>> score_batch(const std::vector<const ScoreRequest*>& reqs) {
        std::vector<std::vector<double>> out(reqs.size());
        if (reqs.size() == 1) {
            out[0] = score_one(*reqs[0]);
            return out;
        }
        // Requests the scheduler found to fit one call together: one block each, from its own snapshot.
        batched += reqs.size();
        std::vector<Block> blocks;
        std::vector<std::pair<size_t, size_t>> span(reqs.size());  // blocks of each request
        for (size_t r = 0; r < reqs.size(); ++r) {
            span[r].first = blocks.size();
            const ScoreRequest& q = *reqs[r];
            if (q.prefix.empty()) {
                for (auto& j : q.jobs) blocks.push_back(alone(j.tokens));
            } else {
                size_t c = 0;
                const Index::Entry* from = snaps.find(q.prefix, c);
                std::vector<size_t> all(q.jobs.size());
                for (size_t i = 0; i < all.size(); ++i) all[i] = i;
                blocks.push_back(state_block(from ? &from->payload : nullptr, c, q.prefix, c, q.prefix.size(), q.jobs, all));
            }
            span[r].second = blocks.size();
        }
        auto ps = run(blocks);
        std::vector<std::pair<Tokens, Cells>> fresh;  // added after the loop: entries in use until then
        size_t k = 0;
        for (size_t r = 0; r < reqs.size(); ++r) {
            for (size_t b = span[r].first; b < span[r].second; ++b)
                for (size_t n = std::max<size_t>(1, blocks[b].pieces.size()); n; --n) out[r].push_back(ps[k++]);
            const ScoreRequest& q = *reqs[r];
            if (q.prefix.empty()) continue;
            Tokens state(q.prefix.begin(), q.prefix.begin() + q.state);
            bool queued = std::any_of(fresh.begin(), fresh.end(), [&](const auto& f) { return f.first == state; });
            if (!queued && snaps.wants(state)) fresh.emplace_back(std::move(state), first(extend(blocks[span[r].first]), q.state));
        }
        for (auto& [tokens, cells] : fresh) snaps.add(std::move(tokens), std::move(cells));
        return out;
    }

    static Block alone(const Tokens& t) {  // a whole prompt, nothing shared
        Block b;
        b.shared = t;
        return b;
    }

    // The state from cell `pos` to `end` plus the questions `qs`: positions continue the state's.
    static Block state_block(const Cells* past, size_t past_n, const Tokens& prefix, size_t pos, size_t end, const std::vector<Job>& jobs,
                             const std::vector<size_t>& qs) {
        Block b;
        b.past = past;
        b.past_n = past_n;
        b.shared.assign(prefix.begin() + pos, prefix.begin() + end);
        b.shared_pos = pos;
        b.skip = prefix.size();
        for (size_t i : qs) b.pieces.push_back(&jobs[i].tokens);
        return b;
    }

    // One request in the calls of plan_calls, each block from the state's cells read so far: its
    // snapshot's, then those of every call that read a piece of the state (the mask stays small, and
    // the attention skips what the causal mask would hide anyway).
    std::vector<double> score_one(const ScoreRequest& q) {
        if (q.prefix.empty()) {  // no state boundary known: every prompt alone
            std::vector<double> out;
            for (auto& j : q.jobs) {
                std::vector<Block> one{alone(j.tokens)};
                out.push_back(run(one)[0]);
            }
            return out;
        }
        const Tokens& prefix = q.prefix;
        const size_t P = prefix.size();
        size_t c = 0;
        const Index::Entry* sn = snaps.find(prefix, c);
        const Cells* start = sn ? &sn->payload : nullptr;
        const Cells* cur = start;  // holds at least the cells before the next call's state piece
        Cells state;
        std::vector<const Tokens*> prompts;
        for (auto& j : q.jobs) prompts.push_back(&j.tokens);
        std::vector<double> out(q.jobs.size());
        for (const Call& call : plan_calls(c, P, prompts, PIECE_TOKENS, CALL_TOKENS, q.jobs.size())) {
            std::vector<Block> one{state_block(cur, call.state_from, prefix, call.state_from, call.state_to, q.jobs, call.questions)};
            auto ps = run(one);
            for (size_t s = 0; s < call.questions.size(); ++s) out[call.questions[s]] = ps[s];
            if (call.state_to > call.state_from) {
                state = extend(one[0]);
                cur = &state;
            }
        }
        // A snapshot of the state unless it is the one we started from (find refreshed that one); of the
        // state only: the rest of the prefix is this request's questions.
        if (cur != start) {
            Tokens kept(prefix.begin(), prefix.begin() + q.state);
            if (snaps.wants(kept)) snaps.add(std::move(kept), first(std::move(state), q.state));
        }
        return out;
    }

    // The first n of the cells.
    Cells first(Cells cells, size_t n) {
        if (n >= cells.count) return cells;
        Cells out;
        out.count = n;
        out.kv.resize(cells.kv.size());
        for (size_t k = 0; k < cells.kv.size(); ++k) {
            out.kv[k].resize(kv_heads * n * head_dim);
            for (size_t h = 0; h < kv_heads; ++h)
                std::memcpy(out.kv[k].data() + h * n * head_dim, cells.kv[k].data() + h * cells.count * head_dim, n * head_dim * sizeof(float));
        }
        return out;
    }

    // Block b's cells after the last call: its first past_n cells, then its shared tokens' new cells.
    Cells extend(const Block& b) {
        Cells out;
        size_t n = b.past_n, s = b.shared.size();
        out.count = n + s;
        out.kv.resize(kv_names.size());
        for (size_t k = 0; k < kv_names.size(); ++k) {
            ov::Tensor pr = req.get_tensor(present_names[k]);  // [1, heads, T, dim]
            size_t T = pr.get_shape()[2];
            const float* src = pr.data<float>();
            out.kv[k].resize(kv_heads * out.count * head_dim);
            for (size_t h = 0; h < kv_heads; ++h) {
                float* dst = out.kv[k].data() + h * out.count * head_dim;
                if (n) std::memcpy(dst, b.past->kv[k].data() + h * b.past->count * head_dim, n * head_dim * sizeof(float));
                std::memcpy(dst + n * head_dim, src + (h * T + b.row) * head_dim, s * head_dim * sizeof(float));
            }
        }
        return out;
    }

    // One call over `blocks`: P(yes) per question in block order (one per block without questions).
    std::vector<double> run(std::vector<Block>& blocks) {
        size_t C = 0, T = 0, K = 0;
        std::vector<PromptTree> trees;
        for (auto& b : blocks) {
            C += b.past_n;
            b.row = T;
            trees.push_back(b.pieces.empty() ? PromptTree{} : prompt_tree(b.pieces, b.skip));
            T += b.shared.size() + trees.back().tokens;
            K += std::max<size_t>(1, b.pieces.size());
        }
        size_t W = C + T;
        ov::Tensor ids(ov::element::i64, {1, T}), pos(ov::element::i64, {1, T}), bias(ov::element::f32, {1, 1, T, W}),
            index(ov::element::i64, {K});
        int64_t* pi = ids.data<int64_t>();
        int64_t* pp = pos.data<int64_t>();
        int64_t* px = index.data<int64_t>();
        float* pb = bias.data<float>();
        std::fill(pb, pb + T * W, -std::numeric_limits<float>::infinity());
        size_t c0 = 0, k = 0;
        for (size_t bi = 0; bi < blocks.size(); ++bi) {
            Block& b = blocks[bi];
            const PromptTree& tree = trees[bi];
            size_t S = b.shared.size(), at = b.row;
            auto open = [&](size_t row, size_t from, size_t to) { std::fill(pb + row * W + from, pb + row * W + to, 0.0f); };
            for (size_t j = 0; j < S; ++j) {
                pi[at + j] = b.shared[j];
                pp[at + j] = static_cast<int64_t>(b.shared_pos + j);
                open(at + j, c0, c0 + b.past_n);                 // the block's cached cells
                open(at + j, C + at, C + at + j + 1);             // its shared tokens, causally
            }
            std::vector<size_t> node_row(tree.nodes.size());
            size_t r = at + S;
            for (size_t n = 0; n < tree.nodes.size(); ++n) {
                const TreeNode& node = tree.nodes[n];
                const Tokens& p = *b.pieces[node.prompt];
                node_row[n] = r;
                for (size_t j = 0; j < node.to - node.from; ++j) {
                    pi[r + j] = p[node.from + j];
                    pp[r + j] = static_cast<int64_t>(node.from + j);
                    open(r + j, c0, c0 + b.past_n);
                    open(r + j, C + at, C + at + S);             // the state read in this call
                    for (size_t a = node.parent; a != TreeNode::NO_PARENT; a = tree.nodes[a].parent)
                        open(r + j, C + node_row[a], C + node_row[a] + tree.nodes[a].to - tree.nodes[a].from);  // what it shares
                    open(r + j, C + r, C + r + j + 1);            // itself, causally
                }
                r += node.to - node.from;
            }
            for (size_t q = 0; q < b.pieces.size(); ++q) px[k++] = static_cast<int64_t>(node_row[tree.leaf[q]]);  // a leaf is one token
            if (b.pieces.empty()) px[k++] = static_cast<int64_t>(at + S - 1);
            c0 += b.past_n;
        }
        req.set_tensor("input_ids", ids);
        req.set_tensor("position_ids", pos);
        req.set_tensor("attention_bias", bias);
        req.set_tensor("logit_index", index);
        for (size_t kk = 0; kk < kv_names.size(); ++kk) req.set_tensor(kv_names[kk], past_tensor(blocks, kk, C));
        req.infer();
        if (T < seen.size()) seen[T] = true;
        const float* lg = req.get_tensor("logits").data<float>();  // [1, K, 2]: logits of "0" and "1"
        std::vector<double> ps(K);
        for (size_t j = 0; j < K; ++j) ps[j] = 1.0 / (1.0 + std::exp(static_cast<double>(lg[2 * j]) - static_cast<double>(lg[2 * j + 1])));
        return ps;
    }

    // Input `k`'s cached cells of every block, one after the other: [1, heads, C, dim]. A single block
    // using all of its buffer is handed over as it is (the layout is the input's).
    ov::Tensor past_tensor(const std::vector<Block>& blocks, size_t k, size_t C) {
        ov::Shape shape{1, kv_heads, C, head_dim};
        if (blocks.size() == 1 && C && blocks[0].past_n == blocks[0].past->count)
            return ov::Tensor(ov::element::f32, shape, const_cast<float*>(blocks[0].past->kv[k].data()));
        ov::Tensor t(ov::element::f32, shape);
        float* dst = t.data<float>();
        for (size_t h = 0; h < kv_heads; ++h) {
            size_t at = 0;
            for (auto& b : blocks) {
                if (!b.past_n) continue;
                std::memcpy(dst + (h * C + at) * head_dim, b.past->kv[k].data() + h * b.past->count * head_dim, b.past_n * head_dim * sizeof(float));
                at += b.past_n;
            }
        }
        return t;
    }
};

Model::Model(const fs::path& dir, int threads, const std::string& hint, int streams, size_t snapshots, size_t snapshot_tokens, size_t quantization_group)
    : impl_(std::make_unique<Impl>(dir, threads, hint, streams, snapshots, snapshot_tokens, quantization_group)) {}
Model::~Model() = default;

std::vector<std::vector<double>> Model::score_batch(const std::vector<const ScoreRequest*>& reqs) { return impl_->score_batch(reqs); }

bool Model::is_warm(size_t n) const { return n < impl_->seen.size() && impl_->seen[n]; }

void Model::warm_length(size_t n) {
    Tokens t(n, 0);
    for (size_t i = 0; i < n; ++i) t[i] = static_cast<int32_t>(1000 + i % 20000);
    score(ScoreRequest{{}, {Job{"w", t}}});
}

void Model::warmup() {
    for (int i = 0; i < 3; ++i) warm_length(24);
}

ojson Model::describe() const {
    const Impl& m = *impl_;
    ojson e = {{"runtime", "openvino"}, {"version", openvino_version()}, {"device", "cpu"}, {"model_dir", m.dir.string()},
               {"dynamic_quantization", m.quantization_group}, {"performance_hint", m.hint}, {"streams", m.streams}};
    e["state_snapshots"] = m.snaps.stats();
    e["state_snapshots"]["bytes"] = m.snaps.kept_tokens() * m.kv_names.size() * m.kv_heads * m.head_dim * sizeof(float);
    e["batched_requests"] = m.batched.load();
    return e;
}

std::string Model::openvino_version() { return ov::get_openvino_version().buildNumber; }
