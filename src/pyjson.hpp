// pyjson: Python's json module as the jev Python server sees a request body, so that the C++ server
// accepts, rejects and renders exactly the same inputs.
//
// - loads(): CPython 3.12's C scanner: the same accepted inputs (NaN, Infinity, lone surrogates,
//   duplicate keys: the last value at the first key's place, integers of any size up to 4300 digits)
//   and the same JSONDecodeError messages and positions (code points, not bytes). Bodies are decoded
//   the way json.loads(bytes) does it: UTF-8 with an optional BOM, surrogates passed through.
// - dumps(): json.dumps with ensure_ascii=False: indent, sort_keys, separators, allow_nan, and float
//   repr (shortest round trip, exponent below -4 or from 16 on).
// - repr(): Python's repr() of the decoded value, for messages that quote it.
// Strings are WTF-8: UTF-8 in which a lone surrogate keeps its 3-byte form (ED A0..BF xx).
#pragma once

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace pyjson {

struct Value {
    enum Kind { Null, Bool, Int, Float, Str, List, Dict };
    Kind kind = Null;
    bool b = false;
    double f = 0;
    std::string s;  // Int: decimal digits, normalized ("-0" -> "0"); Str: WTF-8 text
    std::vector<Value> list;
    std::vector<std::pair<std::string, Value>> dict;  // insertion order, unique keys

    static Value str(std::string text) { Value v; v.kind = Str; v.s = std::move(text); return v; }
    bool is_dict() const { return kind == Dict; }
    bool is_str() const { return kind == Str; }
    bool is_list() const { return kind == List; }
    bool is_null() const { return kind == Null; }
    const Value* get(const std::string& key) const {
        for (auto& kv : dict) if (kv.first == key) return &kv.second;
        return nullptr;
    }
    // Python truthiness of a JSON value
    bool truthy() const {
        switch (kind) {
            case Null: return false;
            case Bool: return b;
            case Int: return s != "0";
            case Float: return f != 0;
            case Str: return !s.empty();
            case List: return !list.empty();
            default: return !dict.empty();
        }
    }
};

struct DecodeError {  // json.JSONDecodeError: FastAPI's 422 json_invalid
    std::string msg;
    size_t pos;
};
struct BodyError {};  // anything else json.loads raises (bad UTF-8, a >4300-digit integer): FastAPI's 400

// ---------------------------------------------------------------- UTF-8 / WTF-8
inline void append_utf8(std::string& out, uint32_t c) {
    if (c < 0x80) out += static_cast<char>(c);
    else if (c < 0x800) { out += static_cast<char>(0xC0 | (c >> 6)); out += static_cast<char>(0x80 | (c & 0x3F)); }
    else if (c < 0x10000) {
        out += static_cast<char>(0xE0 | (c >> 12)); out += static_cast<char>(0x80 | ((c >> 6) & 0x3F)); out += static_cast<char>(0x80 | (c & 0x3F));
    } else {
        out += static_cast<char>(0xF0 | (c >> 18)); out += static_cast<char>(0x80 | ((c >> 12) & 0x3F));
        out += static_cast<char>(0x80 | ((c >> 6) & 0x3F)); out += static_cast<char>(0x80 | (c & 0x3F));
    }
}

// bytes.decode('utf-8', 'surrogatepass'); false on invalid input.
inline bool decode_utf8(const std::string& in, std::u32string& out, bool surrogates = true) {
    out.clear();
    out.reserve(in.size());
    const auto* p = reinterpret_cast<const unsigned char*>(in.data());
    size_t n = in.size(), i = 0;
    while (i < n) {
        unsigned c = p[i];
        if (c < 0x80) { out += c; ++i; continue; }
        int len = c >= 0xF0 && c <= 0xF4 ? 4 : c >= 0xE0 ? 3 : c >= 0xC2 && c < 0xE0 ? 2 : 0;
        if (!len || i + len > n) return false;
        uint32_t cp = c & (len == 2 ? 0x1F : len == 3 ? 0x0F : 0x07);
        for (int k = 1; k < len; ++k) {
            if ((p[i + k] & 0xC0) != 0x80) return false;
            cp = (cp << 6) | (p[i + k] & 0x3F);
        }
        if ((len == 3 && cp < 0x800) || (len == 4 && (cp < 0x10000 || cp > 0x10FFFF))) return false;
        if (!surrogates && cp >= 0xD800 && cp <= 0xDFFF) return false;
        out += cp;
        i += len;
    }
    return true;
}

// The UnicodeDecodeError message of bytes.decode('utf-8') (strict), or "" when the bytes are valid.
inline std::string utf8_error(const std::string& in) {
    const auto* p = reinterpret_cast<const unsigned char*>(in.data());
    size_t n = in.size();
    for (size_t i = 0; i < n;) {
        unsigned c = p[i];
        if (c < 0x80) { ++i; continue; }
        size_t need = c >= 0xC2 && c <= 0xDF ? 2 : c >= 0xE0 && c <= 0xEF ? 3 : c >= 0xF0 && c <= 0xF4 ? 4 : 0;
        std::string reason;
        size_t good = 1;
        if (!need) reason = "invalid start byte";
        else {
            for (; good < need; ++good) {
                if (i + good >= n) { reason = "unexpected end of data"; break; }
                unsigned b = p[i + good], lo = 0x80, hi = 0xBF;
                if (good == 1) {
                    if (c == 0xE0) lo = 0xA0;
                    else if (c == 0xED) hi = 0x9F;
                    else if (c == 0xF0) lo = 0x90;
                    else if (c == 0xF4) hi = 0x8F;
                }
                if (b < lo || b > hi) { reason = "invalid continuation byte"; break; }
            }
        }
        if (reason.empty()) { i += need; continue; }
        char buf[160];
        if (good == 1) std::snprintf(buf, sizeof buf, "'utf-8' codec can't decode byte 0x%02x in position %zu: %s", c, i, reason.c_str());
        else std::snprintf(buf, sizeof buf, "'utf-8' codec can't decode bytes in position %zu-%zu: %s", i, i + good - 1, reason.c_str());
        return buf;
    }
    return "";
}

inline std::u32string code_points(const std::string& wtf8) {
    std::u32string out;
    decode_utf8(wtf8, out);
    return out;
}

inline bool is_surrogate(uint32_t c) { return c >= 0xD800 && c <= 0xDFFF; }

// ---------------------------------------------------------------- loads
class Parser {
public:
    explicit Parser(std::u32string text) : t_(std::move(text)) {}

    Value run() {
        size_t idx = skip(0);
        Value v;
        size_t end;
        try {
            v = scan(idx, end, 0);
        } catch (const Stop& s) {
            throw DecodeError{"Expecting value", s.idx};
        }
        end = skip(end);
        if (end != t_.size()) throw DecodeError{"Extra data", end};
        return v;
    }

private:
    struct Stop { size_t idx; };  // StopIteration(idx): "Expecting value" where it surfaces

    static bool ws(char32_t c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r'; }
    size_t skip(size_t i) const { while (i < t_.size() && ws(t_[i])) ++i; return i; }
    bool at(size_t i, const char* word) const {
        for (size_t k = 0; word[k]; ++k) if (i + k >= t_.size() || t_[i + k] != static_cast<char32_t>(word[k])) return false;
        return true;
    }
    static bool digit(char32_t c) { return c >= '0' && c <= '9'; }

    Value scan(size_t idx, size_t& next, int depth) {
        if (idx >= t_.size()) throw Stop{idx};
        if (depth > 900) throw BodyError{};  // Python: RecursionError
        char32_t c = t_[idx];
        Value v;
        switch (c) {
            case '"': v.kind = Value::Str; v.s = string(idx + 1, next); return v;
            case '{': return object(idx + 1, next, depth + 1);
            case '[': return array(idx + 1, next, depth + 1);
            case 'n': if (at(idx, "null")) { next = idx + 4; return v; } break;
            case 't': if (at(idx, "true")) { v.kind = Value::Bool; v.b = true; next = idx + 4; return v; } break;
            case 'f': if (at(idx, "false")) { v.kind = Value::Bool; next = idx + 5; return v; } break;
            case 'N': if (at(idx, "NaN")) { v.kind = Value::Float; v.f = std::nan(""); next = idx + 3; return v; } break;
            case 'I': if (at(idx, "Infinity")) { v.kind = Value::Float; v.f = INFINITY; next = idx + 8; return v; } break;
            case '-': if (at(idx, "-Infinity")) { v.kind = Value::Float; v.f = -INFINITY; next = idx + 9; return v; } break;
            default: break;
        }
        return number(idx, next);
    }

    Value number(size_t start, size_t& next) {
        size_t n = t_.size(), idx = start;
        if (n == 0) throw Stop{start};
        size_t end_idx = n - 1;
        if (t_[idx] == '-') { ++idx; if (idx > end_idx) throw Stop{start}; }
        if (t_[idx] >= '1' && t_[idx] <= '9') { ++idx; while (idx <= end_idx && digit(t_[idx])) ++idx; }
        else if (t_[idx] == '0') ++idx;
        else throw Stop{start};
        bool is_float = false;
        if (idx < end_idx && t_[idx] == '.' && digit(t_[idx + 1])) {
            is_float = true;
            idx += 2;
            while (idx <= end_idx && digit(t_[idx])) ++idx;
        }
        if (idx < end_idx && (t_[idx] == 'e' || t_[idx] == 'E')) {
            size_t e_start = idx++;
            if (idx < end_idx && (t_[idx] == '-' || t_[idx] == '+')) ++idx;
            while (idx <= end_idx && digit(t_[idx])) ++idx;
            if (digit(t_[idx - 1])) is_float = true; else idx = e_start;
        }
        std::string lit;
        for (size_t k = start; k < idx; ++k) lit += static_cast<char>(t_[k]);
        next = idx;
        Value v;
        if (is_float) {
            v.kind = Value::Float;
            v.f = std::strtod(lit.c_str(), nullptr);  // overflow -> inf, as float() does
            return v;
        }
        v.kind = Value::Int;
        bool neg = lit[0] == '-';
        std::string digits = neg ? lit.substr(1) : lit;
        if (digits.size() > 4300) throw BodyError{};  // int max_str_digits
        v.s = (neg && digits != "0") ? "-" + digits : digits;
        return v;
    }

    std::string string(size_t end, size_t& next) {
        size_t begin = end - 1, len = t_.size();
        std::string out;
        while (true) {
            size_t i = end;
            char32_t c = 0;
            for (; i < len; ++i) {
                c = t_[i];
                if (c == '"' || c == '\\') break;
                if (c <= 0x1F) throw DecodeError{"Invalid control character at", i};
            }
            if (i >= len) throw DecodeError{"Unterminated string starting at", begin};
            for (size_t k = end; k < i; ++k) append_utf8(out, t_[k]);
            ++i;
            if (c == '"') { end = i; break; }
            if (i == len) throw DecodeError{"Unterminated string starting at", begin};
            c = t_[i];
            if (c != 'u') {
                end = i + 1;
                switch (c) {
                    case '"': case '\\': case '/': break;
                    case 'b': c = '\b'; break;
                    case 'f': c = '\f'; break;
                    case 'n': c = '\n'; break;
                    case 'r': c = '\r'; break;
                    case 't': c = '\t'; break;
                    default: throw DecodeError{"Invalid \\escape", end - 2};
                }
                append_utf8(out, c);
                continue;
            }
            ++i;
            end = i + 4;
            if (end >= len) throw DecodeError{"Invalid \\uXXXX escape", i - 1};
            uint32_t cp = hex4(i, end - 5);
            i = end;
            if (cp >= 0xD800 && cp <= 0xDBFF && end + 6 < len && t_[i] == '\\' && t_[i + 1] == 'u') {
                uint32_t low = hex4(i + 2, end + 1);
                if (low >= 0xDC00 && low <= 0xDFFF) { cp = 0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00); end += 6; }
            }
            append_utf8(out, cp);
        }
        next = end;
        return out;
    }

    uint32_t hex4(size_t at, size_t err_pos) const {
        uint32_t v = 0;
        for (size_t k = at; k < at + 4; ++k) {
            char32_t d = t_[k];
            v <<= 4;
            if (d >= '0' && d <= '9') v |= d - '0';
            else if (d >= 'a' && d <= 'f') v |= d - 'a' + 10;
            else if (d >= 'A' && d <= 'F') v |= d - 'A' + 10;
            else throw DecodeError{"Invalid \\uXXXX escape", err_pos};
        }
        return v;
    }

    Value object(size_t idx, size_t& next, int depth) {
        Value v;
        v.kind = Value::Dict;
        std::unordered_map<std::string, size_t> where;
        size_t n = t_.size();
        idx = skip(idx);
        if (idx >= n || t_[idx] != '}') {
            while (true) {
                if (idx >= n || t_[idx] != '"') throw DecodeError{"Expecting property name enclosed in double quotes", idx};
                size_t after;
                std::string key = string(idx + 1, after);
                idx = skip(after);
                if (idx >= n || t_[idx] != ':') throw DecodeError{"Expecting ':' delimiter", idx};
                idx = skip(idx + 1);
                Value item = scan(idx, after, depth);
                auto hit = where.find(key);
                if (hit == where.end()) { where.emplace(key, v.dict.size()); v.dict.emplace_back(std::move(key), std::move(item)); }
                else v.dict[hit->second].second = std::move(item);
                idx = skip(after);
                if (idx < n && t_[idx] == '}') break;
                if (idx >= n || t_[idx] != ',') throw DecodeError{"Expecting ',' delimiter", idx};
                idx = skip(idx + 1);
            }
        }
        next = idx + 1;
        return v;
    }

    Value array(size_t idx, size_t& next, int depth) {
        Value v;
        v.kind = Value::List;
        size_t n = t_.size();
        idx = skip(idx);
        if (idx >= n || t_[idx] != ']') {
            while (true) {
                size_t after;
                v.list.push_back(scan(idx, after, depth));
                idx = skip(after);
                if (idx < n && t_[idx] == ']') break;
                if (idx >= n || t_[idx] != ',') throw DecodeError{"Expecting ',' delimiter", idx};
                idx = skip(idx + 1);
            }
        }
        next = idx + 1;
        return v;
    }

    std::u32string t_;
};

// json.loads(body_bytes)
inline Value loads(const std::string& bytes) {
    std::string body = bytes;
    if (body.size() >= 3 && body.compare(0, 3, "\xEF\xBB\xBF") == 0) body.erase(0, 3);  // utf-8-sig
    std::u32string text;
    if (!decode_utf8(body, text)) throw BodyError{};
    return Parser(std::move(text)).run();
}

// ---------------------------------------------------------------- dumps
struct NanError {  // ValueError: Out of range float values are not JSON compliant: <repr>
    std::string repr;
};

// repr(float)
inline std::string float_repr(double x) {
    if (std::isnan(x)) return "nan";
    if (std::isinf(x)) return x > 0 ? "inf" : "-inf";
    char buf[64];
    auto r = std::to_chars(buf, buf + sizeof buf, x, std::chars_format::scientific);
    std::string sci(buf, r.ptr);  // -d.ddde[+-]XX
    bool neg = sci[0] == '-';
    if (neg) sci.erase(0, 1);
    size_t e = sci.find('e');
    std::string mant = sci.substr(0, e), digits;
    int exp10 = std::atoi(sci.c_str() + e + 1);
    for (char c : mant) if (c != '.') digits += c;
    while (digits.size() > 1 && digits.back() == '0') digits.pop_back();
    std::string out;
    if (exp10 >= -4 && exp10 < 16) {
        if (exp10 < 0) out = "0." + std::string(-exp10 - 1, '0') + digits;
        else if (static_cast<size_t>(exp10) + 1 >= digits.size()) out = digits + std::string(exp10 + 1 - digits.size(), '0') + ".0";
        else out = digits.substr(0, exp10 + 1) + "." + digits.substr(exp10 + 1);
    } else {
        out = digits.substr(0, 1);
        if (digits.size() > 1) out += "." + digits.substr(1);
        char eb[16];
        std::snprintf(eb, sizeof eb, "e%c%02d", exp10 < 0 ? '-' : '+', exp10 < 0 ? -exp10 : exp10);
        out += eb;
    }
    return neg ? "-" + out : out;
}

// json's encode_basestring (ensure_ascii=False)
inline void quote(std::string& out, const std::string& s) {
    out += '"';
    for (unsigned char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            default:
                if (c < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); out += b; }
                else out += static_cast<char>(c);
        }
    }
    out += '"';
}

