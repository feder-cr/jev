// The model's vocabulary, read by llama.cpp's tokenizer (vocab_only) from the model folder's
// tokenizer.gguf: the Python engine's tokenizer, so prompts get the same token ids. llama.cpp is linked
// in (pinned in CMakeLists.txt) without any compute backend.
#pragma once
#include <filesystem>
#include <string>

#include "llama.h"
#include "tokens.hpp"

class Vocab {
public:
    explicit Vocab(const std::filesystem::path& gguf);
    ~Vocab();
    Vocab(const Vocab&) = delete;
    Vocab& operator=(const Vocab&) = delete;

    // llama_tokenize as the Python engine calls it: no special tokens added, control tokens written in
    // the text (the BOS) parsed as their own ids. Read-only: requests tokenize on their own threads.
    Tokens tokenize(const std::string& text) const;
    const std::string& bos() const { return bos_; }  // the BOS token's text, which prompts start with

private:
    llama_model* model_ = nullptr;
    const llama_vocab* vocab_ = nullptr;
    std::string bos_;
};
