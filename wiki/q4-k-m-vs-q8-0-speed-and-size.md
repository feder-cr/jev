---
title: "Q4_K_M vs Q8_0: speed and size for a small model"
description: "jevos ships as a 619 MB q4_k_m and a 943 MB q8_0 file. On our CPU q8_0 is about 1.7x slower; accuracy of the two on one set is not yet measured."
parent: "Speed"
nav_order: 11
---

# Q4_K_M vs Q8_0: speed and size for a small model

**For jevos, `q4_k_m` is the smaller and faster file and the one to start with: 619 MB against
943 MB, and on our reference CPU `q8_0` is about 1.7 times slower.** What we cannot tell you yet
is how much accuracy, if any, the smaller file gives up, because the two builds have not been
measured on the same question set. Until they are, the honest choice is `q4_k_m` for speed and
a test on your own questions if accuracy is tight.

The non-obvious part is that "8-bit is slower" is not a law. In llama.cpp's own benchmark table
for a larger model, `Q8_0` reads prompts about as fast as `Q4_K_M` and is slower only at writing
tokens. On our laptop, for a model that only reads, the bigger file was clearly slower. Which
one wins depends on the hardware and the work, and that is the reason to measure rather than
assume.

This page is which file to download, the measured difference, why size costs time on a CPU,
what we have not measured, and how to check on your own machine. What the letters in the names
mean is on [GGUF quantization types explained](gguf-quantization-types-explained.md).

## Which file should I download?

| | `jevos-v2-q4_k_m.gguf` | `jevos-v2-q8_0.gguf` |
|---|---|---|
| File size | 619 MB | 943 MB |
| Speed on our reference CPU | baseline | about 1.7x slower |
| Accuracy on the same set as the other | not measured | not measured |
| Used in the README quickstart | yes | no |

Start with `q4_k_m`. Every latency on this wiki (54 ms short, 220 ms long, 165 ms for three
questions on one text) was taken with it. Move to `q8_0` only if you have tested both on your
own questions and the larger file is measurably better for you, and the extra time fits your
budget.

Both files are on the [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos-v2) with a
`SHA256SUMS.txt`; check the hash after downloading, as described on
[offline AI for decisions](offline-ai-for-decisions.md).

## What the measurement says

On an Intel Core Ultra 7 255H with 16 threads and no GPU in use, `q8_0` answered the same
requests about 1.7 times slower than `q4_k_m`. Two other 4-bit builds we tried, `q4_0` and
`iq4_nl`, were about as fast as `q4_k_m`; they are not in the release.

A factor applies to the whole request. If a request takes 220 ms with `q4_k_m`, expect something
in the region of 370 ms with `q8_0` on the same machine. That estimate is arithmetic on the
factor, not a separate measurement.

## Why the bigger file is slower on a CPU

A dense model reads essentially all of its weights on each pass, so a file with more bytes per
weight asks the memory system to move more data. llama.cpp's quantization README lists
`Q4_K_M` at about 4.9 bits per weight and `Q8_0` at about 8.5 for the model it uses as an
example, and says quantization "shrinks the model's size and can speed up inference".

How much of that turns into time depends on where the bottleneck is. The same README's table,
for an 8B model on hardware it does not specify, shows prompt processing at about 822 tokens per
second for `Q4_K_M` and 865 for `Q8_0`, and text generation at about 72 against 51. Reading was
not slower with 8 bits there; writing was. On our laptop, for a model that only reads, it was.
The phases and their bottlenecks are on
[prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md), and the
CPU side of it on [what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md).

## What we have not measured

Being straight about the limit: the accuracy numbers we publish were taken on different builds
and different sets, and they cannot be compared to decide between the files.

- The held-out split (0.855 overall, 0.874 on natural yes/no questions, calibration error 0.009)
  was run on `q8_0`.
- The 999 questions written after the model was finished (0.757) were run on `q4_k_m`.

Those are different question sets, and the second is much harder; the gap between them is the
subject of [our held-out benchmark said 0.855](held-out-benchmark-too-optimistic.md). Reading
the two numbers as "q8_0 is 0.1 more accurate" would be wrong. A comparison of the two files on
one set is the missing measurement.

The same README warns that quantization "may introduce some accuracy loss". Whether it does
here, and by how much, is exactly what has not been tested.

## How to check on your own machine

1. Download both files and verify them against `SHA256SUMS.txt`.
2. Start the server with one file, `uv run jev serve --gguf jevos-v2-q4_k_m.gguf --device cpu`,
   wait for `/health` to report ready, and time your real requests; then repeat with the
   other file. Never both at once on one CPU.
3. Run your own labelled questions through both and compare accuracy per kind of question, not
   only the total.

The timing method is on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md), and
building the labelled set is on
[building a yes/no test set for your own data](building-a-yes-no-test-set.md). `jev decide`
with `--gguf` pointing at each file answers the same request files without a server, which makes
the comparison easy to script.

## Short answers to the questions that lead here

**Is Q4_K_M or Q8_0 better?** For jevos on our CPU, `q4_k_m` is 1.7 times faster and a third
smaller. Which is more accurate has not been measured on the same set.

**Is Q8_0 always slower than Q4_K_M?** No. On our CPU, for a reading-only model, it was.
llama.cpp's own table shows similar prompt speed and slower generation on its test hardware.

**How much memory does jevos need?** About 1.2 GB more with the model loaded. We have not
published a separate figure for each file.

**Why ship two files?** So you can test the larger one where accuracy matters more than
speed, once you have your own measurement.

**Are other quantizations available?** The release has `q4_k_m` and `q8_0`. We found `q4_0` and
`iq4_nl` about as fast as `q4_k_m`, but they are not published.

**See also:** [what is GGUF](what-is-gguf.md),
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md) and
[the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md).

## Sources

- File sizes, the 1.7x factor, the `q4_0` and `iq4_nl` observation, latencies, memory and the
  accuracy figures with the build each was run on: our own measurements and the
  [jev release page](https://github.com/feder-cr/jev/releases/tag/jevos-v2).
- Bits per weight, the example benchmark table and the size and accuracy caveats:
  [llama.cpp quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md),
  fetched 2026-09-29. Its hardware is not stated there.
- The 370 ms figure is derived from the factor, not measured.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships the bigger file without
claiming it is better, because nobody has checked that yet.*
