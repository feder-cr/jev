// States kept across requests (after colibri's brio mode), matched by token ids: a request resumes from
// the entry sharing the longest prefix with its state (at least MIN_TOKENS) and reads only the rest.
// Least recently used entries go when the count or the total of state tokens would exceed its limits.
// What an entry holds is the model's (its cells); entries keep their address while they live: the model
// holds pointers to them during calls.
#pragma once
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <memory>
#include <vector>

#include "json.hpp"
#include "tokens.hpp"

template <class Payload>
class SnapshotIndex {
public:
    static constexpr size_t MIN_TOKENS = 32;
    struct Entry {
        Tokens tokens;
        Payload payload;
        uint64_t used;
    };

    SnapshotIndex(size_t max_count, size_t max_tokens) : max_count_(max_count), max_tokens_(max_count ? max_tokens : 0) {}
    bool enabled() const { return max_count_ > 0; }

    // The entry sharing the longest prefix with `prefix`, and that length; null below MIN_TOKENS.
    Entry* find(const Tokens& prefix, size_t& common) {
        Entry* best = nullptr;
        common = 0;
        for (auto& e : entries_) {
            size_t n = 0, m = std::min(e->tokens.size(), prefix.size());
            while (n < m && e->tokens[n] == prefix[n]) ++n;
            if (n > common) { common = n; best = e.get(); }
        }
        if (common < MIN_TOKENS) { common = 0; best = nullptr; }
        if (best) { best->used = ++tick_; hits_++; reused_ += common; } else misses_++;
        return best;
    }

    // Whether a state is worth keeping and not kept yet (a kept one is refreshed instead).
    bool wants(const Tokens& state) {
        if (!enabled() || state.size() < MIN_TOKENS || state.size() > max_tokens_) return false;
        for (auto& e : entries_)
            if (e->tokens == state) { e->used = ++tick_; return false; }
        return true;
    }

    // Keeps a state, evicting least recently used entries until it fits.
    void add(Tokens tokens, Payload payload) {
        while (!entries_.empty() && (entries_.size() >= max_count_ || kept_ + tokens.size() > max_tokens_)) {
            auto lru = std::min_element(entries_.begin(), entries_.end(), [](const auto& a, const auto& b) { return a->used < b->used; });
            kept_ -= (*lru)->tokens.size();
            entries_.erase(lru);
        }
        kept_ += tokens.size();
        entries_.push_back(std::make_unique<Entry>(Entry{std::move(tokens), std::move(payload), ++tick_}));
        count_ = entries_.size();
        kept_tokens_ = kept_;
    }

    nlohmann::ordered_json stats() const {  // counters only: /health reads them beside the model thread
        return {{"kept", count_.load()}, {"max", max_count_}, {"tokens", kept_tokens_.load()}, {"max_tokens", max_tokens_},
                {"hits", hits_.load()}, {"misses", misses_.load()}, {"reused_tokens", reused_.load()}};
    }
    size_t kept_tokens() const { return kept_tokens_.load(); }

private:
    size_t max_count_, max_tokens_, kept_ = 0;
    uint64_t tick_ = 0;
    std::vector<std::unique_ptr<Entry>> entries_;
    std::atomic<size_t> hits_{0}, misses_{0}, reused_{0}, count_{0}, kept_tokens_{0};
};
