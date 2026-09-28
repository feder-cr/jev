---
title: "GGUF quantization types explained: Q4_K_M, Q8_0 and others"
description: "What GGUF quantization names mean: bits, _0 and _1 legacy types, K-quants, _S and _M mixes, IQ types and imatrix, and how to pick one for a classifier."
parent: "llama.cpp and GGUF"
nav_order: 2
---

# GGUF quantization types explained: Q4_K_M, Q8_0 and others

**A GGUF quantization name says how many bits each weight is stored in and which scheme packs
them: Q8_0 is 8-bit weights in blocks of 32 with one scale per block, Q4_K_M is a 4-bit
"K-quant" mix that keeps some tensors at 6 bits.** The number is the nominal bit width, the
suffix after the underscore is the scheme (`_0`, `_1`, `_K`), and a trailing `_S`, `_M` or `_L`
names a mix of types across tensors. Names starting with `IQ` are newer types built around an
importance matrix.

The practical reading is that fewer bits mean a smaller file and less memory traffic per token,
at some cost in accuracy that depends on the model and the task. The cost is not a property of
the name: it has to be measured on what you actually ask the model.

This page is a decoder for the names, a table of real bits per weight, what a mix is, what an
importance matrix does, and how the two jevos builds fit in.

## How to read a name

Take the name apart from left to right.

- **`Q` and a number**: quantized, with that many bits per weight before overhead. `F16`,
  `BF16` and `F32` are plain floating point, not quantized.
- **`_0` and `_1`**: the original "legacy" schemes. Weights are cut into blocks of 32; `_0`
  stores one scale per block (`w = q * block_scale`), `_1` stores a scale and a minimum
  (`w = q * block_scale + block_minimum`). Q4_0, Q4_1, Q5_0, Q5_1 and Q8_0 are all legacy.
- **`_K`**: the K-quants, added to llama.cpp in June 2023. Blocks are grouped into super-blocks
  and the per-block scales are themselves quantized, which spends fewer bits on overhead. Q4_K,
  for example, uses super-blocks of 8 blocks of 32 weights with 6-bit scales and minimums, for
  4.5 bits per weight.
- **`_S`, `_M`, `_L`**: small, medium, large. These are not new storage types but recipes that
  decide which tensors get a higher-precision type.
- **`IQ`**: types such as IQ4_NL, IQ4_XS, IQ3_S and IQ2_XXS use super-blocks of 256 weights and
  are designed to be used with an importance matrix. They extend to much lower bit rates: IQ1_S
  is listed at 1.56 bits per weight, against 2.625 for Q2_K, the smallest K-quant.

There are also ternary types (TQ1_0, TQ2_0) and MXFP4, a 4-bit block floating point type, which
you will meet less often.

## Real bits per weight

The nominal number understates the file size, because scales and mixes add bits. The
llama-quantize README publishes the effective figures for its 8B reference model:

| Type | Bits per weight | Size of the 8B reference |
|---|---|---|
| IQ4_XS | 4.46 | 4.17 GiB |
| Q4_K_S | 4.67 | 4.36 GiB |
| IQ4_NL | 4.68 | 4.38 GiB |
| Q4_K_M | 4.89 | 4.58 GiB |
| Q5_K_M | 5.70 | 5.33 GiB |
| Q6_K | 6.56 | 6.14 GiB |
| Q8_0 | 8.50 | 7.95 GiB |
| F16 | 16.00 | 14.96 GiB |

Q8_0 costs 8.5 bits, not 8, because each block of 32 weights carries its scale. Q4_K_M costs
almost 4.9, not 4.5, because of the tensors the mix keeps at higher precision.

## What the M in Q4_K_M changes

When the K-quants were introduced, the pull request described the two 4-bit recipes this way:
Q4_K_S "uses GGML_TYPE_Q4_K for all tensors", while Q4_K_M "uses GGML_TYPE_Q6_K for half of the
attention.wv and feed_forward.w2 tensors, else GGML_TYPE_Q4_K". The idea is that some weight
matrices are more sensitive to rounding than others, so spending extra bits on them buys back
more quality than spreading the same bits evenly. The recipe lives in llama.cpp's code and can
change between releases, so read that 2023 description as the idea, not as a specification of
every Q4_K_M file you download.

