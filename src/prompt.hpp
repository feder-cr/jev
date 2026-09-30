// The Python engine's binary prompt: the evidence block, then the question.
#pragma once
#include <string>

#include "errors.hpp"
#include "text.hpp"

// prompts.render_state: json.dumps(state, ensure_ascii=False, indent=1) unless it is plain text
inline std::string render_state(const Value& state) {
    std::string body;
    if (state.is_str() && ascii_lower(state.s).find("</evidence>") == std::string::npos)
        body = py_strip(state.s);
    else
        body = pyjson::dumps(state, {1, false, ", ", ": ", true});
    return "<evidence>\n" + body + "\n</evidence>";
}

// translate.text: a string stripped, anything else canonical JSON (sort_keys, no spaces, no NaN)
inline std::string text_of(const Value& v) {
    if (v.is_str()) return py_strip(v.s);
    try {
        return pyjson::dumps(v, {-1, true, ",", ":", false});
    } catch (const pyjson::NanError& e) {
        throw unprocessable(app_err({S("body")}, "Out of range float values are not JSON compliant: " + e.repr));
    }
}

inline std::string binary_prompt(const std::string& bos, const std::string& state_text, const std::string& instruction) {
    return bos + state_text + "\n\nQuestion: " + instruction + "\nAnswer:";
}
