// jev: yes/no decisions on the CPU. jevos runs through OpenVINO (model.cpp: INT8 weights, the graph
// export/export_openvino.py writes), with the Python engine's prompt and tokens (vocab.cpp): several
// questions on one state read the state once, a state asked again resumes from its snapshot, a long
// state is read in pieces, and requests arriving together share a call. One scheduler thread makes every
// model call (scheduler.hpp); validation (wire.cpp) and tokenization run on the requests' own threads.
//
//   jev serve  [--host 127.0.0.1] [--port 8017] [model options]
//              [--warmup 384]       (prompt lengths 1..N compiled while idle; 0 = off)
//              [--batch-tokens 384] (most tokens of requests read together in one call; 0 = one at a time)
//              [--state-cache 16] [--state-cache-tokens 8192]  (states kept for later requests, how many
//                                    and how many state tokens in all; 0 = off)
//   jev decide REQUEST.json [--output FILE] [model options]
//   model options: [--model-dir DIR (model/ beside the binary)] [--name NAME (the folder's model.json)]
//                  [--threads N (all logical CPUs)] [--ctx 8192]
//                  [--dynamic-quantization 128] (activations in INT8 groups of N values; 0 = f32: slower, and
//                                    answers no longer move in their last digits with how a call is composed)
//                  [--hint latency|throughput (latency)] [--streams N (1)]  (OpenVINO's performance hint and
//                                    inference stream count: streams share a call's work, more decisions a
//                                    second under concurrent load, slower single requests)
//
// JEV_API_KEY set: `jev serve` requires `Authorization: Bearer <key>` on every call but /health.
// /health reports the SHA-256 of the model folder's files and their fingerprint (model_files, below).
// DIR holds openvino_model.xml/.bin, tokenizer.gguf (the model's vocabulary) and model.json (its name),
// written by export/export_openvino.py.

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <future>
#include <iterator>
#include <stdexcept>
#include <string>
#include <thread>

#include "model.hpp"
#include "scheduler.hpp"
#include "server.hpp"
#include "sha256.hpp"
#include "vocab.hpp"
#include "wire.hpp"

namespace fs = std::filesystem;

static std::string read_file(const fs::path& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error(path.string() + ": cannot read it");
    return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}

// The name answers carry: the model folder's model.json (export_openvino.py --name).
static std::string model_name(const fs::path& dir) {
    auto meta = ojson::parse(read_file(dir / "model.json"), nullptr, false);
    if (!meta.is_object() || !meta.contains("name") || !meta["name"].is_string())
        throw std::runtime_error((dir / "model.json").string() + ": no \"name\"; write the model with export/export_openvino.py");
    return meta["name"].get<std::string>();
}

// The SHA-256 of each file the server reads from the model folder, and a fingerprint of them all: the
// SHA-256 of their `sha256sum` lines ("<hash>  <name>\n", by name), so `sha256sum model.json
// openvino_model.bin openvino_model.xml tokenizer.gguf | sha256sum` gives the same value.
static ojson model_files(const fs::path& dir) {
    ojson files = ojson::object();
    std::string lines;
    for (const char* name : {"model.json", "openvino_model.bin", "openvino_model.xml", "tokenizer.gguf"}) {
        std::string hash = Sha256::of_file(dir / name);
        files[name] = hash;
        lines += hash + "  " + name + "\n";
    }
    Sha256 all;
    all.update(reinterpret_cast<const unsigned char*>(lines.data()), lines.size());
    return {{"model_files", files}, {"fingerprint", all.hex()}};
}

// json.JSONDecodeError's message: "Expecting value: line 1 column 1 (char 0)", positions in characters.
static std::string decode_error(const std::string& text, const pyjson::DecodeError& e) {
    std::u32string chars = pyjson::code_points(text);
    size_t line = 1, column = 1;
    for (size_t i = 0; i < e.pos && i < chars.size(); ++i) {
        if (chars[i] == U'\n') { ++line; column = 1; } else ++column;
    }
    return e.msg + ": line " + std::to_string(line) + " column " + std::to_string(column) + " (char " + std::to_string(e.pos) + ")";
}

// The answer as `jev decide` writes it: json.dumps(answer, ensure_ascii=False, indent=2), a newline after.
// Answers are create-only: an existing file is never written over.
static void write_answer(const std::string& body, const std::string& output) {
    pyjson::DumpOptions pretty{2, false, ", ", ": ", false};
    std::string text = pyjson::dumps(pyjson::loads(body), pretty) + "\n";
    if (output.empty()) {
        std::fwrite(text.data(), 1, text.size(), stdout);
        return;
    }
    fs::path path(output);
    if (path.has_parent_path()) fs::create_directories(path.parent_path());
    FILE* f = std::fopen(path.string().c_str(), "wbx");
    if (!f) throw std::runtime_error(output + ": exists or cannot be created; an answer is never written over a file");
    std::fwrite(text.data(), 1, text.size(), f);
    std::fclose(f);
}

