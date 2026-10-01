// The questions of one call as a prefix tree over their tokens after the part the call shares: runs of
// tokens several prompts have in common (a choice's instructions and options, a score's scale) are read
// once, and each prompt still sees only its own tokens. Nothing here knows about the model.
#pragma once
#include <algorithm>
#include <cstdint>
#include <map>
#include <vector>

#include "tokens.hpp"

// Tokens [from, to) of prompt `prompt`, at positions from..to-1, read after its parent's (NO_PARENT: right
// after the shared part). A prompt's last token is always a node of its own, the leaf its answer is read at.
struct TreeNode {
    static constexpr size_t NO_PARENT = SIZE_MAX;
    size_t parent;
    size_t prompt;
    size_t from, to;
};

struct PromptTree {
    std::vector<TreeNode> nodes;  // depth first, a parent before its children, children in prompt order
    std::vector<size_t> leaf;     // per prompt, its leaf node
    size_t tokens = 0;            // tokens read: the nodes' lengths
};

// The tree of `prompts` after their first `skip` tokens, which they all share and are read apart (every
// prompt is longer than `skip`).
inline PromptTree prompt_tree(const std::vector<const Tokens*>& prompts, size_t skip) {
    PromptTree t;
    t.leaf.resize(prompts.size());
    auto add = [&](size_t parent, size_t prompt, size_t from, size_t to) {
        t.nodes.push_back({parent, prompt, from, to});
        t.tokens += to - from;
        return t.nodes.size() - 1;
    };
    // members share their tokens before `d`, already in the tree up to `parent`
    auto grow = [&](auto& self, const std::vector<size_t>& members, size_t d, size_t parent) -> void {
        std::vector<std::vector<size_t>> children;  // in order of their first member
        std::vector<bool> leaf;
        std::map<int32_t, size_t> by_token;
        for (size_t m : members) {
            const Tokens& p = *prompts[m];
            if (p.size() - 1 <= d) {  // everything but the last token is in the tree: the leaf
                children.push_back({m});
                leaf.push_back(true);
                continue;
            }
            auto [it, fresh] = by_token.emplace(p[d], children.size());
            if (fresh) {
                children.emplace_back();
                leaf.push_back(false);
            }
            children[it->second].push_back(m);
        }
        for (size_t c = 0; c < children.size(); ++c) {
            const std::vector<size_t>& group = children[c];
            const Tokens& a = *prompts[group[0]];
            if (leaf[c]) {
                t.leaf[group[0]] = add(parent, group[0], a.size() - 1, a.size());
                continue;
            }
            size_t end = a.size() - 1;
            for (size_t m : group) end = std::min(end, prompts[m]->size() - 1);
            size_t e = d + 1;  // the group shares token d
            while (e < end && std::all_of(group.begin(), group.end(), [&](size_t m) { return (*prompts[m])[e] == a[e]; })) ++e;
            self(self, group, e, add(parent, group[0], d, e));
        }
    };
    std::vector<size_t> all(prompts.size());
    for (size_t i = 0; i < all.size(); ++i) all[i] = i;
    grow(grow, all, skip, TreeNode::NO_PARENT);
    return t;
}

// The tokens prompt `p` adds to a tree that already holds `members` (all after `skip`): what it does not
// share with any of them, and always its last token.
inline size_t added_tokens(const std::vector<const Tokens*>& prompts, const std::vector<size_t>& members, size_t p, size_t skip) {
    const Tokens& a = *prompts[p];
    size_t body = a.size() - 1, shared = skip;
    for (size_t m : members) {
        const Tokens& b = *prompts[m];
        size_t k = skip, n = std::min(body, b.size() - 1);
        while (k < n && a[k] == b[k]) ++k;
        shared = std::max(shared, k);
    }
    return a.size() - shared;
}
