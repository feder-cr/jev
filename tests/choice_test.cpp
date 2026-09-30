// choose (src/choice.hpp): a choice's distribution from its options' yes/no answers. Exit status 1 on a
// failure. Built by scripts/build.py, run by tests/check.py.
#include <cmath>
#include <cstdio>
#include <vector>

#include "choice.hpp"

static int failures = 0;

static void expect(bool ok, const char* what) {
    if (!ok) {
        std::printf("FAIL %s\n", what);
        ++failures;
    }
}

static bool near(double a, double b) { return std::fabs(a - b) < 1e-12; }

int main() {
    // four options, one phrasing: normalized, the first highest wins, confidence from the peak
    ChoiceAnswer a = choose({0.8, 0.3, 0.05, 0.05}, 4);
    expect(a.best == 0, "the highest option wins");
    double sum = 0;
    for (double p : a.probabilities) sum += p;
    expect(near(sum, 1.0), "probabilities sum to 1");
    expect(near(a.probabilities[0], 0.8 / 1.2) && near(a.probabilities[1], 0.3 / 1.2), "normalized by the sum");
    expect(near(a.confidence, (0.8 / 1.2 - 0.25) / 0.75), "confidence (p_max - 1/n) / (1 - 1/n)");

    // a tie: the first of the tied options, as Python's max()
    expect(choose({0.4, 0.6, 0.6}, 3).best == 1, "a tie goes to the first tied option");

    // two phrasings: the mean per option before normalizing (phrasing-major layout)
    ChoiceAnswer m = choose({0.9, 0.1, 0.5, 0.3}, 2);
    expect(near(m.probabilities[0], 0.7 / 0.9) && near(m.probabilities[1], 0.2 / 0.9), "the mean over phrasings, then normalized");

    // uniform answers: confidence 0; one certain option: confidence 1
    expect(near(choose({0.3, 0.3, 0.3}, 3).confidence, 0.0), "uniform answers give confidence 0");
    expect(near(choose({1.0, 0.0, 0.0}, 3).confidence, 1.0), "one certain option gives confidence 1");

    // every answer 0: uniform, not a division by zero
    ChoiceAnswer z = choose({0.0, 0.0}, 2);
    expect(near(z.probabilities[0], 0.5) && near(z.probabilities[1], 0.5) && z.best == 0, "all zero answers give a uniform distribution");

    if (failures) return 1;
    std::printf("choose: all checks passed\n");
    return 0;
}
