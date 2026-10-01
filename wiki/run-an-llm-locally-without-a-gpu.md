---
title: "Run an LLM locally without a GPU"
description: "Running an LLM on a CPU works when the model is small, quantized, and the task needs little or no generated text. The jev quickstart as a worked example."
parent: "Local and private AI"
nav_order: 7
---

# Run an LLM locally without a GPU

**You can run an LLM locally without a GPU when three things line up: the model is small, it
is quantized to a few bits per weight, and the task needs little or no generated text.** jevos
is all three: a 1B model with 8-bit (INT8) weights, run on the CPU by `jev`, one native binary,
answering yes/no questions with one probability and no generated tokens. On a laptop with an
Intel Core Ultra 7 255H it answers a short request in 26 ms and a 191-token one in 112 ms. A few
commands take you from the release downloads to the first answer.

The third condition is the one most guides leave out. A CPU can run a small chat model, but
every word of the reply is another step through the model, so long answers are where CPU
inference feels slow. A task that needs only a probability skips that part entirely.

This page is why those three conditions matter, a short explanation of quantization, the
quickstart step by step, and what this approach cannot do.

## Why can a CPU be enough?

**Small.** A model's cost per token grows with its size. A 1B model does a fraction of the
arithmetic of the large models behind chat products, and its weights fit in the memory of an
ordinary laptop.

**Quantized.** The weights are stored in 8 bits or fewer instead of 16, which shrinks the file and
the amount of memory the CPU has to read for every token. On a CPU, reading memory is often
the bottleneck, so a smaller file is also a faster one. More on this on
[what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md).

**No generation.** An LLM processes your prompt in one pass, then produces an answer one token
at a time. The first part runs many tokens in parallel; the second repeats a full step for
every word. A model that returns a probability needs only the first part. The distinction is
explained on [prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md).

## Quantization, in one paragraph

llama.cpp supports integer quantization at 1.5, 2, 3, 4, 5, 6 and 8 bits, and ships prebuilt
binaries for many platforms, which is why it is a common way to run models on a CPU. jev itself
runs jevos-v2 with 8-bit (INT8) weights through OpenVINO, Intel's open-source inference runtime.
The release also ships the same model as GGUF files for llama.cpp and similar tools:
`jevos-v2-q4_k_m.gguf` (619 MB), a 4-bit build, and `jevos-v2-q8_0.gguf` (943 MB), an 8-bit one.
On 215 parity cases, jev's answers are within 0.056 of the `q8_0` GGUF's.
What the letters in those names mean is on
[GGUF quantization types explained](gguf-quantization-types-explained.md).

## The quickstart, step by step

**1. Get jev and the model.** Download `jev-linux-x64.tar.gz` (or `jev-windows-x64.zip`, or
`jev-macos-arm64.tar.gz`) and `jevos-v2-openvino-int8.zip` from the
[release page](https://github.com/feder-cr/jev/releases/tag/jevos-v2).

**2. Unpack them.**

```bash
tar -xzf jev-linux-x64.tar.gz
cd jev
unzip ../jevos-v2-openvino-int8.zip     # creates model/
```

The `jev` folder holds the binary, OpenVINO's libraries and the licenses; the model goes in
`jev/model`. There is nothing to install and nothing to compile: no Python, no GPU. On Windows,
run `unzip jev-windows-x64.zip` instead, and `.\jev.exe serve` in PowerShell for the next step.

**3. Start the server on the CPU.**

```bash
./jev serve
```

jev runs on the CPU only (x86-64 with AVX2, or Apple silicon). `--threads` defaults to all
logical CPUs; set it lower if other heavy programs are running. The server listens on
`127.0.0.1:8017`.

**4. Ask a question.**

```bash
curl http://127.0.0.1:8017/v1/systemone -H 'Content-Type: application/json' -d '{
  "model": "jev-latest",
  "state": "I was charged twice for the same order.",
  "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}}}'
```

The README's answer to this request is `"noul": 0.94` with `"input_tokens": 27` and
`"output_tokens": 0`: a probability of yes, and nothing generated. The request format, several
questions per call and the Python version are on
[ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md).

## What should you expect on your machine?

Our figures come from one laptop: an Intel Core Ultra 7 255H, 16 threads, no GPU. There, a
short request takes 26 ms and a 191-token one 112 ms when the text is read from scratch, and
several questions on the same text cost less than separate requests, because the text is read
once: three questions took about 66 ms, against 49 ms for one.

On a different CPU the numbers will be different, and we have not measured others. Warm the
server up with a few requests before timing, use inputs of realistic length, and read the
`Server-Timing` header on each response for the model's own share.

## What this approach cannot do

Being straight about the limit: this is not a way to run a chatbot on a CPU.

- **No text generation.** jevos answers yes/no, multiple-choice and (early) score questions, as probabilities. It does not write,
  summarise or chat. For that you need a generative model, and on a CPU its speed will depend
  on how long the answers are; llama.cpp itself runs such models.
- **Scores are early.** `score` questions are answered as one yes/no question per level, right 54% of the time on 2,350 held-out score questions and within one level 82%, weak on points to add up.
  Multiple choice is answered, as `choice` questions.
- **English only.**
- **Reading, not computing.** On 999 questions written after training, it was right 0.954 of
  the time on facts stated in the text and 0.584 on questions that need arithmetic. Compute in
  code and ask the model to read.

When a GPU starts to pay off, for large batches, long documents or bigger models, is covered on
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md).

## Short answers to the questions that lead here

**Can I run an LLM without a GPU?** Yes, if the model is small and quantized. jev runs jevos
on the CPU only, with 8-bit weights; there is no GPU path.

**How much RAM does a local LLM need?** It depends on the model and its quantization: roughly
one byte per weight at 8 bits, half that at 4 bits, plus memory for the context. jevos is a 1B
model, and jev runs it with 8-bit weights.

**Do I need to compile llama.cpp?** Not for jev. `jev` is a prebuilt binary and does not use
llama.cpp's runtime, only its tokenizer, compiled in. To run the GGUF files with llama.cpp
directly, its official prebuilt binaries cover many platforms.

**Why is my local chat model slow on a CPU?** Usually the generated answer: every output token
is another full step through the model. A task that needs a probability instead of a paragraph
avoids it.

**Which quantization should I pick?** jev itself runs 8-bit (INT8) weights, so there is nothing
to pick. For the GGUF files in llama.cpp or another tool, `q4_k_m` is the smaller file (619 MB
against 943 MB for `q8_0`).

**See also:** [running llama.cpp CPU only](llama-cpp-cpu-only.md),
[small language models explained](small-language-models-explained.md) and
[an LLM on a laptop](an-llm-on-a-laptop.md).

## Sources

- Commands, options, the example request and answer, and file sizes: the
  [jev README](https://github.com/feder-cr/jev).
- Latency and the 215 parity cases: our measurements on an Intel Core Ultra 7 255H laptop. Accuracy
  by kind of question: our 999-question set, `jevos-q4_k_m`.
- llama.cpp's quantization support and prebuilt binaries: the
  [llama.cpp README](https://github.com/ggml-org/llama.cpp), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model that runs on a laptop CPU
because its job is one number, not a paragraph.*
