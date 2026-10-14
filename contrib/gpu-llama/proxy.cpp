// jevos-v4 on the GPU: jev's /v1/systemone wire format served from a GGUF through llama.cpp.
//
// The wire layer (validation, prompt rendering, tokenization, answer math, response shape, usage)
// is jev's own code: wire.cpp, prompt.hpp, request_tokens.cpp, choice.hpp, score.hpp, pyjson.hpp.
// Only the scoring backend differs from jev: instead of OpenVINO's answer-head graph, each binary
// job is one llama.cpp decode of the state prefix plus the job's own tokens, and P(yes) is read
// from the logits of the answer tokens "0" and "1" at the last position:
//     P = sigmoid(logit("1") - logit("0"))
// exactly as jev's served OpenVINO graph does with its 2-row answer head.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

#include "httplib.h"

#include "errors.hpp"
#include "pyjson.hpp"
#include "text.hpp"
#include "prompt.hpp"
#include "wire.hpp"
#include "choice.hpp"
#include "score.hpp"
#include "vocab.hpp"
#include "request_tokens.hpp"

#include "llama.h"

static const size_t CTX = 8192;
static const char* SERVED = "jevos-v4";
static const char* ALIAS_PREFIX = "jev-";

// ---------------------------------------------------------------- llama scoring

struct LlamaScorer {
    llama_model* model = nullptr;
    llama_context* ctx = nullptr;
    const llama_vocab* vocab_ll = nullptr;
    llama_token t0 = -1, t1 = -1;  // the answer tokens "0" and "1"
    std::mutex mu;                 // one context: serve requests one at a time

    LlamaScorer(const std::string& gguf_path) {
        llama_backend_init();
        llama_model_params mp = llama_model_default_params();
        mp.n_gpu_layers = 99;
        model = llama_model_load_from_file(gguf_path.c_str(), mp);
        if (!model) throw std::runtime_error("cannot load " + gguf_path);
        vocab_ll = llama_model_get_vocab(model);
        llama_context_params cp = llama_context_default_params();
        cp.n_ctx = CTX;
        cp.n_batch = CTX;
        cp.n_ubatch = 2048;
        ctx = llama_init_from_model(model, cp);
        if (!ctx) throw std::runtime_error("cannot create the llama context");
        // the answer tokens must each be a single token, as the OpenVINO export asserts
        for (const char* d : {"0", "1"}) {
            llama_token tmp[4];
            int k = llama_tokenize(vocab_ll, d, 1, tmp, 4, false, true);
            if (k != 1) throw std::runtime_error(std::string("the answer digit '") + d + "' is not one token");
            if (d[0] == '0') t0 = tmp[0]; else t1 = tmp[0];
        }
    }

    ~LlamaScorer() {
        if (ctx) llama_free(ctx);
        if (model) llama_model_free(model);
    }

    // P(yes) for every job of one request: the shared prefix is decoded once, each job then reads
    // its own tokens on top of it (llama.cpp rolls the cache back, so every job sees the state and
    // itself alone, as jev's attention mask does).
    std::vector<double> score(const RequestTokens& rt) {
        std::lock_guard<std::mutex> lk(mu);
        llama_memory_t mem = llama_get_memory(ctx);
        llama_memory_clear(mem, true);
        std::vector<double> ps(rt.prompts.size());
        if (!rt.prefix.empty()) {
            llama_batch b = llama_batch_get_one(const_cast<llama_token*>(rt.prefix.data()), (int) rt.prefix.size());
            if (llama_decode(ctx, b)) throw std::runtime_error("llama_decode failed on the shared prefix");
        }
        for (size_t i = 0; i < rt.prompts.size(); ++i) {
            const Tokens& t = rt.prompts[i];
            const llama_token* suffix = t.data() + rt.prefix.size();
            int n = (int) (t.size() - rt.prefix.size());
            llama_batch b = llama_batch_get_one(const_cast<llama_token*>(suffix), n);
            if (llama_decode(ctx, b)) throw std::runtime_error("llama_decode failed on a question");
            const float* lg = llama_get_logits_ith(ctx, -1);
            double z = (double) lg[t1] - (double) lg[t0];
            ps[i] = 1.0 / (1.0 + std::exp(-z));
            if (i + 1 < rt.prompts.size() && !rt.prefix.empty())
                llama_memory_seq_rm(mem, 0, rt.prefix.size(), -1);
        }
        return ps;
    }

