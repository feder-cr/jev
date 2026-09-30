// The unit of work between the API and the model: token ids.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

using Tokens = std::vector<int32_t>;

struct Job {
    std::string id;
    Tokens tokens;  // the whole prompt
};

// One request's model work: its questions' prompts and the tokens they all start with, read once (empty =
// none). The first `state` of them are the state's: what is kept as a snapshot for later requests (the
// rest, such as a choice's instructions and options, belongs to this request's questions).
struct ScoreRequest {
    Tokens prefix;
    std::vector<Job> jobs;
    size_t state = 0;
    size_t tokens() const {  // what reading it costs, the state once
        size_t n = prefix.size();
        for (auto& j : jobs) n += j.tokens.size() - prefix.size();
        return n;
    }
};
