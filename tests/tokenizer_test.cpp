// Token ids of texts, as `jev` tokenizes prompts (src/vocab.cpp): tests/tokenizer.py checks them.
//
//   tokenizer-test TOKENIZER.gguf TEXTS.txt
//
// TEXTS.txt: one text per line, JSON-escaped (tests/tokenizer.py writes it). Prints, per text, its token ids
// separated by spaces, one line each; a text the tokenizer refuses prints "error: <why>" instead.
#include <cstdio>
#include <fstream>
#include <string>

#include "json.hpp"
#include "vocab.hpp"
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main(int argc, char** argv) try {
    if (argc != 3) { std::fprintf(stderr, "usage: tokenizer-test TOKENIZER.gguf TEXTS.txt\n"); return 2; }
#ifdef _WIN32
    _setmode(_fileno(stdout), _O_BINARY);  // the same bytes on every OS: "\n", not "\r\n"
#endif
    Vocab vocab(argv[1]);
    std::ifstream in(argv[2], std::ios::binary);
    if (!in) { std::fprintf(stderr, "cannot read %s\n", argv[2]); return 1; }
    std::string line, out;
    while (std::getline(in, line)) {
        std::string text = nlohmann::json::parse(line).get<std::string>();
        out.clear();
        try {
            for (int32_t id : vocab.tokenize(text)) out += (out.empty() ? "" : " ") + std::to_string(id);
        } catch (const std::exception& e) {
            out = std::string("error: ") + e.what();
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    return 0;
} catch (const std::exception& e) {
    std::fprintf(stderr, "tokenizer-test: %s\n", e.what());
    return 1;
}