    void warmup() {
        RequestTokens rt;
        Tokens warm = rt.prefix;
        std::string text = "warmup";
        Tokens t;
        t.resize(text.size() + 8);
        int n = llama_tokenize(vocab_ll, text.data(), (int) text.size(), t.data(), (int) t.size(), false, true);
        t.resize(n);
        rt.prompts.push_back(t);
        score(rt);
    }
};

// ---------------------------------------------------------------- the request pipeline
// Everything below mirrors jev's src/server.cpp systemone(): the same prompt construction, the same
// answer assembly, the same usage count, the same response bytes.

static void add_prompts(const std::vector<NativeQuestion>& qs, std::vector<size_t>& question_of, std::vector<std::string>& instructions) {
    for (size_t k = 0; k < qs.size(); ++k) {
        if (qs[k].kind == "boolean") {
            question_of.push_back(k);
            instructions.push_back(qs[k].instructions);
            continue;
        }
        std::vector<std::string> described;
        for (auto& [field, text] : qs[k].texts) described.push_back(text);
        if (qs[k].kind == "choice")
            for (auto& phrasing : CHOICE_PHRASINGS)
                for (size_t i = 0; i < described.size(); ++i) {
                    question_of.push_back(k);
                    instructions.push_back(choice_instructions(qs[k].instructions, described, i, phrasing));
                }
        else
            for (auto& phrasing : SCORE_PHRASINGS)
                for (size_t i = 1; i < described.size(); ++i) {
                    question_of.push_back(k);
                    instructions.push_back(score_instructions(qs[k].instructions, described, i, phrasing));
                }
    }
}

