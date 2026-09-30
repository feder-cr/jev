// The request's validation, as the Python server runs it. Its order of checks: the wire model
// (pydantic: every error at once), the model name, the translation to the native request (texts), the
// native model (lengths, then the state), the binary refusal, the prompts (encoding, context).
#pragma once
#include <string>
#include <utility>
#include <vector>

#include "errors.hpp"

using Errs = std::vector<ErrItem>;

inline const char* DEFAULT_NOUL = "Does the evidence support a yes?";

// wire.SystemOneRequest; `body` null = no body at all
void check_wire(const Value& body, Errs& errs);

// A question after translate.native_question: its type and texts, in the native model's field order.
struct NativeQuestion {
    std::string id, kind;  // boolean | choice | score
    std::string instructions;
    std::vector<std::pair<std::string, std::string>> texts;  // (field, text): descriptions, options, levels
};

NativeQuestion to_native(const std::string& qid, const Value& q);

// schema.Request: Text fields (stripped, 1-8000 characters), the question count, then valid_state.
void check_native(const Value& state, const std::vector<NativeQuestion>& qs, Errs& errs);