struct DumpOptions {
    int indent = -1;  // -1 = None
    bool sort_keys = false;
    const char* item_sep = ", ";
    const char* key_sep = ": ";
    bool allow_nan = true;
};

inline void dump(std::string& out, const Value& v, const DumpOptions& o, int level) {
    switch (v.kind) {
        case Value::Null: out += "null"; return;
        case Value::Bool: out += v.b ? "true" : "false"; return;
        case Value::Int: out += v.s; return;
        case Value::Float:
            if (std::isnan(v.f) || std::isinf(v.f)) {
                if (!o.allow_nan) throw NanError{float_repr(v.f)};
                out += std::isnan(v.f) ? "NaN" : v.f > 0 ? "Infinity" : "-Infinity";
            } else out += float_repr(v.f);
            return;
        case Value::Str: quote(out, v.s); return;
        default: break;
    }
    bool is_list = v.kind == Value::List;
    size_t count = is_list ? v.list.size() : v.dict.size();
    if (!count) { out += is_list ? "[]" : "{}"; return; }
    out += is_list ? '[' : '{';
    std::string sep = o.item_sep, newline;
    if (o.indent >= 0) {
        newline = "\n" + std::string(static_cast<size_t>(o.indent) * (level + 1), ' ');
        sep = ",";  // json.dumps(indent=...) uses (',', ': ') unless told otherwise
        sep += newline;
        out += newline;
    }
    if (is_list) {
        for (size_t i = 0; i < count; ++i) { if (i) out += sep; dump(out, v.list[i], o, level + 1); }
    } else {
        std::vector<const std::pair<std::string, Value>*> items;
        for (auto& kv : v.dict) items.push_back(&kv);
        // str order = code point order = byte order of (WTF-)8
        if (o.sort_keys) std::stable_sort(items.begin(), items.end(), [](auto* a, auto* b) { return a->first < b->first; });
        for (size_t i = 0; i < count; ++i) {
            if (i) out += sep;
            quote(out, items[i]->first);
            out += o.key_sep;
            dump(out, items[i]->second, o, level + 1);
        }
    }
    if (o.indent >= 0) out += "\n" + std::string(static_cast<size_t>(o.indent) * level, ' ');
    out += is_list ? ']' : '}';
}

