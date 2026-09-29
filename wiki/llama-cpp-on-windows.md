---
title: "llama.cpp on Windows without compiling"
description: "Run llama.cpp on Windows from the official prebuilt zips: which archive to pick, what jev download --only runtime chooses, and how jev devices checks it."
parent: "llama.cpp and GGUF"
nav_order: 6
---

# llama.cpp on Windows without compiling

**You do not need Visual Studio to run llama.cpp on Windows: every llama.cpp release publishes
ready-made Windows zips for the CPU (x64 and arm64) and for GPU backends such as CUDA and
Vulkan, and `uv run jev download --only runtime` picks, verifies and unpacks the right one for
you.** After that, `uv run jev devices` shows which compute devices the runtime can see, and
`jev serve --device cpu` runs the model on the processor whatever else is installed.

Building llama.cpp yourself on Windows is supported but heavy: the build guide asks for Visual
Studio 2022 with the C++ desktop workload, CMake tools, Git, the Clang compiler and the LLVM
toolset for MSBuild, and GPU builds add the CUDA toolkit or the Vulkan SDK. For running a model,
none of that is necessary.

This page is the ways to get llama.cpp without compiling, which Windows archive does what, what
jev's download command actually decides, how to check the result, and the usual snags.

## Three ways to get llama.cpp without a compiler

1. **The releases page.** Each build of llama.cpp is published as a tag (`b` plus a number) on
   GitHub with archives per platform and backend. Unzip one and the tools and libraries are
   ready.
2. **winget.** The Hugging Face llama.cpp guide gives `winget install llama.cpp` for Windows.
3. **jev's download command.** `uv run jev download --only runtime` fetches the archive of one
   pinned release that matches this machine. It is the same official archive as option 1; jev
   only automates the choice and the check.

Options 1 and 2 are for using llama.cpp's own programs. Option 3 installs the same files for
jev, which loads the library inside them; the difference between that and a Python binding is on
[llama-cpp-python vs calling llama.cpp through ctypes](llama-cpp-python-vs-ctypes.md).

## Which Windows archive is which

For the release jev pins, `b11081`, the Windows packages jev knows about are:

| Machine | Family | Archive |
|---|---|---|
| x64 | CPU | `llama-b11081-bin-win-cpu-x64.zip` |
| arm64 | CPU | `llama-b11081-bin-win-cpu-arm64.zip` |
| x64 | Vulkan (AMD, Intel and NVIDIA GPUs) | `llama-b11081-bin-win-vulkan-x64.zip` |
| x64 | CUDA 13.4 | `llama-b11081-bin-win-cuda-13.4-x64.zip` plus `cudart-llama-bin-win-cuda-13.4-x64.zip` |
| x64 | ROCm 10.0 | `llama-b11081-bin-win-rocm-10.0-x64.zip` |
| x64 | SYCL | `llama-b11081-bin-win-sycl-x64.zip` |

The release itself has more (a CUDA 12.4 build, for example); these are the ones jev can
install. The CUDA build comes as two zips because the CUDA runtime libraries are shipped
separately; both are unpacked into one folder.

## What jev download --only runtime decides

The command's logic is short and worth knowing, because it may not pick the CPU build.

- With the default `--runtime auto`, on Windows it chooses **CUDA if an NVIDIA driver is
  installed** (it checks that `nvcuda.dll` loads; no CUDA toolkit needed), **otherwise Vulkan**.
  The code notes that the Vulkan build falls back to the CPU when there is no GPU.
- `--runtime cpu` (or `vulkan`, `cuda`, `rocm`, `sycl`) asks for a specific family and fails
  with the list of available ones if this machine has no such package. On Windows arm64 only
  the CPU package exists.
- Each archive is checked against a sha256 written in jev's code. An interrupted download
  resumes from the bytes already on disk; a file with the wrong hash is deleted, never used.
- The result is unpacked under `runtimes\llama-b11081-win32-x64-<family>`. Running the command
  again when that folder is complete downloads nothing.

If you want the smallest and simplest install for a CPU-only machine, ask for it:

