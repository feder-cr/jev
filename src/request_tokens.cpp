#include "request_tokens.hpp"

#include <algorithm>
#include <atomic>
#include <thread>

#include "prompt.hpp"

static const size_t PARALLEL_TOKENIZE_BYTES = 64 * 1024;  // below it, threads cost more than they save

RequestTokens tokenize_request(const Vocab& vocab, const std::string& state_text, const std::vector<std::string>& instructions) {
    const size_t n = instructions.size();
    std::vector<Tokens> tokens(n + 1);  // the prompts, then the state alone
    auto work = [&](size_t i) {
        tokens[i] = vocab.tokenize(i < n ? binary_prompt(vocab.bos(), state_text, instructions[i]) : vocab.bos() + state_text);
    };
    size_t workers = std::min<size_t>(tokens.size(), std::max(1u, std::thread::hardware_concurrency()));
    if (workers > 1 && state_text.size() * tokens.size() > PARALLEL_TOKENIZE_BYTES) {
        std::atomic<size_t> next{0};
        std::vector<std::thread> pool;
        for (size_t w = 0; w < workers; ++w)
            pool.emplace_back([&] { for (size_t i; (i = next++) < tokens.size();) work(i); });
        for (auto& t : pool) t.join();
    } else {
        for (size_t i = 0; i < tokens.size(); ++i) work(i);
    }
    RequestTokens out;
    out.prefix = std::move(tokens.back());
    tokens.pop_back();
    if (!out.prefix.empty()) out.prefix.pop_back();
    for (auto& t : tokens) {
        size_t k = 0;
        while (k < out.prefix.size() && k < t.size() && out.prefix[k] == t[k]) ++k;
        out.prefix.resize(k);
    }
    for (auto& t : tokens) if (t.size() <= out.prefix.size()) out.prefix.clear();
    out.prompts = std::move(tokens);
    return out;
}
