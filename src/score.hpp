// A score question from yes/no answers: one threshold question per level above the lowest, "is it at
// this level or higher?" (prompt.hpp's score_instructions), and the answers become one distribution
// over the levels.
#pragma once
#include <algorithm>
#include <string>
#include <vector>

// The phrasings asked for each threshold, among the two the model was trained on
// (datagen/binary_templates.py SCORE_PHRASINGS); a threshold's P(yes) is the mean over them. This one:
// the same accuracy on 2,350 held-out score questions, and fewer thresholds out of order (19% vs 29%).
inline const std::vector<std::string> SCORE_PHRASINGS = {"Is the answer at the following level or higher?"};

struct ScoreAnswer {
    double score;                       // the expected level, 0 to n - 1
    std::vector<double> probabilities;  // one per level, summing to 1
    double confidence;                  // Jev's: how concentrated around the most probable level
};

// `ps` holds P(level >= k) for every phrasing and k = 1..n-1, phrasing-major (ps[f * (n - 1) + k - 1]).
// The mean over phrasings, made non-increasing in k where the separate answers are not (pool adjacent
// violators); P(level = k) = P(>= k) - P(>= k + 1), with P(>= 0) = 1 and P(>= n) = 0. Confidence:
// 1 - E|i - mode| / the same for a uniform distribution about the middle, clamped (decisions.score_confidence).
inline ScoreAnswer rate(const std::vector<double>& ps, size_t n) {
    const size_t t = n - 1, phrasings = ps.size() / t;
    std::vector<double> ge(t, 0.0);
    for (size_t f = 0; f < phrasings; ++f)
        for (size_t k = 0; k < t; ++k) ge[k] += ps[f * t + k] / static_cast<double>(phrasings);
    std::vector<std::pair<double, size_t>> pools;  // (sum, count), each pool's mean below the one before
    for (double v : ge) {
        pools.push_back({v, 1});
        while (pools.size() > 1 && pools[pools.size() - 2].first * pools.back().second < pools.back().first * pools[pools.size() - 2].second) {
            auto last = pools.back();
            pools.pop_back();
            pools.back().first += last.first;
            pools.back().second += last.second;
        }
    }
    ge.clear();
    for (auto& [sum, count] : pools) ge.insert(ge.end(), count, std::clamp(sum / static_cast<double>(count), 0.0, 1.0));
    std::vector<double> p(n);
    for (size_t i = 0; i < n; ++i) p[i] = std::max(0.0, (i == 0 ? 1.0 : ge[i - 1]) - (i == t ? 0.0 : ge[i]));  // not -1e-17 from rounding
    double score = 0.0;
    size_t mode = 0;
    for (size_t i = 0; i < n; ++i) {
        score += static_cast<double>(i) * p[i];
        if (p[i] > p[mode]) mode = i;
    }
    double spread = 0.0, uniform = 0.0, middle = static_cast<double>(t) / 2.0;
    for (size_t i = 0; i < n; ++i) {
        spread += p[i] * (i > mode ? static_cast<double>(i - mode) : static_cast<double>(mode - i));
        uniform += (static_cast<double>(i) > middle ? static_cast<double>(i) - middle : middle - static_cast<double>(i)) / static_cast<double>(n);
    }
    return {score, std::move(p), std::clamp(1.0 - spread / uniform, 0.0, 1.0)};
}
