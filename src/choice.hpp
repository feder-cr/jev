// A choice question from yes/no answers: each option is asked against all the others (prompt.hpp's
// choice_instructions), and the answers become one distribution over the options.
#pragma once
#include <algorithm>
#include <string>
#include <vector>

// The phrasings asked for each option, among the three the model was trained on
// (datagen/binary_templates.py CHOICE_PHRASINGS); an option's P(yes) is the mean over them.
inline const std::vector<std::string> CHOICE_PHRASINGS = {"Among the candidates, is it this one?"};

struct ChoiceAnswer {
    size_t best;                       // the first option with the highest probability
    std::vector<double> probabilities;  // one per option, summing to 1
    double confidence;                 // the peak rescaled from uniform (0) to certain (1), as Jev reports it
};

// `ps` holds P(yes) for every phrasing and option, phrasing-major (ps[f * n + i]): the mean over phrasings
// per option, normalized to sum 1 (the yes/no answers are separate questions and do not sum to 1 by
// themselves); confidence (p_max - 1/n) / (1 - 1/n).
inline ChoiceAnswer choose(const std::vector<double>& ps, size_t n) {
    const size_t phrasings = ps.size() / n;
    std::vector<double> p(n, 0.0);
    for (size_t f = 0; f < phrasings; ++f)
        for (size_t i = 0; i < n; ++i) p[i] += ps[f * n + i] / static_cast<double>(phrasings);
    double sum = 0.0;
    for (double x : p) sum += x;
    for (double& x : p) x = sum > 0.0 ? x / sum : 1.0 / static_cast<double>(n);
    size_t best = 0;
    for (size_t i = 1; i < n; ++i)
        if (p[i] > p[best]) best = i;
    double uniform = 1.0 / static_cast<double>(n);
    double confidence = std::clamp((p[best] - uniform) / (1.0 - uniform), 0.0, 1.0);
    return {best, std::move(p), confidence};
}
