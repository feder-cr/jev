---
title: "Q4_K_M vs Q8_0: speed and size for a small model"
description: "jevos-v4 ships as q4_k_m and q8_0 GGUF files for llama.cpp and other tools; jev itself runs 8-bit weights. Accuracy of the two is not measured on one set."
parent: "Speed"
nav_order: 11
---

# Q4_K_M vs Q8_0: speed and size for a small model

**Of the two GGUF files of jevos, `q4_k_m` is the smaller one and the one to start with in
llama.cpp, Ollama, LM Studio or another tool that reads GGUF: about 4.9 bits per weight against
8.5.** `jev`
itself reads neither file: it runs the model with 8-bit (INT8) weights through OpenVINO. What we
cannot tell you yet is how much accuracy, if any, the smaller file gives up, because the two
builds have not been measured on the same question set. Until they are, the honest choice is
`q4_k_m` for size and a test on your own questions if accuracy is tight.

The non-obvious part is that "8-bit is slower" is not a law. In llama.cpp's own benchmark table
for a larger model, `Q8_0` reads prompts about as fast as `Q4_K_M` and is slower only at writing
tokens. Which one wins depends on the hardware and the work, and that is the reason to measure
rather than assume.

This page is which file to download, the measured difference, why size costs time on a CPU,
what we have not measured, and how to check on your own machine. What the letters in the names
mean is on [GGUF quantization types explained](gguf-quantization-types-explained.md).

## Which file should I download?

| | `jevos-v4-q4_k_m.gguf` | `jevos-v4-q8_0.gguf` |
|---|---|---|
| Bits per weight (llama.cpp's figures) | about 4.9 | about 8.5 |
| Accuracy on the same set as the other | not measured | not measured |
| Read by `jev` itself | no | no |

Start with `q4_k_m`. The latencies on this wiki (28 ms short, 130 ms long, 66 ms for three
questions on one text) were taken with `jev`, which runs the INT8 model, not with either GGUF
file. Move to `q8_0` only if you have tested both on your own questions and the larger file is
measurably better for you, and the extra time fits your budget.

Both files are on the [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos-v4); check the hash after
downloading, as described on
[offline AI for decisions](offline-ai-for-decisions.md).

## What the measurement says

`jev` runs 8-bit (INT8) weights through OpenVINO, not a GGUF quantization. By bit width,
`q8_0` is the GGUF file closest to what `jev` runs, but how closely its answers match has not been
measured for jevos-v4.

How fast each GGUF file is depends on the tool that runs it and on your CPU. Measure it there,
as described below, rather than taking a factor from someone else's machine.

## Why the bigger file is slower on a CPU

A dense model reads essentially all of its weights on each pass, so a file with more bytes per
weight asks the memory system to move more data. llama.cpp's quantization README lists
`Q4_K_M` at about 4.9 bits per weight and `Q8_0` at about 8.5 for the model it uses as an
example, and says quantization "shrinks the model's size and can speed up inference".

How much of that turns into time depends on where the bottleneck is. The same README's table,
for an 8B model on hardware it does not specify, shows prompt processing at about 822 tokens per
second for `Q4_K_M` and 865 for `Q8_0`, and text generation at about 72 against 51. Reading was
not slower with 8 bits there; writing was.
The phases and their bottlenecks are on
[prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md), and the
CPU side of it on [what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md).

## What we have not measured

Being straight about the limit: the accuracy numbers we publish for jevos-v4 (87.0% of 821
hand-written yes/no questions, 78.9% of 999) were taken through `jev`'s own 8-bit model, not
through either GGUF file. Earlier measurements on the first jevos were run on different builds
and different sets, and they cannot be compared to decide between the files; the gap between a
held-out split and fresh questions is the subject of
[our held-out benchmark said 0.855](held-out-benchmark-too-optimistic.md). A comparison of the two
files on one set is the missing measurement.

The same README warns that quantization "may introduce some accuracy loss". Whether it does
here, and by how much, is exactly what has not been tested.

## How to check on your own machine

1. Download both files and verify them against `SHA256SUMS.txt`.
2. Load one file in llama.cpp or the tool you use, and time prompts the size of your real
   requests; then repeat with the other file. Never both at once on one CPU.
3. Run your own labelled questions through both and compare accuracy per kind of question, not
   only the total.

The timing method is on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md), and
building the labelled set is on
[building a yes/no test set for your own data](building-a-yes-no-test-set.md). `jev decide`
answers the same request files without a server with `jev`'s own INT8 model, which gives you a
third column to compare the two files against.

## Short answers to the questions that lead here

**Is Q4_K_M or Q8_0 better?** For jevos, `q4_k_m` is the smaller file. Which is faster depends
on your tool and CPU, and which is more accurate has not been measured on the same set. `jev`
itself runs 8-bit weights and reads neither file.

**Is Q8_0 always slower than Q4_K_M?** No. llama.cpp's own table shows similar prompt speed and
slower generation on its test hardware.

**How much memory does jevos need?** About 1 GB with the model loaded, and up to 1.4 GB once its cache of recent texts is full. We have not
published a separate figure for each GGUF file.

**Why ship two files?** For llama.cpp, Ollama, LM Studio and other tools: so you can test the
larger one where accuracy matters more than speed, once you have your own measurement.

**Are other quantizations available?** The release has `q4_k_m` and `q8_0` as GGUF, and the
INT8 OpenVINO model that `jev` runs.

**See also:** [what is GGUF](what-is-gguf.md),
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md) and
[the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md).

## Sources

- Latencies, memory and the accuracy figures with the build each was run on: our own
  measurements and the [jev release page](https://github.com/feder-cr/jev/releases/tag/jevos-v4).
- Bits per weight, the example benchmark table and the size and accuracy caveats:
  [llama.cpp quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md),
  fetched 2026-09-29. Its hardware is not stated there.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships the bigger file without
claiming it is better, because nobody has checked that yet.*
