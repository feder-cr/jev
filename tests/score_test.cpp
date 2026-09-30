// rate (src/score.hpp): a score's distribution from its thresholds' yes/no answers. Exit status 1 on a
// failure. Built by scripts/build.py, run by tests/check.py.
#include <cmath>
#include <cstdio>
#include <vector>

#include "score.hpp"

static int failures = 0;

static void expect(bool ok, const char* what) {
    if (!ok) {
        std::printf("FAIL %s\n", what);
        ++failures;
    }
}

static bool near(double a, double b) { return std::fabs(a - b) < 1e-12; }

int main() {
    // three levels, thresholds in order: P(= k) = P(>= k) - P(>= k+1), the expected level, Jev's confidence
    ScoreAnswer a = rate({0.9, 0.2}, 3);
    expect(near(a.probabilities[0], 0.1) && near(a.probabilities[1], 0.7) && near(a.probabilities[2], 0.2), "differences of the thresholds");
    expect(near(a.score, 0.7 + 2 * 0.2), "the expected level");
    // mode 1: E|i - 1| = 0.3; uniform about the middle (1): (1 + 0 + 1) / 3
    expect(near(a.confidence, 1 - 0.3 / (2.0 / 3)), "confidence 1 - E|i - mode| / the uniform's");

    // thresholds out of order are pooled: P(>= 1) = 0.3 < P(>= 2) = 0.5 become 0.4 and 0.4
    ScoreAnswer p = rate({0.3, 0.5}, 3);
    expect(near(p.probabilities[0], 0.6) && near(p.probabilities[1], 0.0) && near(p.probabilities[2], 0.4), "out of order thresholds pooled");
    double sum = 0;
    for (double x : p.probabilities) sum += x;
    expect(near(sum, 1.0), "probabilities sum to 1");

    // two phrasings: the mean per threshold first (phrasing-major layout)
    ScoreAnswer m = rate({1.0, 0.6}, 2);
    expect(near(m.probabilities[1], 0.8) && near(m.score, 0.8), "the mean over phrasings");

    // certain answers: confidence 1; every threshold one half on two levels: confidence 0
    expect(near(rate({1.0, 1.0, 0.0}, 4).confidence, 1.0), "a certain level gives confidence 1");
    expect(near(rate({0.5}, 2).confidence, 0.0), "an even split of two levels gives confidence 0");

    if (failures) return 1;
    std::printf("rate: all checks passed\n");
    return 0;
}