## What an importance matrix does

`llama-quantize --imatrix file` takes an importance matrix, data that tells the quantizer which
weights matter most, and uses it, in the README's words, "for quant optimizations". The README
puts the
general trade plainly: quantization "may introduce some accuracy loss which is usually measured
in Perplexity (ppl) and/or Kullback-Leibler Divergence (kld). This can be minimized by using a
suitable imatrix file." The IQ types rely on it; K-quants can use it too.

For a classifier, note what those two metrics measure: how close the quantized model's
next-token predictions stay to the original on general text. They are a good sign, not a
measurement of your yes/no accuracy.

## The two jevos builds

jevos ships two files: `jevos-q4_k_m.gguf` at 619 MB and `jevos-q8_0.gguf` at 943 MB. On the
reference laptop (Intel Core Ultra 7 255H, 16 threads, no GPU), q8_0 is about 1.7 times slower
than q4_k_m; q4_0 and iq4_nl builds ran about as fast as q4_k_m. The speed and size side of that
choice has its own page, [Q4_K_M vs Q8_0 for a small model](q4-k-m-vs-q8-0-speed-and-size.md).

Being straight about the limit: the accuracy of q4_k_m and q8_0 has not been measured on the
same question set. Our published numbers come from different sets on different builds, so they
cannot be subtracted to give a quantization cost. If the difference matters to you, run both
files on your own labelled cases.

## Picking a type for a decision model

- **Start with Q4_K_M.** It is the type in the llama-quantize README's basic example and the
  build the jev quickstart uses. On our reference CPU the smaller file was also the faster
  one, for reasons explained on
  [what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md).
- **Use Q8_0 when you want the reference.** It is closest to the original weights, costs more
  memory and time, and is the natural baseline to test a smaller build against.
- **Go below 4 bits only with a test set.** IQ3 and IQ2 files are much smaller, and small models
  have the least spare capacity to lose. Measure on [a yes/no test set of your own
  data](building-a-yes-no-test-set.md) before shipping one.

## Short answers to the questions that lead here

**What does K mean in Q4_K_M?** It marks the K-quants, a scheme with super-blocks and quantized
block scales. The M means the medium mix, which keeps some tensors at a higher-precision type.

**Is Q8_0 lossless?** No. It is 8-bit round-to-nearest with one scale per 32 weights. It is
close to the original, but it is still a quantization.

**What is the difference between Q4_0 and Q4_K_M?** Q4_0 is a legacy type with one scale per
block of 32; Q4_K_M uses super-blocks, quantized block scales and a mix of types across
tensors.

**Do I need an imatrix?** Not for Q8_0 or the common K-quants, though it can help. The IQ types
are designed around one.

**Which quantization is most accurate for classification?** Nobody can say from the name. The
higher-bit types are usually closer to the original model; measure the ones you consider.

**See also:** [what is GGUF](what-is-gguf.md),
[GGUF vs safetensors](gguf-vs-safetensors.md) and
[run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md).

## Sources

- Our own measurements: file sizes from the
  [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos); relative speed of
  q8_0, q4_0 and iq4_nl against q4_k_m on the reference laptop; the statement that accuracy of
  the two builds was not compared on one set.
- [llama-quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md),
  fetched 2026-09-29: bits per weight and sizes, imatrix option, the accuracy-loss sentence.
- [Hugging Face Hub docs: GGUF quantization types](https://huggingface.co/docs/hub/gguf),
  fetched 2026-09-29: block and super-block structure and weight formulas.
- [llama.cpp pull request 1684, k-quants](https://github.com/ggml-org/llama.cpp/pull/1684),
  fetched 2026-09-29: Q4_K_S and Q4_K_M recipes as first described, June 2023.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships a 4-bit and an 8-bit
build so that anyone can test the smaller one against the larger on their own questions.*
