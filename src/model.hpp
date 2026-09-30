// The model: jevos on the CPU through OpenVINO (INT8 weights), running the graph export/export_openvino.py
// writes. Token ids in, P(yes) = sigmoid(l1 - l0) out, from the logits of the answer tokens "1" and "0".
#pragma once
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

#include "json.hpp"
#include "tokens.hpp"

using ojson = nlohmann::ordered_json;  // insertion order: Python's default

class Model {
public:
    // How requests are split into calls (plan_calls), measured against one call of up to 2048 tokens.
    // The CPU plugin decomposes a stateless attention into dense matmuls (ov::pass::CommonOptimizations
    // decomposes every ScaledDotProductAttention its KV-cache fusion did not take), so a call's attention
    // costs its tokens times its cells whatever the mask hides. Questions go in calls of up to CALL_TOKENS:
    // 80 questions on a state (1750 tokens) -12 to -17%; up to ~1000 tokens one call, as before (512
    // gained more at 1750 tokens but lost 13% at 550: a small last call pays a call's fixed cost). A long
    // state is read in pieces of PIECE_TOKENS: smaller pieces copy its cells more often (a 5000-token state:
    // +20% at 512, the same at 1024-2048). Requests read together fit CALL_TOKENS in all.
    static constexpr size_t CALL_TOKENS = 1024;
    static constexpr size_t PIECE_TOKENS = 2048;
    // Lengths worth warming while idle (the CPU plugin builds kernels per input shape, 3-10 ms the first
    // time a length runs): at 384 tokens that is under 5% of the call, and a request arriving during a
    // warm-up call waits under ~0.2 s.
    static constexpr size_t WARM_TOKENS = 384;

    // `dir` holds openvino_model.xml/.bin; `snapshots` states of at most `snapshot_tokens` tokens in all
    // are kept for later requests (0 = none). Activations are quantized to INT8 in groups of
    // `quantization_group` values (0 = kept f32: slower, and an answer no longer moves, in its last digits,
    // with how a call is composed).
    Model(const std::filesystem::path& dir, int threads, size_t snapshots, size_t snapshot_tokens, size_t quantization_group);
    ~Model();
    Model(const Model&) = delete;
    Model& operator=(const Model&) = delete;

    // P(yes) per job of each request. Several requests are read in one call (the scheduler hands over
    // only requests that fit CALL_TOKENS together); a request's prefix is its state (empty: none known).
    std::vector<std::vector<double>> score_batch(const std::vector<const ScoreRequest*>& reqs);
    std::vector<double> score(const ScoreRequest& r) { return score_batch({&r})[0]; }

    bool is_warm(size_t n) const;  // a call of `n` tokens has run already: its kernels exist
    void warm_length(size_t n);    // a throwaway prompt of `n` tokens
    void warmup();                 // the first calls pay for allocations and thread start-up
    ojson describe() const;        // the `engine` object of /health; counters only, safe beside the model thread

    static std::string openvino_version();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
