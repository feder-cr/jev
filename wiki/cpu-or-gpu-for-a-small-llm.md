---
title: "CPU or GPU for a small LLM"
description: "For a small model on short inputs, one request at a time, a CPU is usually enough. When a GPU starts to pay: large batches, long texts, generation."
parent: "Speed"
nav_order: 8
---

# CPU or GPU for a small LLM

**For a small model reading short inputs one request at a time, a modern CPU is usually enough,
and it is the hardware you already have.** A GPU pays off when there is a lot of parallel
arithmetic to do: many requests batched together, long documents, or long generated answers.
jev is built and measured for the first case: it runs on the CPU only, measured on a laptop,
and has no GPU path.

The question is less "which is faster" than "which is idle". A GPU that finished a 50 ms job in
10 ms (illustrative numbers, not a measurement) would save 40 ms per request, which matters if you have thousands of requests per second and
barely matters if you have ten a minute. What decides it is your traffic, not the hardware's
peak.

This page is three questions that decide it, what each processor is good at, the costs that are
not about speed, how jev picks a device, and when to switch.

## Three questions that decide it

1. **How many decisions per second at peak?** A handful per second with no queue is a CPU job.
   Sustained high concurrency is where batching on a GPU earns its cost.
2. **How long are the inputs?** Tens to a few hundred tokens read quickly on a CPU; on our
   laptop jevos took 26 ms at about 30 tokens and 112 ms at about 190. Thousands of tokens per
   request multiply that.
3. **Does the model generate?** A decision model with zero output tokens avoids the long
   sequential phase entirely. A chat model writing paragraphs spends most of its time there.

If the answers are "few", "short" and "no", stay on the CPU and spend the effort on the input
instead. The factors that set CPU speed are on
[what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md).

## What a GPU is good at, and what it is not

Language model inference has two phases. The Splitwise paper describes the prompt phase as
compute-intensive, many tokens processed in parallel, and the token generation phase as bound
by memory bandwidth and capacity. GPUs are built for the parallel arithmetic of the first
phase; how much they help the second depends on the memory they read from.

The same paper notes that batching the token phase "yields high throughput", and the vLLM paper
opens with "high throughput serving of large language models (LLMs) requires batching
sufficiently many requests at a time". Both statements are about serving many users. A GPU's
advantage grows with the amount of work it can do at once, which is why it shines under load
and matters less for one short request.

What a GPU does not remove: the time your application spends building the request, the HTTP
round trip, and any work your code does with the answer. For a request that already takes tens
of milliseconds, those parts are a larger share than they look.

## Costs that are not about speed

- **Availability.** Every server and laptop has a CPU. GPUs in a data centre are a separate
  budget line; on a laptop, the integrated one may or may not be supported by your runtime.
- **Memory.** On a CPU the loaded model lives in system memory, which most machines have spare;
  on a GPU it has to fit in the card's memory next to whatever else runs there.
- **Deployment.** A CPU-only service is one binary and one model folder on any machine; a GPU
  service adds drivers and a matching runtime build. llama.cpp publishes builds for many
  backends (CUDA, HIP, Metal, Vulkan, SYCL and others, per its README), which helps, but it is
  still one more thing to match.
- **Contention.** A shared GPU is shared latency. So is a shared CPU; see the note on
  benchmarking on [measuring LLM latency](measuring-llm-latency-median-and-p90.md).

For many teams the deciding argument is that the CPU servers already exist; that angle is on
[on-premise LLM for business decisions](on-premise-llm-for-business-decisions.md).

## How jev picks a device

It does not pick one: jev runs on the CPU only. It runs jevos-v2 with 8-bit (INT8) weights
through OpenVINO, on any x86-64 CPU with AVX2 and on Apple silicon, and it is fastest on CPUs
with AVX-VNNI or AVX-512 VNNI. There is no device option and no GPU build.

Every jevos number we publish was taken on an Intel Core Ultra 7 255H with 16 threads, the
configuration of the README's benchmark. The release also ships the model as GGUF files for
llama.cpp and other tools; if you run those on a GPU, measure it yourself: we make no claim
about the speed you will see, and the [CPU-only guide for llama.cpp](llama-cpp-cpu-only.md)
covers the flags that matter when you stay on the CPU.

## When to reach for a GPU

- **Throughput beyond one machine's CPU.** When requests queue and the p90 climbs past your
  budget, the choices are more CPU processes, more machines, or a GPU with batching. The trade-off
  is on [throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).
- **Long documents at interactive speed.** Thousands of tokens per request is prompt-heavy work,
  the phase GPUs accelerate most.
- **A larger model.** If a small model is not accurate enough for your questions, the model you
  move to may not be practical on a CPU at all. llama.cpp's "CPU+GPU hybrid inference" exists
  for models "larger than the total VRAM capacity", in its own words, which says something about
  the sizes involved.

Being straight about the limit: a small model on a CPU is a good fit for a narrow job. It is not
a way to avoid GPUs for everything.

## Short answers to the questions that lead here

**Do I need a GPU to run an LLM?** Not for a small model on short inputs. jevos is measured on a
laptop CPU with no GPU in use. See
[run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md).

**Is a GPU always faster?** Per unit of work it usually is. For one short request the difference
can be small next to everything else in the request, and the GPU has its own costs.

**Can jevos use a GPU?** jev runs on the CPU only. The GGUF files in the release can be run
elsewhere, for example in llama.cpp; we have only published CPU measurements.

**What about an integrated GPU?** jev does not use it. If you run the GGUF files on one, whether
it beats the CPU cores on your laptop is something to measure, not assume.

**When is the CPU the wrong choice?** High sustained concurrency, very long inputs, generation,
or a model too large to run well in system memory.

**See also:** [the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md),
[edge AI decisions on a CPU](edge-ai-decisions-on-a-cpu.md) and
[an LLM on a laptop](an-llm-on-a-laptop.md).

## Sources

- jevos latency, the reference machine and the CPU requirements: our measurements and the
  [jev README](https://github.com/feder-cr/jev).
- The two inference phases and batching the token phase: Patel et al.,
  [Splitwise](https://arxiv.org/abs/2311.18677), fetched 2026-09-29.
- Batching for throughput: Kwon et al.,
  [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180),
  fetched 2026-09-29.
- Backends and hybrid inference: [llama.cpp README](https://github.com/ggml-org/llama.cpp),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which runs on the CPU only, the one
setting all of its numbers were measured on.*
