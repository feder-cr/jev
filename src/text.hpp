// Python's str semantics on WTF-8 text (pyjson.hpp): len(), strip(), and encoding errors.
#pragma once
#include <cstdio>
#include <cstring>
#include <string>

#include "ascii.hpp"
#include "pyjson.hpp"

inline bool has_surrogate(const std::string& s) {
    for (size_t i = 0; i + 1 < s.size(); ++i)
        if (static_cast<unsigned char>(s[i]) == 0xED && static_cast<unsigned char>(s[i + 1]) >= 0xA0) return true;
    return false;
}

inline size_t utf8_length(const std::string& s) {  // len() of a (WTF-8) str
    size_t n = 0;
    for (unsigned char c : s) n += (c & 0xC0) != 0x80;
    return n;
}

// Python str.strip(): ASCII whitespace, \x1c-\x1f and the Unicode spaces str.isspace() accepts.
inline bool space_at(const std::string& s, size_t i, size_t& width) {
    unsigned char c = s[i];
    if (c == ' ' || (c >= 0x09 && c <= 0x0D) || (c >= 0x1C && c <= 0x1F)) { width = 1; return true; }
    static const char* spaces[] = {"\xC2\x85", "\xC2\xA0", "\xE1\x9A\x80", "\xE2\x80\x80", "\xE2\x80\x81", "\xE2\x80\x82",
                                   "\xE2\x80\x83", "\xE2\x80\x84", "\xE2\x80\x85", "\xE2\x80\x86", "\xE2\x80\x87", "\xE2\x80\x88",
                                   "\xE2\x80\x89", "\xE2\x80\x8A", "\xE2\x80\xA8", "\xE2\x80\xA9", "\xE2\x80\xAF", "\xE2\x81\x9F",
                                   "\xE3\x80\x80"};
    for (const char* sp : spaces) {
        size_t n = std::strlen(sp);
        if (s.compare(i, n, sp) == 0) { width = n; return true; }
    }
    return false;
}

inline std::string py_strip(const std::string& s) {
    size_t b = 0, w = 0;
    while (b < s.size() && space_at(s, b, w)) b += w;
    size_t e = s.size();
    while (e > b) {  // walk back over whole UTF-8 characters
        size_t start = e - 1;
        while (start > b && (static_cast<unsigned char>(s[start]) & 0xC0) == 0x80) --start;
        if (space_at(s, start, w) && start + w == e) e = start; else break;
    }
    return s.substr(b, e - b);
}


// str.encode("utf-8") of text holding lone surrogates: UnicodeEncodeError's message, else "".
inline std::string surrogate_error(const std::string& text) {
    if (!has_surrogate(text)) return "";  // a byte scan; decoding to code points only when needed
    auto cps = pyjson::code_points(text);
    for (size_t i = 0; i < cps.size(); ++i) {
        if (!pyjson::is_surrogate(cps[i])) continue;
        size_t j = i;
        while (j < cps.size() && pyjson::is_surrogate(cps[j])) ++j;
        char buf[160];
        if (j - i == 1)
            std::snprintf(buf, sizeof buf, "'utf-8' codec can't encode character '\\u%04x' in position %zu: surrogates not allowed", static_cast<unsigned>(cps[i]), i);
        else
            std::snprintf(buf, sizeof buf, "'utf-8' codec can't encode characters in position %zu-%zu: surrogates not allowed", i, j - 1);
        return buf;
    }
    return "";
}
