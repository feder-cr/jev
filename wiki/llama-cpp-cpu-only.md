---
title: "Running llama.cpp CPU only"
description: "How to keep llama.cpp on the CPU, how many threads to give it, why hybrid cores complicate that, and what memory mapping means for a small model."
parent: "llama.cpp and GGUF"
nav_order: 7
---

# Running llama.cpp CPU only

**To run llama.cpp on the CPU only, either install a CPU build or tell it to offload nothing
(`--device none` or `-ngl 0` on llama.cpp's tools, `--device cpu` on jev), then set the thread
count to roughly your number of physical cores and measure from there.** llama.cpp's own docs
recommend physical rather than logical cores for `--threads`. jev's README says to set
`--threads` to your core count, fewer if other heavy apps are running; its default is 4.

The part that is not obvious is that "use every core" is a starting point, not an answer. On
processors that mix fast and slow cores, and on machines doing other work, the best thread
count is often lower than the maximum. It depends on the machine, so it has to be measured.

This page is the switches that keep llama.cpp off the GPU, how the thread options work, why
hybrid cores make the choice harder, what memory looks like on the CPU, and when a CPU is not
enough.

## Keeping llama.cpp off the GPU

There are two independent levers, and it helps to know both.

**Which runtime you install.** llama.cpp releases have CPU-only archives for each platform. A
CPU build has no GPU backend to pick, so nothing can be offloaded by accident. With jev,
`uv run jev download --only runtime --runtime cpu` installs that package; the default `auto`
may install a CUDA or Vulkan build instead.

**Which devices you ask for at run time.** A GPU build can still run entirely on the CPU:

- `llama-server` and the other tools take `--device none`, documented as "none = don't
  offload", or `-ngl 0` to keep no layers in VRAM. `--list-devices` shows what is available.
- `jev serve --device cpu` passes llama.cpp an empty device list and keeps no weights on a
  GPU, even when a GPU runtime is installed. `uv run jev devices` shows what the runtime sees.

```bash
uv run jev serve --gguf jevos-q4_k_m.gguf --device cpu --threads 16
```

## How the thread options work

llama.cpp's tools have two thread settings:

| Option | What it controls | Default |
|---|---|---|
| `-t`, `--threads` | threads used during generation | -1 |
| `-tb`, `--threads-batch` | threads used for batch and prompt processing | same as `--threads` |

The docs add that "in some systems, it is beneficial to use a higher number of threads during
batch processing than during generation", and recommend physical cores for `--threads`.

For a decision model the second one is the one that matters. jevos generates no tokens, so all
of its time is prompt processing, the phase explained on
[prefill vs decode](prefill-vs-decode-llm-latency.md). jev's `--threads` sets both values to the
same number, so there is only one knob to tune.

## Why hybrid cores make "all threads" a guess

Many recent laptop and desktop chips mix core types. The reference laptop for the jevos
numbers, an Intel Core Ultra 7 255H, has 16 cores in three kinds, 6 performance cores, 8
efficient cores and 2 low-power efficient cores, and 16 threads in total. The published
measurements used `--threads 16`.

The theory of why more threads can be slower, which we have not measured on this page:

- **Each step waits for the slowest thread.** Work on a matrix is split across threads, and the
  step finishes when the last share is done. A share given to a slower core, or to a core that
  another program is using, holds up the rest.
- **Memory bandwidth is shared.** Past some point, more cores are waiting on the same memory
  rather than computing. Why memory traffic dominates on a CPU is covered on
  [what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md).
- **Other work competes.** A browser, a build or a video call takes cores away without telling
  llama.cpp, which is why the README says "fewer if other heavy apps are running".

llama.cpp's tools also offer placement controls for this: `--cpu-mask` for an affinity mask,
`--cpu-strict` for strict placement, `--prio` for priority and `--poll` for how threads wait
for work. jev does not expose these; it sets the thread count only.

The practical answer: try a few values (for example the number of performance cores, then
more), and compare medians after warm-up, one run at a time. The method is on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

## Memory on the CPU

On the CPU the model lives in ordinary RAM, and llama.cpp's default is to memory-map the file:
the load mode `auto` maps the model "unless the device does not support it". Mapping lets the
operating system page weights in from the file instead of copying them up front. The
alternative `mlock` pins the model in RAM so it cannot be swapped out; the docs note it "can
improve performance but trades away some of the advantages of memory-mapping by requiring more
RAM to run and potentially slowing down load times."

For jevos the numbers are small: the q4_k_m file is 619 MB and memory use grows by about 1.2 GB
with the model loaded, with a context of up to 8,192 tokens. That fits alongside normal
work on most machines, which is what makes CPU-only practical for it.

## What CPU only gives and what it costs

With the settings above, jevos on the reference laptop answers a short request (about 30 tokens)
in 54 ms and a long one (about 190 tokens) in 220 ms, about 1.1 ms per prompt token. Cost grows
with the length of the text, so the CPU is comfortable for messages, tickets and records, and
slower for long documents.

Being straight about the limit: a CPU is the wrong tool when you process long documents at
volume or need high throughput from one box. Then a GPU build of the same llama.cpp release is
the right kind of tool, and the trade-off is on [CPU or GPU for a small
LLM](cpu-or-gpu-for-a-small-llm.md).

## Short answers to the questions that lead here

**How do I force llama.cpp to use only the CPU?** Use a CPU build, or pass `--device none` or
`-ngl 0` to llama.cpp's tools. With jev, pass `--device cpu`.

**How many threads should llama.cpp use?** Start at the number of physical cores, as llama.cpp's
docs recommend, then measure lower values. Fewer if other heavy programs are running.

**What is the difference between --threads and --threads-batch?** The first is for generation,
the second for batch and prompt processing. A decision model only does the second.

**Does llama.cpp use efficient cores?** It runs threads wherever the operating system places
them unless you set an affinity mask. Whether that helps on your chip is a measurement.

**Why is my CPU inference slower with more threads?** Usually shared memory bandwidth, slower
cores holding up each step, or other programs using the same cores.

**See also:** [llama.cpp on Windows without compiling](llama-cpp-on-windows.md),
[run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md) and
[an LLM on a laptop](an-llm-on-a-laptop.md).

## Sources

- Our own measurements and facts: latency, tokens, memory and context of jevos on the reference
  laptop with 16 threads, and the `--threads` guidance, from the
  [jev README](https://github.com/feder-cr/jev); how `--device cpu` and `--threads` are applied,
  from `llama_cpp.py` and `llama_release.py`.
- [llama-server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
  fetched 2026-09-29: `--threads`, `--threads-batch`, `--device`, `-ngl`, `--list-devices`,
  `--cpu-mask`, `--cpu-strict`, `--prio`, `--poll`.
- [llama.cpp completion README](https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md),
  fetched 2026-09-29: physical-core recommendation, batch threads note, load modes and `mlock`.
- [Intel Core Ultra 7 255H specifications](https://www.intel.com/content/www/us/en/products/sku/241751/intel-core-ultra-7-processor-255h-24m-cache-up-to-5-10-ghz/specifications.html),
  fetched 2026-09-29: core types and thread count.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose published timings all come from
one hybrid-core laptop with its 16 threads in use.*