inline std::string dumps(const Value& v, const DumpOptions& o = {}) {
    std::string out;
    dump(out, v, o, 0);
    return out;
}

// ---------------------------------------------------------------- repr
// str.isprintable(), approximated outside Latin-1 by the blocks of non-printable characters
// (format, separators, surrogates, private use) that can plausibly reach a message.
inline bool printable(uint32_t c) {
    if (c < 0x20 || (c >= 0x7F && c <= 0xA0) || c == 0xAD) return false;
    if (c < 0x300) return true;
    if ((c >= 0x600 && c <= 0x605) || c == 0x61C || c == 0x6DD || c == 0x70F || c == 0x180E || c == 0x1680) return false;
    if ((c >= 0x2000 && c <= 0x200F) || (c >= 0x2028 && c <= 0x202F) || (c >= 0x205F && c <= 0x206F) || c == 0x3000) return false;
    if ((c >= 0xD800 && c <= 0xF8FF) || c == 0xFEFF || (c >= 0xFFF9 && c <= 0xFFFB) || c == 0xFFFE || c == 0xFFFF) return false;
    if ((c >= 0xE0000 && c <= 0xE0FFF) || c >= 0xF0000) return false;
    return true;
}

inline std::string str_repr(const std::string& s) {
    auto cps = code_points(s);
    bool has_single = false, has_double = false;
    for (auto c : cps) { has_single |= c == '\''; has_double |= c == '"'; }
    char q = has_single && !has_double ? '"' : '\'';
    std::string out(1, q);
    for (uint32_t c : cps) {
        if (c == static_cast<uint32_t>(q) || c == '\\') { out += '\\'; out += static_cast<char>(c); }
        else if (c == '\t') out += "\\t";
        else if (c == '\n') out += "\\n";
        else if (c == '\r') out += "\\r";
        else if (c < 0x7F && c >= 0x20) out += static_cast<char>(c);
        else if (printable(c)) append_utf8(out, c);
        else {
            char b[16];
            if (c <= 0xFF) std::snprintf(b, sizeof b, "\\x%02x", c);
            else if (c <= 0xFFFF) std::snprintf(b, sizeof b, "\\u%04x", c);
            else std::snprintf(b, sizeof b, "\\U%08x", c);
            out += b;
        }
    }
    return out + q;
}

inline std::string repr(const Value& v) {
    switch (v.kind) {
        case Value::Null: return "None";
        case Value::Bool: return v.b ? "True" : "False";
        case Value::Int: return v.s;
        case Value::Float: return float_repr(v.f);
        case Value::Str: return str_repr(v.s);
        case Value::List: {
            std::string out = "[";
            for (size_t i = 0; i < v.list.size(); ++i) out += (i ? ", " : "") + repr(v.list[i]);
            return out + "]";
        }
        default: {
            std::string out = "{";
            for (size_t i = 0; i < v.dict.size(); ++i) out += (i ? ", " : "") + str_repr(v.dict[i].first) + ": " + repr(v.dict[i].second);
            return out + "}";
        }
    }
}

// str(value): the value itself for a string, its repr otherwise
inline std::string str(const Value& v) { return v.kind == Value::Str ? v.s : repr(v); }

}  // namespace pyjson
