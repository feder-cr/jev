// The jev API: POST /v1/systemone, GET /v1/models and /health, with the Python server's answers and
// errors (`jev serve`); the same answer for one request file (`jev decide`).
#pragma once
#include <string>

#include "errors.hpp"
#include "model.hpp"
#include "scheduler.hpp"
#include "vocab.hpp"

struct Timing {  // milliseconds, for Server-Timing
    double parse = 0, validate = 0, tokenize = 0, queue = 0, inference = 0, respond = 0;
};

// One request body in, its answer body out (compact JSON), or an ApiError. Requests are tokenized with
// `vocab` on the caller's thread; model calls go through `scheduler`; `model` is read only to describe
// itself (/health).
struct Api {
    const Model& model;
    const Vocab& vocab;
    Scheduler& scheduler;
    std::string served;  // the model's name in answers
    size_t ctx;          // the longest prompt, in tokens
    ojson files;         // /health: the SHA-256 of each file of the model folder, and their fingerprint
    std::string systemone(const Value& body, Timing& tm) const;
};

// An error's body as the Python server writes it (what JSONResponse cannot encode is itself an error).
std::string rendered_error(const ApiError& e);

struct ServeOptions {
    std::string host, api_key;  // api_key empty: no authentication
    int port;
};

// Serves until the listener stops; false when it cannot listen.
bool serve(const Api& api, const ServeOptions& options);
