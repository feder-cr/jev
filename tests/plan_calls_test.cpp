// plan_calls (src/calls.hpp) and prompt_tree (src/tree.hpp). The calls cover the state in order, answer
// every question exactly once, keep state pieces within the piece budget and question calls within the
// call budget (except a question that alone exceeds it), and always end. Every question's path in its
// call's tree spells exactly its own tokens, and shared runs are read once. Exit status 1 on a failure.
// Built by scripts/build.py, run by tests/check.py.
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

// Prompts of P shared tokens, then their own: `shared[i]` tokens common to every prompt of the same
// `group[i]`, then `own[i]` tokens no other prompt has.
static std::vector<Tokens> prompts_of(size_t P, const std::vector<size_t>& own, const std::vector<size_t>& shared = {},
                                      const std::vector<int>& group = {}) {
    std::vector<Tokens> out;
    for (size_t i = 0; i < own.size(); ++i) {
        Tokens t(P, 7);
        for (size_t s = 0; s < (shared.empty() ? 0 : shared[i]); ++s) t.push_back(1000 + 100 * group[i] + static_cast<int32_t>(s % 50));
        for (size_t s = 0; s < own[i]; ++s) t.push_back(100000 + static_cast<int32_t>(i * 10000 + s));
        out.push_back(std::move(t));
    }
    return out;
}

static std::vector<const Tokens*> pointers(const std::vector<Tokens>& ps) {
    std::vector<const Tokens*> out;
    for (auto& p : ps) out.push_back(&p);
    return out;
}

// A tree's paths spell the prompts, parents come first, every leaf is a prompt's last token.
static void check_tree(const std::string& name, const std::vector<const Tokens*>& prompts, size_t skip, const PromptTree& t) {
    size_t tokens = 0;
    for (size_t n = 0; n < t.nodes.size(); ++n) {
        expect(t.nodes[n].parent == TreeNode::NO_PARENT || t.nodes[n].parent < n, name + ": a parent before its children");
        expect(t.nodes[n].to > t.nodes[n].from, name + ": no empty node");
        tokens += t.nodes[n].to - t.nodes[n].from;
    }
    expect(tokens == t.tokens, name + ": the token count is the nodes'");
    for (size_t q = 0; q < prompts.size(); ++q) {
        Tokens path;
        std::vector<size_t> chain;
        for (size_t n = t.leaf[q]; n != TreeNode::NO_PARENT; n = t.nodes[n].parent) chain.push_back(n);
        size_t at = skip;
        for (auto it = chain.rbegin(); it != chain.rend(); ++it) {
            const TreeNode& node = t.nodes[*it];
            expect(node.from == at, name + ": a path's positions continue");
            const Tokens& src = *prompts[node.prompt];
            path.insert(path.end(), src.begin() + node.from, src.begin() + node.to);
            at = node.to;
        }
        expect(Tokens(prompts[q]->begin() + skip, prompts[q]->end()) == path, name + ": question " + std::to_string(q) + "'s path is its tokens");
        expect(t.nodes[t.leaf[q]].to - t.nodes[t.leaf[q]].from == 1 && t.nodes[t.leaf[q]].to == prompts[q]->size(), name + ": the leaf is the last token");
    }
}

static std::vector<Call> check(const std::string& name, size_t from, size_t P, const std::vector<Tokens>& ps, size_t piece, size_t budget, size_t max_count) {
    auto prompts = pointers(ps);
    auto calls = plan_calls(from, P, prompts, piece, budget, max_count);
    std::vector<int> answered(ps.size(), 0);
    size_t pos = from;
    bool questions_started = false;
    for (auto& c : calls) {
        expect(c.state_from == pos || (c.state_from == P && pos == P), name + ": the state is read in order, without gaps");
        expect(c.state_to >= c.state_from && c.state_to <= P, name + ": a state piece within the state");
        pos = c.state_to;
        size_t tokens = c.state_to - c.state_from;
        std::vector<const Tokens*> mine;
        for (size_t q : c.questions) {
            ++answered[q];
            mine.push_back(prompts[q]);
        }
        expect(c.questions.size() <= max_count, name + ": at most max_count questions a call");
        if (c.questions.empty()) {
            expect(tokens <= piece && tokens > 0, name + ": a state piece within the piece budget, not empty");
            expect(!questions_started, name + ": state pieces come before the questions");
        } else {
            PromptTree t = prompt_tree(mine, P);
            check_tree(name, mine, P, t);
            tokens += t.tokens;
            expect(tokens <= budget || c.questions.size() == 1, name + ": a question call within the budget unless one question alone exceeds it");
            questions_started = true;
        }
    }
    expect(pos == P, name + ": the whole state is read");
    for (size_t q = 0; q < ps.size(); ++q) expect(answered[q] == 1, name + ": question " + std::to_string(q) + " answered once");
    return calls;
}

