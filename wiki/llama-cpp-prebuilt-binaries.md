---
title: "Using llama.cpp prebuilt binaries instead of building"
description: "llama.cpp publishes prebuilt archives per platform and backend for every build. How to pick one, pin it, verify it, and when building is still worth it."
parent: "llama.cpp and GGUF"
nav_order: 8
---

# Using llama.cpp prebuilt binaries instead of building

**Every llama.cpp build is published on GitHub as a release tagged `b` plus a number, with
ready-made archives for each operating system and backend, so you can run llama.cpp without a
compiler by downloading the archive that matches your machine.** For a service, the useful habit
is to pin one release, record the sha256 of the archive you use, and report the release at
runtime. jev itself does not load llama.cpp's runtime (it runs 8-bit OpenVINO weights and
compiles in only llama.cpp's tokenizer), but the jevos-v2 release ships the model as GGUF files,
and those are what you would run on a prebuilt llama.cpp.

Why it matters: a model's answers depend on two things, the GGUF file and the runtime that
executes it. Most teams pin the first and let the second float. Pinning the runtime too turns
"the model changed its answer" into a question you can actually investigate.

This page is what the releases offer, how to pick an archive, why and how to pin one, a
pattern for verifying it, and when building from source is still the better choice.

## What the releases page offers

llama.cpp's README lists "Download pre-built binaries from the releases page" among its install
options, next to Docker and building from source. Each release carries
archives grouped by platform and backend. On 2026-09-29 the list covered, among others:

- **macOS**: Apple Silicon (arm64) and Intel (x64).
- **Linux (Ubuntu builds)**: CPU for x64, arm64 and s390x; Vulkan; CUDA 12 and 13; ROCm;
  SYCL; OpenVINO.
- **Windows**: CPU for x64 and arm64; CUDA 12 and 13; Vulkan; SYCL; ROCm; OpenCL for Adreno on
  arm64.
- **Android**, and an iOS XCFramework.

CUDA builds come with a separate archive of CUDA runtime libraries, so the machine needs an
NVIDIA driver but not a CUDA toolkit. The newest tag listed that day was `b11240`; releases are
frequent, which is exactly why pinning matters.

## How to pick an archive

Match three things: operating system, processor (x64 or arm64) and backend.

- **No GPU, or you want the CPU on purpose**: the plain CPU archive. It is the smallest and has
  no driver dependencies; see [running llama.cpp CPU only](llama-cpp-cpu-only.md).
- **NVIDIA GPU**: the CUDA archive plus its `cudart` archive, unpacked into the same folder.
- **Any other GPU, or unsure**: Vulkan covers AMD, Intel and NVIDIA GPUs.
- **Apple Silicon**: the macOS arm64 archive, which uses Metal.

The Windows walk-through is on
[llama.cpp on Windows without compiling](llama-cpp-on-windows.md).

## Why pin one release

- **The API moves.** llama.cpp keeps a changelog issue for the public `libllama` API that lists
  new functions, changed parameter structs, removals and renames. Anything that links against
  the library, including bindings, is written for a particular release.
- **The arithmetic changes.** Releases change the code that computes the model. Nothing
  promises that the same GGUF gives identical probabilities on two releases, and we have not
  measured how far they move, so a threshold tuned on one release should be re-checked on the
  next.
- **Audits need an answer.** If a probability is questioned months later, "model file X on
  llama.cpp release Y" is a complete answer; "model file X on whatever was installed" is not.
  What else to record is on [logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## How to pin and verify

A short pattern for a service:

1. **One release, one commit.** Keep the release tag (for example `b11081`) and its commit as
   constants in your deployment. Code that binds to the library's structs, such as ctypes
   bindings, is transcribed from that release's headers, so for it the pin is not optional.
2. **A hash per archive.** Write down the sha256 of every archive you install, per operating
   system, processor and family. A download with a different hash is deleted and the install
   fails; nothing unverified is unpacked.
3. **Robust download.** Resume interrupted transfers from the bytes already on disk, unpack into
   a staging folder, move into place only when the library is found, and refuse archive entries
   that would land outside the target folder.
4. **Reported at runtime.** Have the service report the llama.cpp release, the commit, the
   device and the sha256 of the GGUF, so two servers can be shown to run the same model on the
   same runtime setup.

Because the archive hashes are known in advance, the same install works in an
[offline or air-gapped environment](offline-ai-for-decisions.md): download once, carry the
runtime folder and the GGUF, check the hashes.

## When building from source is still the better choice

Being straight about it: prebuilt archives are the right default, not the only answer.

- **No archive for your platform.** The archives cover the common operating systems and
  processors. Elsewhere, build the commit you pinned, with `-DBUILD_SHARED_LIBS=ON` if your own
  code loads the library.
- **A backend the archives do not ship.** llama.cpp supports more backends than it publishes
  archives for, and can build several at once or as dynamically loaded plug-ins
  (`GGML_BACKEND_DL`).
- **A policy that requires source builds.** Some organizations only run binaries they built.
  Then build the pinned commit and record your own hash.

In CI the same logic applies: cache the runtime folder keyed on the release, as sketched in
[running LLM yes/no checks in GitHub Actions](github-actions-llm-checks.md).

## Short answers to the questions that lead here

**Where do I download llama.cpp binaries?** From the releases page of the ggml-org/llama.cpp
repository on GitHub. Each tag has archives per platform and backend.

**Which llama.cpp release should I use?** For a new project, a recent one. For a running
service, the one you tested with, pinned, until you have re-tested on a newer one.

**Do the CUDA binaries need the CUDA toolkit?** The releases ship the CUDA runtime as a separate
archive; you need the NVIDIA driver.

**Does jev use a prebuilt llama.cpp?** No. jev runs 8-bit OpenVINO weights and compiles in
llama.cpp's tokenizer; the prebuilt archives are for running the jevos GGUF files with
llama.cpp directly.

**See also:** [llama-cpp-python vs calling llama.cpp through ctypes](llama-cpp-python-vs-ctypes.md),
[what is GGUF](what-is-gguf.md) and [self-hosted AI for decisions](self-hosted-ai-for-decisions.md).

## Sources

- Our own facts: what jev runs, and the GGUF files in the jevos-v2 release, from the
  [jev repository](https://github.com/feder-cr/jev).
- [llama.cpp README](https://github.com/ggml-org/llama.cpp) and
  [releases page](https://github.com/ggml-org/llama.cpp/releases), fetched 2026-09-29:
  install options, archive list, newest tag that day.
- [llama.cpp release b11081](https://github.com/ggml-org/llama.cpp/releases/tag/b11081),
  fetched 2026-09-29: tag, commit and asset names.
- [libllama API changelog, issue 9289](https://github.com/ggml-org/llama.cpp/issues/9289) and
  [llama.cpp build guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose release ships the model as GGUF
files for whichever llama.cpp release you pin.*
