---
title: "llama-cpp-python vs calling llama.cpp through ctypes"
description: "llama-cpp-python wraps llama.cpp and usually compiles it on install; jev loads the official prebuilt library through a small ctypes layer."
parent: "llama.cpp and GGUF"
nav_order: 5
---

# llama-cpp-python vs calling llama.cpp through ctypes

**llama-cpp-python is a full Python package around llama.cpp, with a high-level API and an
OpenAI-compatible server, and a plain `pip install` builds llama.cpp from source; jev instead
downloads llama.cpp's official prebuilt release and calls it through a small ctypes layer of its
own that covers only what scoring needs.** Both end up calling the same C API from Python. The
difference is who builds the native library, how much of the API is wrapped, and who has to
keep up when llama.cpp changes.

The part people miss is that llama-cpp-python's own low-level layer is also ctypes. Its README
says so: "The low-level API is a direct ctypes binding to the C API provided by llama.cpp." So
the choice is not ctypes against something safer. It is a maintained, broad binding with a
compile step, against a narrow binding pinned to one binary release.

This page is what each approach gives you, how jev's runtime is put together, the costs of
writing your own binding, a side-by-side table, and when to pick which.

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

jev never compiles anything. `uv run jev download --only runtime` fetches the archive for this
machine from llama.cpp's GitHub releases for the pinned build `b11081` (commit `161755f`), plus
the separate CUDA runtime archive for CUDA builds, checks each against a sha256 recorded in
jev's code, and unpacks them under `runtimes/`. The archives are the same ones anyone can
download from the releases page; jev picks the one that matches the operating system,
the processor and the accelerator family.

The binding is a single Python module. Its header comment says it is "limited to what scoring
needs: no sampling, no generation", and that struct layouts and signatures "are transcribed from
`include/llama.h` and `ggml/include/ggml-backend.h`" of that exact release. At load time it opens
the ggml and llama libraries in the runtime folder, looks up each function it needs and fails
with a clear message if a symbol is missing, then loads the compute backends that the release
ships as plug-ins next to the library.

That is enough for a decision model, because jevos generates nothing: every answer is a
probability read from the model's forward pass, with `output_tokens` always 0. Why that is
enough is covered on [why one forward pass beats generating an
answer](why-one-forward-pass-beats-generation.md).

## What writing your own binding costs

Being straight about the downside: a hand-written binding is only correct for the release it was
transcribed from.

- **Structs by value.** llama.cpp passes parameter structs by value. If a field is added or
  reordered in a new release and the Python side is not updated, the call does not fail
  cleanly; it can read garbage or crash. jev's module states this risk in its own header, and
  the Python documentation warns that ctypes use can "corrupt data and objects" or "cause
  crashes".
- **API drift is real.** llama.cpp keeps a public changelog of the `libllama` API (issue 9289)
  that lists additions, parameter changes to `llama_model_params` and `llama_context_params`,
  removals and renames. Every upgrade means reading it and re-transcribing.
- **Narrow coverage.** Only the calls jev uses are bound. There is no sampler, no chat API, no
  embeddings. If you need those, you would be rebuilding llama-cpp-python.

In exchange, the runtime is exactly one known binary, the install needs no compiler, and the
same archive can be checked by hash on every machine. This is the same reasoning as on
[using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md).

## Side by side

| | llama-cpp-python | jev's ctypes layer |
|---|---|---|
| Native library | built on install, or a pre-built wheel | official llama.cpp release archive |
| Compiler needed | yes, unless a wheel matches | no |
| llama.cpp version | the vendored submodule of the package version | one pinned release, `b11081` |
| API covered | low-level plus high-level plus server | only what scoring needs |
| Generation and sampling | yes | none |
| Upgrading llama.cpp | upgrade the package | re-transcribe layouts, change the pin |
| Override | build with your own flags | `JEV_LLAMA_DIR` pointing at a build of the same commit |

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

**Can I point jev at my own llama.cpp build?** Yes, with `JEV_LLAMA_DIR`, but it must be a build
of the same commit, `161755f`, because the struct layouts are copied from that release.

**Why not use llama-cpp-python inside jev?** It would add a compile step or a wheel constraint
to every install, and most of what it wraps would go unused.

**What happens if the runtime and the binding do not match?** A missing function is reported by
name at load. A changed struct layout may not be caught and can crash, which is why the release
is pinned.

**See also:** [llama.cpp vs Ollama for a classification service](llama-cpp-vs-ollama-for-classification.md),
[running llama.cpp CPU only](llama-cpp-cpu-only.md) and
[jev serve vs llama.cpp server](jev-serve-vs-llama-cpp-server.md).

## Sources

- Our own facts: how jev downloads, verifies and binds the runtime, from `llama_release.py`,
  `llama_cpp.py` and `cli.py` in the [jev repository](https://github.com/feder-cr/jev);
  zero output tokens, from the README.
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

*From the notes of [jev](https://github.com/feder-cr/jev), whose whole native dependency is an
official llama.cpp release whose archive hashes are written in the code.*