int main() {
    const std::vector<size_t> ten{20, 18, 25, 31, 22, 19, 17, 24, 16, 12};
    auto one = check("999-like request", 0, 154, prompts_of(154, ten), 2048, 512, 16);
    expect(one.size() == 1 && one[0].state_to == 154 && one[0].questions.size() == 10, "a request that fits is one call");
    check("small budget", 0, 154, prompts_of(154, ten), 2048, 64, 16);
    check("pieces smaller than calls", 0, 1000, prompts_of(1000, ten), 128, 512, 16);
    auto many = check("many questions", 0, 200, prompts_of(200, std::vector<size_t>(80, 20)), 2048, 512, 1 << 20);
    expect(many.size() == 4, "80 questions of 20 tokens on a 200-token state: 4 calls of at most 512 tokens");
    check("long state", 0, 5000, prompts_of(5000, {20, 30, 25}), 2048, 512, 16);
    check("long state from a snapshot", 1800, 5000, prompts_of(5000, {20, 30, 25}), 2048, 512, 16);
    check("full snapshot hit", 300, 300, prompts_of(300, {20, 30, 25}), 2048, 512, 16);
    check("a question longer than a call", 0, 100, prompts_of(100, {2100}), 2048, 512, 16);  // the old loop never ended here
    check("a question longer than a call, full hit", 100, 100, prompts_of(100, {2100}), 2048, 512, 16);
    check("a long question among short ones", 0, 100, prompts_of(100, {10, 2100, 12}), 2048, 512, 16);
    check("a long question after a long state", 0, 4000, prompts_of(4000, {3000}), 2048, 512, 16);
    check("many questions, few sequences", 0, 200, prompts_of(200, std::vector<size_t>(150, 20)), 2048, 2048, 4);
    check("no questions", 0, 5000, {}, 2048, 512, 16);

    // A choice of 10 options (120 shared tokens, 6 of their own each) beside 2 yes/no questions and a score
    // of 3 thresholds (40 shared, 3 each): the shared runs are read once, all in one call.
    std::vector<size_t> own{6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 15, 18, 3, 3, 3}, shared{120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 0, 0, 40, 40, 40};
    std::vector<int> group{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 3, 3};
    auto mixed = prompts_of(60, own, shared, group);
    auto calls = check("a choice, yes/no questions and a score", 0, 60, mixed, 2048, 1024, 64);
    expect(calls.size() == 1, "the mixed request is one call");
    PromptTree t = prompt_tree(pointers(mixed), 60);
    expect(t.tokens == 120 + 10 * 6 + 15 + 18 + 40 + 3 * 3, "the mixed request reads each shared run once: " + std::to_string(t.tokens));
    check("the mixed request, small budget", 0, 60, mixed, 2048, 200, 64);

    // The same question twice, a question that is all of another's start, one-token questions.
    std::vector<Tokens> odd{{7, 7, 1, 2, 3}, {7, 7, 1, 2, 3}, {7, 7, 1, 2}, {7, 7, 9}, {7, 7, 1, 2, 3, 4}};
    check_tree("same, prefix and short questions", pointers(odd), 2, prompt_tree(pointers(odd), 2));
    check("same, prefix and short questions", 0, 2, odd, 2048, 1024, 64);

    std::printf(failures ? "%d plan_calls checks failed\n" : "plan_calls: all checks passed\n", failures);
    return failures ? 1 : 0;
}
