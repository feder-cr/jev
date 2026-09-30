// A request's tokens as the Python engine makes them.
#pragma once
#include <string>
#include <vector>

#include "vocab.hpp"

struct RequestTokens {
    std::vector<Tokens> prompts;  // one per question, in order: each prompt tokenized whole
    Tokens prefix;                // the state's tokens the prompts share; empty when a prompt does not extend them
};

// Every prompt whole, as the Python engine does (state and question share BPE merges across their
// boundary). The prefix: the state's own tokens minus the last one (a merge may cross the boundary), cut
// to what every prompt starts with, and dropped when a prompt does not extend it; the model reads it once
// for all the questions, keeps it as a snapshot, and reads a long one in pieces. `state_text` is the
// rendered state (render_state); `instructions`, each question's text. A long state with several
// questions spreads its tokenizations over threads, which gives the same tokens.
RequestTokens tokenize_request(const Vocab& vocab, const std::string& state_text, const std::vector<std::string>& instructions);
