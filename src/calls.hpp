// How a request is split into model calls (plan_calls). Nothing here knows about the model.
#pragma once
#include <algorithm>
#include <vector>

// One model call of a request: the state tokens [state_from, state_to) it reads and the questions (jobs)
// it answers.
struct Call {
    size_t state_from = 0, state_to = 0;
    std::vector<size_t> questions;
};

// The state's tokens from `from` (the cells before come from a snapshot) up to P, then the questions
// (suffix[i] tokens each after the state), shortest first. While the rest of the state and the shortest
// question do not fit `call_budget`, a piece of at most `piece_budget` state tokens goes alone; the call
// with the state's last piece takes the questions that fit `call_budget`, the next calls the others, as
// many as fit and at most `max_count` each. A question longer than the budget has a call of its own.
inline std::vector<Call> plan_calls(size_t from, size_t P, const std::vector<size_t>& suffix, size_t piece_budget, size_t call_budget,
                                    size_t max_count) {
    std::vector<size_t> order(suffix.size());
    for (size_t i = 0; i < order.size(); ++i) order[i] = i;
    std::stable_sort(order.begin(), order.end(), [&](size_t a, size_t b) { return suffix[a] < suffix[b]; });
    std::vector<Call> calls;
    size_t pos = from;
    const size_t shortest = order.empty() ? 0 : suffix[order[0]];
    while (pos < P && P - pos + shortest > call_budget) {
        size_t n = std::min(piece_budget, P - pos);
        calls.push_back({pos, pos + n, {}});
        pos += n;
    }
    for (size_t k = 0; k < order.size();) {
        Call call{pos, P, {}};
        size_t used = P - pos;
        while (k < order.size() && (call.questions.empty() || (call.questions.size() < max_count && used + suffix[order[k]] <= call_budget))) {
            used += suffix[order[k]];
            call.questions.push_back(order[k++]);
        }
        calls.push_back(std::move(call));
        pos = P;
    }
    if (order.empty() && pos < P) calls.push_back({pos, P, {}});
    return calls;
}
