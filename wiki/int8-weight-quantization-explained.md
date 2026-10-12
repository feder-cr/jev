---
title: "INT8 weight quantization explained"
description: "What 8-bit weights store, symmetric vs asymmetric, per-channel vs blocks, weights only vs activations, why it helps a CPU and what accuracy it costs."
parent: "Speed"
nav_order: 14
---

# INT8 weight quantization explained

**INT8 weight quantization stores each weight as an 8-bit integer, plus a scale (and sometimes a
zero point) shared by a row or block of weights to map the integers back to real values.** That
is a quarter of the 32-bit size and half of the 16-bit one, and on a CPU, where a language model
often waits on memory, fewer bytes usually means faster passes. The accuracy cost of 8 bits is
usually small (OpenVINO rates it "Low") but depends on the model and the task, so check it.

The point often missed is that "INT8" names a width, not a method. Symmetric or asymmetric,
one scale per channel or per block of 32, weights only or activations too: two "8-bit" builds of
one model are not interchangeable without a test.

This page is the mapping with a worked example, the two schemes, the speed, activations, the
accuracy evidence, and GGUF.

## What does an 8-bit weight actually store?

The standard form comes from Jacob et al. (2017): a real value r is stored as an integer q with
r = S(q - Z), where S is a floating-point scale and Z an integer zero point. It makes sure "the
real value r=0 be exactly representable", because operators often pad arrays with zeros.
With the range set from the weights' own extremes, the loss is rounding: every weight lands
within half a step of where it was.

How many weights share one scale is the granularity. NNCF, OpenVINO's compression library, lists
both of its INT8 weight modes as "Per-channel" with FP16 scales: one scale per output channel.
Its "group-wise" option, offered for 4-bit modes, gives each group (for example 128 weights) its
own parameters. llama.cpp's Q8_0 uses blocks of 32.

## Symmetric or asymmetric: what is the difference?

Symmetric quantization centers the integer range on zero and stores no zero point; asymmetric
quantization shifts the range to fit the real minimum and maximum. In NNCF's definitions,
symmetric weights use levels -127 to 127 and asymmetric ones 0 to 255, with the rule that
"floating-point zero should be within quantization range and strictly mapped into quant".

An illustrative row of five weights from -0.50 to 0.30 (our arithmetic, not a
measurement):

| Weight | Symmetric q (S = 0.50/127) | Back to real | Asymmetric q (S = 0.80/255, Z = 159) | Back to real |
|---|---|---|---|---|
| -0.50 | -127 | -0.500 | 0 | -0.499 |
| -0.12 | -30 | -0.118 | 121 | -0.119 |
| 0.00 | 0 | 0.000 | 159 | 0.000 |
| 0.07 | 18 | 0.071 | 181 | 0.069 |
| 0.30 | 76 | 0.299 | 255 | 0.301 |

Symmetric never uses the codes 77 to 127, because nothing in this row is that large and positive.
Asymmetric spends all 256 codes on the range that exists, so its step is about a fifth smaller
(0.0031 against 0.0039), for the price of one more stored number per channel. On a row balanced
around zero, the two come out about the same.

NNCF's default for weight compression is asymmetric, "INT8_ASYM mode", with INT8_SYM available
"for symmetric quantization without zero point". llama.cpp's Q8_0 is symmetric: each block holds
a 16-bit scale and 32 signed 8-bit values, nothing else.

## Why do 8-bit weights make a CPU faster?

A dense model reads essentially all its weights on every pass; fewer bytes take less time to
stream. OpenVINO's weight compression page says it "improves inference speed by reducing the
latency of memory access when computing the operations with weights".

The sizes are arithmetic: a billion weights take about 4 GB at 32 bits, 2 GB at 16 and 1 GB at
8, plus the scales. OpenVINO's table shows the step from 32 to 8 bits on real models: dolly-v2-3b
from 10.3 GB to 2.6 GB, Llama-2-7b-chat from 25.1 GB to 6.3 GB.

Time shrinks less than size, because reading a long prompt leans on arithmetic more than on
memory, as [prefill vs decode](prefill-vs-decode-llm-latency.md) explains; OpenVINO's trade-off
table rates its INT8 latency gain "Medium". jevos-v4 runs with 8-bit weights through OpenVINO
in about 1 GB of memory with the model loaded; the runtime side is on
[OpenVINO for LLM inference on a CPU](openvino-for-llm-inference-on-a-cpu.md).

## Weights only, or activations too?

Weight-only quantization keeps the activations, the values flowing through the model, in
floating point. In OpenVINO's words, unlike full model quantization, "where both weights and
activations are quantized", weight compression "only targets weights, keeping activations as
floating-point numbers", and needs no sample data to calibrate activation ranges.

