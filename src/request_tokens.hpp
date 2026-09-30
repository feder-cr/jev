// A request's tokens as the Python engine makes them.
#pragma once
#include <string>
#include <vector>

#include "vocab.hpp"

struct RequestTokens {
    std::vector<Tokens> prompts;  // one per question, in order: each prompt tokenized whole
    Tokens prefix;                // the tokens every prompt starts with, read once; empty when none
    size_t state = 0;             // how many of them are the state's (usage, snapshots)
};

// Every prompt whole, as the Python engine does (state and question share BPE merges across their
// boundary). The state's part: its own tokens minus the last one (a merge may cross the boundary), cut to
// what every prompt starts with, and none when a prompt does not extend it. The prefix: with several
// prompts, all the tokens they have in common (for a choice, its instructions and options too), short of
// the shortest prompt; the model reads it once for all the questions and reads a long one in pieces. `state_text` is the
// rendered state (render_state); `instructions`, each question's text. A long state with several
// questions spreads its tokenizations over threads, which gives the same tokens.
RequestTokens tokenize_request(const Vocab& vocab, const std::string& state_text, const std::vector<std::string>& instructions);
