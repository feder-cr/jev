---
title: "What makes a local LLM fast on a CPU"
description: "The five things that decide how fast a language model runs on a CPU: size, quantization, memory bandwidth, tokens processed, and whether it generates."
parent: "Speed"
nav_order: 2
---

# What makes a local LLM fast on a CPU

**A language model is fast on a CPU when it is small, stored in few bits per weight, asked to
read few tokens, and not asked to write any.** Size and quantization decide how many bytes the
processor has to move for every step; the length of the input decides how much work the step
does; generation multiplies the cost by the number of words in the answer. Get all four right
and a CPU without a GPU answers in tens to hundreds of milliseconds.

The point people miss is that on a CPU the limit is often not arithmetic but memory: the
processor spends its time waiting for weights to arrive. That is why halving the bytes can
matter more than adding cores, and why generation, which rereads the weights for every token,
is the expensive part.

This page is the list of factors, how each one works, what the thread setting does, and the
only measured numbers we have for jevos, from one laptop.

## The short list

1. **Parameter count.** Fewer weights, fewer bytes to read and fewer multiplications.
2. **Bits per weight.** A 4-bit quantized file is roughly half the size of an 8-bit one, with
   the same number of parameters.
3. **Memory bandwidth.** How fast the machine can stream those bytes to the cores.
4. **Tokens processed.** Prompt length sets the work of the reading step.
5. **Tokens generated.** Every output token is another pass through the model.

Threads and instruction sets matter too, but they tune how well the machine uses the budget the
first five set.

## Why size and bits come first

In a typical dense language model, each pass reads essentially all of the weights. A model with a few hundred million
to a few billion parameters, quantized to around 4 or 5 bits each, fits in a file of well under
a gigabyte to a few gigabytes, and a laptop's memory system can move that quickly.

llama.cpp, the usual runtime for GGUF files, supports integer quantization from 1.5 to 8 bits
"for faster inference and reduced memory use", in its own words. Its quantization README lists
Q4_K_M at about 4.9 bits per weight and Q8_0 at about 8.5 for the model it uses as an example.
For jevos the two released GGUF files are 619 MB for `q4_k_m` and 943 MB for `q8_0`; jev itself
runs the model with 8-bit (INT8) weights through OpenVINO. The GGUF trade-off, including what we
have not measured yet, is on [Q4_K_M vs Q8_0: speed and size](q4-k-m-vs-q8-0-speed-and-size.md), and
what the names mean is on [GGUF quantization types explained](gguf-quantization-types-explained.md).

Quantization is not free: the llama.cpp documentation says it "may introduce some accuracy
loss". How much depends on the model and the task, so check it on your own questions.

## Memory bandwidth vs compute

LLM inference has two phases with different bottlenecks. The Splitwise paper describes the
prompt phase as compute-intensive, with all input tokens going "through the forward pass of the
model in parallel", and the token generation phase as "more memory bandwidth and capacity
bound", because each new token is computed from the last one.

On a CPU this split is sharp. Reading a prompt uses the cores' vector units on many tokens at
once, so the weights fetched from memory are reused across the whole prompt. Generating a token
fetches the same weights again to compute one token. A model that only reads a prompt and never
generates stays in the phase that CPUs handle best. The two phases are explained in detail on
[prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md).

## Tokens in, tokens out

Once the model and the machine are fixed, the work is set by tokens.

- **Input tokens.** The reading step grows with the prompt. On our reference laptop jevos took
  26 ms for a request of about 30 tokens and 112 ms for one of about 190, reading each text from
  scratch. The detail, and how to trim the input, is on
  [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).
- **Output tokens.** Each one is a full pass. A chat model answering "Yes, this is a billing
  problem." pays for several of them; jevos pays for none, because `output_tokens` is always 0.

This is why the design of the input is a speed decision. Sending the whole order record when
the question needs two fields costs time on every request; the practical side is on
[sending JSON as the text: designing the state](designing-the-state-as-json.md).

## Threads: more is not always better

`jev serve` uses all logical CPUs by default; set `--threads` lower if other heavy apps are
running. Our measurements used 16 threads on a 16-thread laptop.

Two cautions, both general and not measured by us. Memory-bound work stops scaling once the
memory system is saturated, so threads beyond that point add contention rather than speed. And
laptop CPUs often mix performance and efficiency cores, so "all threads" can put part of the
work on slower cores. If speed matters, try a few values on your own machine; more on
[running llama.cpp CPU only](llama-cpp-cpu-only.md).

## What we measured, and what it does not tell you

| Request | Tokens | jevos, text read from scratch | jevos, same text asked again |
|---|---|---|---|
| short | about 30 | 26 ms | 25 ms |
| long | about 190 | 112 ms | 22 ms |
| one text, three questions | 95 | about 66 ms (49 ms for one question alone) | 39 ms (24 ms for one) |

Reference machine: Intel Core Ultra 7 255H, 16 threads, no GPU in use, about 1 GB of extra
memory with the model loaded. jev keeps texts it has read, so a request on a text it has seen
reads only the question.

Being straight about the limit: this is one laptop. A desktop with more memory bandwidth, an
older CPU, or a server shared with other work will give different numbers. The factors above
tell you which direction they move, not by how much.

## Short answers to the questions that lead here

**Why is my LLM slow on the CPU?** Usually because it is large, stored at high precision, fed a
long prompt, or generating a long answer. Generation is often the biggest single cost.

**Does quantization make a model faster on a CPU?** Usually, because there are fewer bytes to
move. jev itself runs jevos with 8-bit weights.

**Do more CPU cores help?** Up to a point. Past the memory bandwidth limit, extra threads add
little, and on hybrid CPUs the slower cores can pull the average down.

**Is a GPU required for a fast LLM?** Not for a small model on short inputs. See
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md).

**What is the fastest way to get a yes/no answer from a local model?** Ask a model that returns
a probability, keep the input short, and ask several questions about one text in one request.

**See also:** [run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md),
[why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md) and
[many questions about one text](many-questions-about-one-text.md).

## Sources

- jevos latency, file sizes, memory and the thread guidance: our own
  measurements and the [jev README](https://github.com/feder-cr/jev).
- Prompt phase and token phase characteristics: Patel et al.,
  [Splitwise](https://arxiv.org/abs/2311.18677), fetched 2026-09-29.
- Quantization range and purpose:
  [llama.cpp README](https://github.com/ggml-org/llama.cpp), fetched 2026-09-29; bits per
  weight and the accuracy caveat:
  [llama.cpp quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md),
  fetched 2026-09-29.
- Remarks on thread scaling and hybrid cores are general reasoning, not measured here.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which runs on a laptop CPU and was
measured on one; the laptop is named on every page so you can tell how far the numbers travel.*