Activations are the harder half. SmoothQuant (Xiao et al., 2022) starts from "the fact that
weights are easy to quantize while activations are not" and reports W8A8 (8-bit weights and
activations) up to 1.56 times faster with half the memory and "negligible loss in accuracy".
LLM.int8() (Dettmers et al., 2022) handles "emergent outliers" with a mixed-precision
decomposition.

A middle path works at run time: an OpenVINO blog post describes dynamic quantization of the
inputs to matrix multiplications, "effective when weights are already quantized into int4 or
int8", in groups whose size "impacts both performance and accuracy". The post covers GPUs and
says CPUs support it with behavior that "may differ slightly". jev has an option of that name, `--dynamic-quantization`, default 128,
documented at the top of `src/main.cpp`.

## How much accuracy does INT8 weight quantization cost?

Usually little on the models measured; nothing you can assume for yours.
OpenVINO's data-free table, perplexity on Lambada OpenAI (lower is better):

| Model | FP32 | INT8_ASYM | INT4_ASYM, mixed |
|---|---|---|---|
| dolly-v2-3b | 5.01 | 5.07 | 5.28 |
| Llama-2-7b-chat | 3.28 | 3.29 | 3.41 |

NNCF says both INT8 modes "typically preserve model accuracy", and OpenVINO warns that below 1B
parameters "low-bit weight compression may result in more accuracy reduction than with larger
models".

Being straight about the limit: perplexity measures how well a model predicts general text, not
whether a yes/no answer flips. No comparison of jevos at 8 bits against higher precision is
published, so we cannot give that cost for jevos. For any quantized build, run [a yes/no test set of your own data](building-a-yes-no-test-set.md) and check
calibration too, as on [LLM calibration explained](llm-calibration-explained.md).

## How does this relate to GGUF Q8_0 and Q4_K_M?

Q8_0's 32 values plus one 16-bit scale cost 8 + 16/32 bits per
weight, which is why llama.cpp's quantize README lists 8.5008 for its 8B example. A per-channel
scale over a channel of 1,000 weights (illustrative) adds only 0.016 bits. Q4_K_M, at 4.8944
bits per weight in the same README, uses super-blocks of 256 weights, decoded on
[GGUF quantization types explained](gguf-quantization-types-explained.md).

jevos-v4 comes three ways: the 8-bit OpenVINO model that `jev` runs, and `jevos-v4-q8_0.gguf`
(942,872,288 bytes) and `jevos-v4-q4_k_m.gguf` (619,289,312 bytes) for llama.cpp. The first two
are both "8-bit" yet different formats, and no comparison of their answers is published. Choosing
between the GGUF files is on [Q4_K_M vs Q8_0: speed and size](q4-k-m-vs-q8-0-speed-and-size.md).

## Short answers to the questions that lead here

**Is INT8 quantization lossless?** No: each weight is rounded to one of 255 or 256 levels, and in
OpenVINO's table perplexity moves a little.

**What is the difference between symmetric and asymmetric INT8?** Whether a zero point is stored.
Asymmetric fits the real minimum and maximum, which uses the codes better on lopsided ranges.

**Does INT8 make inference faster on a CPU?** Usually, with fewer bytes to move; measure on your
own hardware.

**Should I use INT8 or 4-bit?** INT8 stays closer to the original at a larger size; in OpenVINO's
table the 4-bit modes save more memory at a larger perplexity cost.

**See also:** [what is GGUF](what-is-gguf.md),
[what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md) and
[small language models explained](small-language-models-explained.md).

## Sources

- Our own facts: 8-bit weights through OpenVINO, about 1 GB of memory, the
  `--dynamic-quantization` default ([jev README](https://github.com/feder-cr/jev)); GGUF byte
  sizes ([Hugging Face model page](https://huggingface.co/feder-cr/jev)). The five-weight example
  and the overhead figures are our arithmetic, illustrative.
- All fetched 2026-10-12: Jacob et al.,
  [arXiv:1712.05877](https://arxiv.org/abs/1712.05877) (read in its [HTML version](https://ar5iv.labs.arxiv.org/html/1712.05877));
  [NNCF weight compression](https://github.com/openvinotoolkit/nncf/blob/develop/docs/usage/post_training_compression/weights_compression/Usage.md);
  [NNCF quantization schemes](https://github.com/openvinotoolkit/nncf/blob/develop/docs/usage/Quantization.md);
  [OpenVINO weight compression](https://github.com/openvinotoolkit/openvino/blob/master/docs/articles_en/openvino-workflow/model-optimization-guide/weight-compression.rst);
  [OpenVINO dynamic quantization post](https://blog.openvino.ai/blog-posts/dynamic-quantization-support-from-gpu-with-xmx);
  [SmoothQuant](https://arxiv.org/abs/2211.10438); [LLM.int8()](https://arxiv.org/abs/2208.07339);
  [llama.cpp quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md);
  [ggml-common.h](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-common.h).

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships jevos as one 8-bit
OpenVINO model and two GGUF builds, with no published comparison of their answers yet.*
