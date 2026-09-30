// The Python server's error bodies.
#pragma once
#include <initializer_list>
#include <string>
#include <vector>

#include "pyjson.hpp"

using pyjson::Value;

// `wire` items are FastAPI's RequestValidationError (type, loc, msg, input[, ctx]); the others are
// the app's ValueError handler (loc, msg, type).
struct ErrItem {
    std::string type;
    std::vector<Value> loc;
    std::string msg;
    bool wire = false;
    Value input;
    std::string ctx;  // serialized JSON object, empty = none
};

struct ApiError {
    int status;
    std::vector<ErrItem> items;
    std::string raw;  // a whole body instead of `items` (400/500)
};

inline Value S(const std::string& s) { return Value::str(s); }
inline Value I(size_t i) { Value v; v.kind = Value::Int; v.s = std::to_string(i); return v; }
inline std::vector<Value> L(std::vector<Value> base, std::initializer_list<Value> more) {
    for (auto& m : more) base.push_back(m);
    return base;
}

inline ErrItem wire_err(const std::string& type, std::vector<Value> loc, const std::string& msg, const Value& input, std::string ctx = "") {
    return {type, std::move(loc), msg, true, input, std::move(ctx)};
}
inline ErrItem app_err(std::vector<Value> loc, const std::string& msg, const std::string& type = "value_error") {
    return {type, std::move(loc), msg, false, {}, ""};
}
inline ApiError unprocessable(std::vector<ErrItem> items) { return {422, std::move(items), ""}; }
inline ApiError unprocessable(ErrItem item) { return {422, {std::move(item)}, ""}; }



// Starlette's JSONResponse: compact, raw UTF-8, allow_nan=False; what it cannot encode is a 500.
inline std::string error_body(const ApiError& e) {
    if (!e.raw.empty()) return e.raw;
    pyjson::DumpOptions compact{-1, false, ",", ":", false};
    std::string out = "{\"detail\":[";
    for (size_t i = 0; i < e.items.size(); ++i) {
        const ErrItem& it = e.items[i];
        Value loc;
        loc.kind = Value::List;
        loc.list = it.loc;
        std::string type, msg;
        pyjson::quote(type, it.type);
        pyjson::quote(msg, it.msg);
        out += i ? "," : "";
        if (it.wire) {
            out += "{\"type\":" + type + ",\"loc\":" + pyjson::dumps(loc, compact) + ",\"msg\":" + msg + ",\"input\":" + pyjson::dumps(it.input, compact);
            if (!it.ctx.empty()) out += ",\"ctx\":" + it.ctx;
            out += "}";
        } else {
            out += "{\"loc\":" + pyjson::dumps(loc, compact) + ",\"msg\":" + msg + ",\"type\":" + type + "}";
        }
    }
    return out + "]}";
}
