// How a request is split into model calls (plan_calls). Nothing here knows about the model.
#pragma once
#include <algorithm>
#include <cstdint>
#include <vector>

#include "tree.hpp"

// One model call of a request: the state tokens [state_from, state_to) it reads and the questions (jobs)
// it answers.
struct Call {
    size_t state_from = 0, state_to = 0;
    std::vector<size_t> questions;
};

// The prompts all start with the same P tokens (the state, and what else they share), read from `from`
// on (the cells before come from a snapshot); after them, each call reads its questions as a prefix tree
// (tree.hpp), so a question costs only what it does not share with the others in its call. While the
// rest of the state and the cheapest question do not fit `call_budget`, a piece of at most
// `piece_budget` state tokens goes alone; the call with the state's last piece takes questions in order
// while they fit `call_budget`, the next calls the others, at most `max_count` each. A question longer
// than the budget has a call of its own.
inline std::vector<Call> plan_calls(size_t from, size_t P, const std::vector<const Tokens*>& prompts, size_t piece_budget, size_t call_budget,
                                    size_t max_count) {
    std::vector<Call> calls;
    size_t pos = from;
    size_t cheapest = prompts.empty() ? 0 : SIZE_MAX;
    for (auto* p : prompts) cheapest = std::min(cheapest, p->size() - P);
    while (pos < P && P - pos + cheapest > call_budget) {
        size_t n = std::min(piece_budget, P - pos);
        calls.push_back({pos, pos + n, {}});
        pos += n;
    }
    for (size_t k = 0; k < prompts.size();) {
        Call call{pos, P, {}};
        size_t used = P - pos;
        while (k < prompts.size()) {
            size_t cost = added_tokens(prompts, call.questions, k, P);
            if (!call.questions.empty() && (call.questions.size() >= max_count || used + cost > call_budget)) break;
            used += cost;
            call.questions.push_back(k++);
        }
        calls.push_back(std::move(call));
        pos = P;
    }
    if (prompts.empty() && pos < P) calls.push_back({pos, P, {}});
    return calls;
}
