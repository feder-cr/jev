// plan_calls (src/calls.hpp): the calls cover the state in order, answer every question exactly once,
// keep state pieces within the piece budget and question calls within the call budget (except a question
// that alone exceeds it), and always end. Exit status 1 on a failure. Built by scripts/build.py, run by
// tests/check.py.
#include <cstdio>
#include <string>
#include <vector>

#include "calls.hpp"

static int failures = 0;

static void expect(bool ok, const std::string& what) {
    if (!ok) {
        std::printf("FAIL %s\n", what.c_str());
        ++failures;
    }
}

static std::vector<Call> check(const std::string& name, size_t from, size_t P, const std::vector<size_t>& suffix, size_t piece, size_t budget,
                               size_t max_count) {
    auto calls = plan_calls(from, P, suffix, piece, budget, max_count);
    std::vector<int> answered(suffix.size(), 0);
    size_t pos = from;
    bool questions_started = false;
    for (auto& c : calls) {
        expect(c.state_from == pos || (c.state_from == P && pos == P), name + ": the state is read in order, without gaps");
        expect(c.state_to >= c.state_from && c.state_to <= P, name + ": a state piece within the state");
        pos = c.state_to;
        size_t tokens = c.state_to - c.state_from;
        for (size_t q : c.questions) {
            ++answered[q];
            tokens += suffix[q];
        }
        expect(c.questions.size() <= max_count, name + ": at most max_count questions a call");
        if (c.questions.empty()) {
            expect(tokens <= piece && tokens > 0, name + ": a state piece within the piece budget, not empty");
            expect(!questions_started, name + ": state pieces come before the questions");
        } else {
            expect(tokens <= budget || c.questions.size() == 1, name + ": a question call within the budget unless one question alone exceeds it");
            questions_started = true;
        }
    }
    expect(pos == P, name + ": the whole state is read");
    for (size_t q = 0; q < suffix.size(); ++q) expect(answered[q] == 1, name + ": question " + std::to_string(q) + " answered once");
    return calls;
}

int main() {
    const std::vector<size_t> ten{20, 18, 25, 31, 22, 19, 17, 24, 16, 12};
    auto one = check("999-like request", 0, 154, ten, 2048, 512, 16);
    expect(one.size() == 1 && one[0].state_to == 154 && one[0].questions.size() == 10, "a request that fits is one call");
    check("small budget", 0, 154, ten, 2048, 64, 16);
    check("pieces smaller than calls", 0, 1000, ten, 128, 512, 16);
    auto many = check("many questions", 0, 200, std::vector<size_t>(80, 20), 2048, 512, 1 << 20);
    expect(many.size() == 4, "80 questions of 20 tokens on a 200-token state: 4 calls of at most 512 tokens");
    check("long state", 0, 5000, {20, 30, 25}, 2048, 512, 16);
    check("long state from a snapshot", 1800, 5000, {20, 30, 25}, 2048, 512, 16);
    check("full snapshot hit", 300, 300, {20, 30, 25}, 2048, 512, 16);
    check("a question longer than a call", 0, 100, {2100}, 2048, 512, 16);  // the old loop never ended here
    check("a question longer than a call, full hit", 100, 100, {2100}, 2048, 512, 16);
    check("a long question among short ones", 0, 100, {10, 2100, 12}, 2048, 512, 16);
    check("a long question after a long state", 0, 4000, {3000}, 2048, 512, 16);
    check("many questions, few sequences", 0, 200, std::vector<size_t>(150, 20), 2048, 2048, 4);
    check("no questions", 0, 5000, {}, 2048, 512, 16);
    std::printf(failures ? "%d plan_calls checks failed\n" : "plan_calls: all checks passed\n", failures);
    return failures ? 1 : 0;
}