int main(int argc, char** argv) {
    std::string gguf_path, host = "127.0.0.1";
    int port = 8153;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto next = [&]() { return std::string(argv[++i]); };
        if (a == "--model") gguf_path = next();
        else if (a == "--port") port = std::stoi(next());
        else if (a == "--host") host = next();
        else { fprintf(stderr, "unknown arg %s\n", a.c_str()); return 1; }
    }
    if (gguf_path.empty()) { fprintf(stderr, "usage: %s --model MODEL.gguf [--port N] [--host H]\n", argv[0]); return 1; }

    Vocab vocab(gguf_path);        // the tokenizer, as jev reads it from the GGUF
    LlamaScorer scorer(gguf_path); // the model, on the GPU
    scorer.warmup();

    httplib::Server svr;
    svr.new_task_queue = [] { return new httplib::ThreadPool(4); };

    svr.Get("/health", [](const httplib::Request&, httplib::Response& res) {
        res.set_content("{\"status\":\"ok\"}", "application/json");
    });

    svr.Post("/v1/systemone", [&](const httplib::Request& req, httplib::Response& res) {
        Value body;
        try {
            body = pyjson::loads(req.body);
        } catch (const pyjson::DecodeError& e) {
            res.status = 422;
            res.set_content("{\"error\":[{\"type\":\"json_invalid\",\"loc\":[\"body\"],\"msg\":\"JSON decode error\",\"input\":{}}]}", "application/json");
            return;
        } catch (const pyjson::BodyError&) {
            res.status = 400;
            res.set_content("{\"error\":[{\"type\":\"body_error\",\"loc\":[\"body\"],\"msg\":\"Invalid body\"}]}", "application/json");
            return;
        }
        Errs errs;
        check_wire(body, errs);
        if (errs.empty()) {
            const Value* model = body.get("model");
            const std::string& requested = model->s;
            if (!(requested == SERVED || requested.rfind(ALIAS_PREFIX, 0) == 0))
                errs.push_back(app_err({S("body"), S("model")}, std::string("Unknown model ") + pyjson::str_repr(requested) + ": this server answers as " + SERVED));
        }
        if (errs.empty()) {
            std::vector<NativeQuestion> qs;
            for (auto& [qid, q] : body.get("questions")->dict) qs.push_back(to_native(qid, q));
            check_native(*body.get("state"), qs, errs);
            if (errs.empty()) {
                try {
                    auto answered = [&]() -> std::string {
                        std::vector<size_t> question_of;
                        std::vector<std::string> instructions;
                        add_prompts(qs, question_of, instructions);
                        std::string state_text = render_state(*body.get("state"));
                        for (auto& in : instructions)
                            if (size_t n = vocab.tokenize(binary_prompt(vocab.bos(), state_text, in)).size(); n > CTX)
                                throw unprocessable(app_err({S("body")}, "Prompt is " + std::to_string(n) + " tokens, over the context limit " + std::to_string(CTX)));
                        RequestTokens rt = tokenize_request(vocab, state_text, instructions);
                        for (auto& t : rt.prompts)
                            if (t.size() > CTX) throw unprocessable(app_err({S("body")}, "Prompt is " + std::to_string(t.size()) + " tokens, over the context limit " + std::to_string(CTX)));
                        std::vector<double> ps = scorer.score(rt);

                        // usage counts the shared state once, as the Python server does
                        size_t compiled = 0, shared = rt.prompts.size() > 1 ? rt.state : 0;
                        for (auto& j : rt.prompts) compiled += j.size();

                        std::vector<std::vector<double>> answered(qs.size());
                        for (size_t i = 0; i < ps.size(); ++i) answered[question_of[i]].push_back(ps[i]);

                        std::string out = "{\"model\":";
                        pyjson::quote(out, SERVED);
                        out += ",\"answers\":{";
                        for (size_t k = 0; k < qs.size(); ++k) {
                            if (k) out += ",";
                            pyjson::quote(out, qs[k].id);
                            if (qs[k].kind == "boolean") {
                                out += ":{\"type\":\"noul\",\"noul\":" + pyjson::float_repr(answered[k][0]) + "}";
                                continue;
                            }
                            if (qs[k].kind == "score") {
                                const std::vector<std::string>& legend = qs[k].legend;
                                ScoreAnswer a = rate(answered[k], legend.size());
                                out += ":{\"type\":\"score\",\"score\":" + pyjson::float_repr(a.score) + ",\"legend\":{";
                                for (size_t i = 0; i < legend.size(); ++i) out += (i ? ",\"" : "\"") + std::to_string(i) + "\":" + legend[i];
                                out += "},\"probabilities\":{";
                                for (size_t i = 0; i < legend.size(); ++i) out += (i ? ",\"" : "\"") + std::to_string(i) + "\":" + pyjson::float_repr(a.probabilities[i]);
                                out += "},\"confidence\":" + pyjson::float_repr(a.confidence) + "}";
                                continue;
                            }
                            const std::vector<std::string>& options = qs[k].options;
                            ChoiceAnswer a = choose(answered[k], options.size());
                            out += ":{\"type\":\"choice\",\"choice\":";
                            pyjson::quote(out, options[a.best]);
                            out += ",\"probabilities\":{";
                            for (size_t i = 0; i < options.size(); ++i) {
                                if (i) out += ",";
                                pyjson::quote(out, options[i]);
                                out += ":" + pyjson::float_repr(a.probabilities[i]);
                            }
                            out += "},\"confidence\":" + pyjson::float_repr(a.confidence) + "}";
                        }
                        out += "},\"usage\":{\"input_tokens\":" + std::to_string(compiled - shared * (rt.prompts.size() - 1)) + ",\"output_tokens\":0}}";
                        return out;
                    }();
                    res.set_content(answered, "application/json");
                    return;
                } catch (const ApiError& e) {
                    res.status = e.status;
                    res.set_content(error_body(e), "application/json");
                    return;
                }
            }
        }
        res.status = 422;
        res.set_content(error_body(unprocessable(std::move(errs))), "application/json");
    });

    fprintf(stderr, "jevos-gpu listening on http://%s:%d (model: %s)\n", host.c_str(), port, gguf_path.c_str());
    if (!svr.listen(host.c_str(), port)) { fprintf(stderr, "cannot bind\n"); return 1; }
    return 0;
}
