---
title: "llama.cpp on Windows without compiling"
description: "Run llama.cpp on Windows from the official prebuilt zips: which archive to pick, how to check what it sees, and how jev runs on Windows."
parent: "llama.cpp and GGUF"
nav_order: 6
---

# llama.cpp on Windows without compiling

**You do not need Visual Studio to run llama.cpp on Windows: every llama.cpp release publishes
ready-made Windows zips for the CPU (x64 and arm64) and for GPU backends such as CUDA and
Vulkan; unzip one and its tools are ready.** `--list-devices` then shows which compute devices
the build can see, and `--device none` runs the model on the processor whatever else is
installed. jev needs none of this: `jev-windows-x64.zip` holds one native binary that runs the
model on the CPU, and the jevos-v2 release ships the model as GGUF files for llama.cpp.

Building llama.cpp yourself on Windows is supported but heavy: the build guide asks for Visual
Studio 2022 with the C++ desktop workload, CMake tools, Git, the Clang compiler and the LLVM
toolset for MSBuild, and GPU builds add the CUDA toolkit or the Vulkan SDK. For running a model,
none of that is necessary.

This page is the ways to get llama.cpp without compiling, which Windows archive does what, how
to check the result, how jev runs on Windows, and the usual snags.

## Three ways to get llama.cpp without a compiler

1. **The releases page.** Each build of llama.cpp is published as a tag (`b` plus a number) on
   GitHub with archives per platform and backend. Unzip one and the tools and libraries are
   ready.
2. **winget.** The Hugging Face llama.cpp guide gives `winget install llama.cpp` for Windows.
3. **A tool that bundles it.** LM Studio and Ollama run models with llama.cpp and install it for
   you, behind their own programs and APIs.

Options 1 and 2 give you llama.cpp's own programs, which is what the rest of this page is about;
loading its library from Python instead is compared on
[llama-cpp-python vs calling llama.cpp through ctypes](llama-cpp-python-vs-ctypes.md).

## Which Windows archive is which

For release `b11081`, for example, the Windows packages include:

| Machine | Family | Archive |
|---|---|---|
| x64 | CPU | `llama-b11081-bin-win-cpu-x64.zip` |
| arm64 | CPU | `llama-b11081-bin-win-cpu-arm64.zip` |
| x64 | Vulkan (AMD, Intel and NVIDIA GPUs) | `llama-b11081-bin-win-vulkan-x64.zip` |
| x64 | CUDA 13.4 | `llama-b11081-bin-win-cuda-13.4-x64.zip` plus `cudart-llama-bin-win-cuda-13.4-x64.zip` |
| x64 | ROCm 10.0 | `llama-b11081-bin-win-rocm-10.0-x64.zip` |
| x64 | SYCL | `llama-b11081-bin-win-sycl-x64.zip` |

The release itself has more (a CUDA 12.4 build, for example). The CUDA build comes as two zips
because the CUDA runtime libraries are shipped separately; both are unpacked into one folder.

## Checking what the runtime can see

llama.cpp's tools take `--list-devices`, which prints the compute devices the unpacked build can
see. Look for the device you expect, with the kind you expect, before measuring anything.

## Running on the CPU whatever is installed

On llama.cpp's tools, `--device` decides where the model runs, separately from which archive was
unpacked: `--device none` (or `-ngl 0`) keeps every weight on the processor, even in a GPU build.

jev runs on the CPU only (x86-64 with AVX2), with no GPU path, no Python and no download step.
Unzip `jev-windows-x64.zip`, unpack `jevos-v2-openvino-int8.zip` into the `jev` folder so that
it creates `jev\model`, and start the server from that folder. The jevos numbers were measured
on the CPU with no GPU; in PowerShell the command is:

```powershell
.\jev.exe serve
```

On a laptop, [running llama.cpp CPU only](llama-cpp-cpu-only.md) covers the thread setting, and
[what an LLM on a laptop can do in real time](an-llm-on-a-laptop.md) covers what to expect.

## Common snags on Windows

- **DLLs next to each other.** The release zips put `llama.dll`, the ggml libraries and the
  backend plug-ins in one folder, and the CUDA and OpenMP dependencies beside them. If you move
  files around by hand, keep them together. The same goes for the `jev` folder, where the
  binary sits beside OpenVINO's libraries.
- **Your own build.** jev builds from source with `python -m pip install -r requirements.txt`
  and `python scripts/build.py` (CMake, Ninja, a C++17 compiler), run on Windows from a Visual
  Studio developer prompt.
- **The wrong family picked.** If `--list-devices` shows a GPU you did not want to use, you do
  not need to reinstall: pass `--device none`.

Being straight about the limit: we have not published Windows-specific timings. The reference
numbers (26 ms for a short request, 112 ms for a long one) are from one laptop with an Intel
Core Ultra 7 255H and 16 threads, and apply to that machine.

## Short answers to the questions that lead here

**Can I run llama.cpp on Windows without building it?** Yes. Each release has Windows zips for
CPU and GPU backends, and winget can install it too.

**Which llama.cpp zip do I need on Windows?** For CPU only, `win-cpu-x64` (or `win-cpu-arm64`
on ARM). For an NVIDIA GPU, the CUDA zip plus its `cudart` zip. For other GPUs, Vulkan.

**Does jev need llama.cpp on Windows?** No. `jev-windows-x64.zip` holds the binary and
OpenVINO's libraries; llama.cpp's tokenizer is compiled in.

**How do I see which devices llama.cpp detects?** llama.cpp's own tools have a
`--list-devices` option.

**Does jevos need a GPU on Windows?** No. jev runs on the CPU only.

**See also:** [using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md),
[run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md) and
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md).

## Sources

- Our own facts: the contents of `jev-windows-x64.zip`, how to run it and how to build it, from
  the [jev repository](https://github.com/feder-cr/jev); latency on the reference laptop, from
  the README.
- [llama.cpp build guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md),
  fetched 2026-09-29: Windows build requirements, multiple backends, `--list-devices`.
- [llama.cpp release b11081](https://github.com/ggml-org/llama.cpp/releases/tag/b11081) and the
  [releases page](https://github.com/ggml-org/llama.cpp/releases), fetched 2026-09-29.
- [Hugging Face docs: GGUF usage with llama.cpp](https://huggingface.co/docs/hub/gguf-llamacpp),
  fetched 2026-09-29: `winget install llama.cpp`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships for Windows as one folder:
the binary, OpenVINO's libraries and the licenses.*
