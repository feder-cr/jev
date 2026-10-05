---
title: "llama-cpp-python vs calling llama.cpp through ctypes"
description: "llama-cpp-python wraps llama.cpp and usually compiles it on install; a small ctypes layer of your own can load the official prebuilt library instead."
parent: "llama.cpp and GGUF"
nav_order: 5
---

# llama-cpp-python vs calling llama.cpp through ctypes

**llama-cpp-python is a full Python package around llama.cpp, with a high-level API and an
OpenAI-compatible server, and a plain `pip install` builds llama.cpp from source; the
alternative is to download llama.cpp's official prebuilt release and call it through a small
ctypes layer of your own that covers only what you need, such as scoring.** Both end up calling the same C API from Python. The
difference is who builds the native library, how much of the API is wrapped, and who has to
keep up when llama.cpp changes.

The part people miss is that llama-cpp-python's own low-level layer is also ctypes. Its README
says so: "The low-level API is a direct ctypes binding to the C API provided by llama.cpp." So
the choice is not ctypes against something safer. It is a maintained, broad binding with a
compile step, against a narrow binding pinned to one binary release.

This page is what each approach gives you, what jev does and how a thin binding is put
together, the costs of writing your own binding, a side-by-side table, and when to pick which.

## What llama-cpp-python gives you

The project describes itself as "Simple Python bindings for @ggerganov's llama.cpp library" and
offers three layers: low-level ctypes access to the C API, a high-level Python API with
OpenAI-style completion and chat calls, and a web server meant as an OpenAI API drop-in. On top
it lists chat completion, function calling, vision models, JSON schema constraints and
speculative decoding.

Installing it is where the trade-off sits. `pip install llama-cpp-python` "will also build
llama.cpp from source and install it alongside this python package", which needs a C compiler:
gcc or clang on Linux, Visual Studio or MinGW on Windows, Xcode on macOS. GPU backends are chosen
with `CMAKE_ARGS` at install time (CUDA, Metal, ROCm, Vulkan, SYCL, OpenBLAS). There are
pre-built wheels from an extra index for CPU and for CUDA, with stated limits on CUDA versions,
GPU compute capability and Python versions. The llama.cpp source it builds is a git submodule
under `vendor/llama.cpp`.

## What jev does instead

jev takes neither route: it has no Python in it at run time. It is one native binary that runs
jevos-v4 with 8-bit (INT8) weights through OpenVINO and compiles in llama.cpp's tokenizer, so
its token ids match the GGUF files. For Python users, the jevos-v4 release also ships the model
as GGUF files, `jevos-v4-q4_k_m.gguf` and `jevos-v4-q8_0.gguf`, which either approach on this
page can load; jev itself does not read GGUF files.

A thin binding of your own is usually a single Python module, limited to what scoring needs: no
sampling, no generation. Its struct layouts and signatures are transcribed from
`include/llama.h` and `ggml/include/ggml-backend.h` of one exact release. At load time it opens
the ggml and llama libraries in the runtime folder, looks up each function it needs and fails
with a clear message if a symbol is missing, then loads the compute backends that the release
ships as plug-ins next to the library.

That is enough for a decision model such as jevos, which generates nothing: every answer is a
probability read without generating any text, with `output_tokens` always 0. Why that is
enough is covered on [why one forward pass beats generating an
answer](why-one-forward-pass-beats-generation.md).

## What writing your own binding costs

Being straight about the downside: a hand-written binding is only correct for the release it was
transcribed from.

- **Structs by value.** llama.cpp passes parameter structs by value. If a field is added or
  reordered in a new release and the Python side is not updated, the call does not fail
  cleanly; it can read garbage or crash. The Python documentation warns that ctypes use can "corrupt data and objects" or "cause
  crashes".
- **API drift is real.** llama.cpp keeps a public changelog of the `libllama` API (issue 9289)
  that lists additions, parameter changes to `llama_model_params` and `llama_context_params`,
  removals and renames. Every upgrade means reading it and re-transcribing.
- **Narrow coverage.** Only the calls you use are bound. There is no sampler, no chat API, no
  embeddings. If you need those, you would be rebuilding llama-cpp-python.

In exchange, the runtime is exactly one known binary, the install needs no compiler, and the
same archive can be checked by hash on every machine. This is the same reasoning as on
[using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md).

## Side by side

| | llama-cpp-python | your own ctypes layer |
|---|---|---|
| Native library | built on install, or a pre-built wheel | official llama.cpp release archive |
| Compiler needed | yes, unless a wheel matches | no |
| llama.cpp version | the vendored submodule of the package version | one pinned release |
| API covered | low-level plus high-level plus server | only what scoring needs |
| Generation and sampling | yes | none |
| Upgrading llama.cpp | upgrade the package | re-transcribe layouts, change the pin |
| Override | build with your own flags | a build of the same commit |

## Which one should you use?

- **You want to generate text, chat, or use many models from Python.** Use llama-cpp-python.
  It is the general tool, and reimplementing it is not worth it.
- **You need one narrow operation, on machines where installing a compiler is a problem.** A
  thin ctypes layer over the official binaries is reasonable, if you accept owning it. Windows
  desktops are the common case; see [llama.cpp on Windows without
  compiling](llama-cpp-on-windows.md).
- **You only need decisions over HTTP.** Neither: run `jev serve` and call it from any
  language. The [Python client guide](python-client-for-local-llm-decisions.md) shows the calls.

## Short answers to the questions that lead here

**Does llama-cpp-python need a compiler?** A plain `pip install` builds llama.cpp from source,
so yes. Pre-built CPU and CUDA wheels are published on an extra index, within stated version
limits.

**Is ctypes slower than a compiled extension?** The heavy work runs inside llama.cpp either
way. Python only pays for crossing into the library; we have not measured that cost on its own.

**Does jev use ctypes?** No. jev is one native binary with no Python at run time; it runs 8-bit
OpenVINO weights and uses llama.cpp only as its compiled-in tokenizer.

**Can I load jevos with llama-cpp-python?** The jevos-v4 release ships GGUF files, the format
llama.cpp loads; you get the model, not jev's decision endpoint.

**What happens if the runtime and the binding do not match?** A missing function is reported by
name at load. A changed struct layout may not be caught and can crash, which is why the release
is pinned.

**See also:** [llama.cpp vs Ollama for a classification service](llama-cpp-vs-ollama-for-classification.md),
[running llama.cpp CPU only](llama-cpp-cpu-only.md) and
[jev serve vs llama.cpp server](jev-serve-vs-llama-cpp-server.md).

## Sources

- Our own facts: what jev runs and the GGUF files in its release, from the
  [jev repository](https://github.com/feder-cr/jev); zero output tokens, from the README.
- [llama-cpp-python README](https://github.com/abetlen/llama-cpp-python), fetched 2026-09-29:
  description, layers, install behaviour, requirements, backends, wheels, vendored submodule,
  low-level ctypes API.
- [llama.cpp libllama API changelog, issue 9289](https://github.com/ggml-org/llama.cpp/issues/9289),
  fetched 2026-09-29.
- [Python ctypes documentation](https://docs.python.org/3/library/ctypes.html), fetched
  2026-09-29: description and safety warning.
- [llama.cpp release b11081](https://github.com/ggml-org/llama.cpp/releases/tag/b11081),
  fetched 2026-09-29: tag, commit and asset names.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which borrows only llama.cpp's
tokenizer and ships its model as GGUF files for anyone who wants the Python route.*