```bash
uv run jev download --only runtime --runtime cpu
```

## Checking what the runtime can see

`uv run jev devices` loads the installed runtime and prints a JSON report: the llama.cpp
release, the installed runtime families, the runtime folder in use, and one entry per compute
device with its `name`, `description`, `kind` (`cpu`, `gpu`, `igpu` or `accel`), `backend` and
`total_bytes`. If no runtime is installed, the report carries an `error` field with the command
to run instead.

Two things to look for. First, that the device you expect is there, with the kind you expect:
jev's `auto` device choice treats `gpu` and `igpu` entries differently, preferring a discrete
GPU. Second, that the release is the one
you pinned; the same value appears later as `llama_cpp_release` in the server's `/health`.

## Running on the CPU whatever is installed

`--device` decides where the model runs, separately from which runtime was downloaded. With
`--device cpu`, jev gives llama.cpp an empty device list and keeps every weight on the
processor, even if a GPU runtime is installed. The jevos numbers were measured on the CPU with
no GPU, and the README's command is:

```bash
uv run jev serve --gguf jevos-v2-q4_k_m.gguf --device cpu --threads 16
```

The default `--device auto` prefers a discrete GPU, then an integrated one, then the CPU. On a
laptop, [running llama.cpp CPU only](llama-cpp-cpu-only.md) covers the thread setting, and
[what an LLM on a laptop can do in real time](an-llm-on-a-laptop.md) covers what to expect.

## Common snags on Windows

- **DLLs next to each other.** The release zips put `llama.dll`, the ggml libraries and the
  backend plug-ins in one folder, and the CUDA and OpenMP dependencies beside them. jev adds that
  folder to the DLL search path before loading. If you move files around by hand, keep them
  together.
- **Your own build.** `JEV_LLAMA_DIR` can point at a folder you built, but it must be the same
  commit, `161755f`, because jev's bindings are copied from that release's headers.
- **The wrong family picked.** If `jev devices` shows a GPU you did not want to use, you do not
  need to reinstall: start the server with `--device cpu`.

Being straight about the limit: we have not published Windows-specific timings. The reference
numbers (54 ms for a short request, 220 ms for a long one) are from one laptop with an Intel
Core Ultra 7 255H and 16 threads, and apply to that machine.

## Short answers to the questions that lead here

**Can I run llama.cpp on Windows without building it?** Yes. Each release has Windows zips for
CPU and GPU backends, and winget can install it too.

**Which llama.cpp zip do I need on Windows?** For CPU only, `win-cpu-x64` (or `win-cpu-arm64`
on ARM). For an NVIDIA GPU, the CUDA zip plus its `cudart` zip. For other GPUs, Vulkan.

**Why did jev download the Vulkan build on a PC without a GPU?** That is the default choice
when no NVIDIA driver is found; the Vulkan build falls back to the CPU. Use `--runtime cpu` for
the CPU package.

**How do I see which devices llama.cpp detects?** `uv run jev devices` prints them as JSON.
llama.cpp's own tools have a `--list-devices` option.

**Does jevos need a GPU on Windows?** No. It is built to run with `--device cpu`.

**See also:** [using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md),
[run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md) and
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md).

## Sources

- Our own facts: the package list, the automatic choice, hash checks, resume, install folder
  and the `jev devices` report, from `llama_release.py`, `loader.py`, `llama_cpp.py` and
  `cli.py` in the [jev repository](https://github.com/feder-cr/jev); latency on the reference
  laptop, from the README.
- [llama.cpp build guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md),
  fetched 2026-09-29: Windows build requirements, multiple backends, `--list-devices`.
- [llama.cpp release b11081](https://github.com/ggml-org/llama.cpp/releases/tag/b11081) and the
  [releases page](https://github.com/ggml-org/llama.cpp/releases), fetched 2026-09-29.
- [Hugging Face docs: GGUF usage with llama.cpp](https://huggingface.co/docs/hub/gguf-llamacpp),
  fetched 2026-09-29: `winget install llama.cpp`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which pins one llama.cpp release and
checks the hash of every archive it downloads.*
