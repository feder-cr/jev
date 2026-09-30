#include "vocab.hpp"

#include <cstdio>
#include <cstdlib>
#include <stdexcept>

// Warnings and errors only (JEV_LLAMA_LOG=1: everything).
static void log_filter(ggml_log_level level, const char* text, void*) {
    static const bool verbose = [] { const char* v = std::getenv("JEV_LLAMA_LOG"); return v && std::string(v) == "1"; }();
    if (verbose || level == GGML_LOG_LEVEL_WARN || level == GGML_LOG_LEVEL_ERROR) std::fputs(text, stderr);
}

Vocab::Vocab(const std::filesystem::path& gguf) {
    llama_log_set(&log_filter, nullptr);
    auto mp = llama_model_default_params();
    mp.vocab_only = true;
    model_ = llama_model_load_from_file(gguf.string().c_str(), mp);
    if (!model_) throw std::runtime_error("cannot read the vocabulary " + gguf.string() + " (export/export_openvino.py writes it)");
    vocab_ = llama_model_get_vocab(model_);
    char piece[256];
    int n = llama_token_to_piece(vocab_, llama_vocab_bos(vocab_), piece, sizeof piece, 0, true);
    bos_ = n > 0 ? std::string(piece, n) : "";
}

Vocab::~Vocab() {
    if (model_) llama_model_free(model_);
}

Tokens Vocab::tokenize(const std::string& text) const {
    Tokens out(text.size() + 8);  // a token covers at least one byte
    int n = llama_tokenize(vocab_, text.data(), static_cast<int32_t>(text.size()), out.data(), static_cast<int32_t>(out.size()), false, true);
    if (n < 0) {
        out.resize(-n);
        n = llama_tokenize(vocab_, text.data(), static_cast<int32_t>(text.size()), out.data(), static_cast<int32_t>(out.size()), false, true);
    }
    if (n < 0) throw std::runtime_error("llama_tokenize failed");
    out.resize(n);
    return out;
}