int main(int argc, char** argv) try {
    const char* usage = "usage: jev serve [options] | jev decide REQUEST.json [--output FILE] [options] (options: top of src/main.cpp)\n";
    if (argc < 2 || (std::string(argv[1]) != "serve" && std::string(argv[1]) != "decide")) { std::fputs(usage, stderr); return 2; }
    const std::string command = argv[1];
    std::string host = "127.0.0.1", name, input, output, hint = "LATENCY";
    int port = 8017, threads = static_cast<int>(std::max(1u, std::thread::hardware_concurrency())), streams = 1;
    // batch_tokens: requests read together pay off while they are small (measured, one call vs separate
    // calls: 4 x 64 tokens -11%, 3 x 120 -16%, 2 x 150 +3%, 4 x 200 +17%): the matmuls gain rows, the
    // attention of every block runs over all the call's cells.
    size_t ctx = 8192, warmup = Model::WARM_TOKENS, batch_tokens = 384;
    size_t state_cache = 16, state_cache_tokens = 8192;  // state snapshots: how many, how many state tokens in all
    size_t quantization_group = 128;
    fs::path model_dir = fs::absolute(fs::path(argv[0])).parent_path() / "model";
    for (int i = 2; i < argc; ++i) {
        std::string a = argv[i];
        auto next = [&]() -> std::string { if (i + 1 >= argc) throw std::runtime_error(a + " needs a value"); return argv[++i]; };
        bool serving = command == "serve";
        if (a == "--model-dir") model_dir = next();
        else if (a == "--name") name = next();
        else if (a == "--threads") threads = std::stoi(next());
        else if (a == "--ctx") ctx = std::stoul(next());
        else if (a == "--dynamic-quantization") quantization_group = std::stoul(next());
        else if (a == "--hint") { hint = next(); std::transform(hint.begin(), hint.end(), hint.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
                                  if (hint != "LATENCY" && hint != "THROUGHPUT") throw std::runtime_error(a + " is latency or throughput"); }
        else if (a == "--streams") streams = std::stoi(next());
        else if (serving && a == "--host") host = next();
        else if (serving && a == "--port") port = std::stoi(next());
        else if (serving && a == "--warmup") warmup = std::stoul(next());
        else if (serving && a == "--batch-tokens") batch_tokens = std::stoul(next());
        else if (serving && a == "--state-cache") state_cache = std::stoul(next());
        else if (serving && a == "--state-cache-tokens") state_cache_tokens = std::stoul(next());
        else if (!serving && a == "--output") output = next();
        else if (!serving && input.empty() && a.rfind("--", 0) != 0) input = a;
        else { std::fprintf(stderr, "jev %s: unknown option %s\n%s", command.c_str(), a.c_str(), usage); return 2; }
    }
    if (command == "decide" && input.empty()) { std::fputs(usage, stderr); return 2; }
    if (name.empty()) name = model_name(model_dir);

    // decide: the request is read and its wire model checked before the model loads.
    Value body;
    if (command == "decide") {
        std::string text = read_file(input);
        try {
            body = pyjson::loads(text);
        } catch (const pyjson::DecodeError& e) {
            throw std::runtime_error(input + ": " + decode_error(text, e));
        } catch (const pyjson::BodyError&) {
            throw std::runtime_error(input + ": not readable as JSON (bad UTF-8, or an integer of more than 4300 digits)");
        }
        Errs errs;
        check_wire(body, errs);
        if (!errs.empty()) {
            std::fprintf(stderr, "jev: %s\n", rendered_error(unprocessable(std::move(errs))).c_str());
            return 1;
        }
    }

    auto load_start = std::chrono::steady_clock::now();
    // serve: the files it reads are hashed while OpenVINO compiles the model (/health reports them)
    std::future<ojson> files;
    if (command == "serve") files = std::async(std::launch::async, model_files, model_dir);
    Vocab vocab(model_dir / "tokenizer.gguf");
    std::fprintf(stderr, "jev: loading %s (OpenVINO %s)\n", model_dir.string().c_str(), Model::openvino_version().c_str());
    Model model(model_dir, threads, hint, streams, command == "serve" ? state_cache : 0, state_cache_tokens, quantization_group);
    if (command == "decide") {
        Scheduler scheduler(model, 0, 0);
        Api api{model, vocab, scheduler, name, ctx, ojson::object()};
        Timing tm;
        try {
            write_answer(api.systemone(body, tm), output);
        } catch (const ApiError& e) {
            std::fprintf(stderr, "jev: %s\n", rendered_error(e).c_str());
            return 1;
        }
        return 0;
    }
    model.warmup();
    ojson hashes = files.get();
    const char* key = std::getenv("JEV_API_KEY");
    const std::string api_key = key ? key : "";
    std::fprintf(stderr, "jev: %s on http://%s:%d (%s), ready in %.1f s: %d threads, %s\n", name.c_str(), host.c_str(), port,
                 api_key.empty() ? "no auth" : "Bearer auth",
                 std::chrono::duration<double>(std::chrono::steady_clock::now() - load_start).count(), threads, model.describe().dump().c_str());
    Scheduler scheduler(model, warmup, batch_tokens);
    Api api{model, vocab, scheduler, name, ctx, std::move(hashes)};
    return serve(api, {host, api_key, port}) ? 0 : 1;
} catch (const std::exception& e) {
    std::fprintf(stderr, "jev: %s\n", e.what());
    return 1;
}
