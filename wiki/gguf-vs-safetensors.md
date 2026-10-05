---
title: "GGUF vs safetensors"
description: "safetensors stores raw tensors for framework code; GGUF stores quantized tensors plus run metadata for llama.cpp. When each format is the right one."
parent: "llama.cpp and GGUF"
nav_order: 3
---

# GGUF vs safetensors

**safetensors is a safe, fast container for raw tensors, used by Transformers, Diffusers and
other framework code; GGUF is a container for tensors plus the metadata needed to run a model,
built for llama.cpp and the tools around it.** A safetensors file needs the model code and
config files beside it to become a model; a GGUF file carries the architecture name, tokenizer
and prompt template inside. In practice safetensors is where models are trained and published,
and GGUF is what you convert them to for quantized local inference on a CPU or a small GPU.

The two are not rivals so much as two ends of a pipeline. safetensors was made as a safe
alternative to pickle-based checkpoints, and GGUF, like it, is a plain data layout with no code
to execute. Where they differ is in what else they promise: safetensors keeps the format
deliberately minimal, GGUF packs in everything an inference engine needs.

This page compares what each file holds, which runtimes read which, how quantization fits,
how to convert between them, and which one a decision service should ship.

## What each file holds

**safetensors** is small enough to describe in three lines. The first 8 bytes are an unsigned
little-endian integer giving the header size N. The next N bytes are a UTF-8 JSON header mapping
each tensor name to its `dtype`, `shape` and `data_offsets`. The rest is the tensor data. A
special `__metadata__` key allows a free-form string-to-string map, and nothing more structured.
The rules are strict: no duplicate keys, a header capped at 100 MB, little-endian, row-major
layout, and a byte buffer with no holes.

**GGUF** starts with a magic number and a format version, then a list of typed key-value
metadata, one info record per tensor, alignment padding and then the data. The metadata is
standardized: `general.architecture`, `general.file_type`, tokenizer tokens and scores, and
`tokenizer.chat_template`, among others. The spec's stated goal is that "all information needed
to load a model is contained in the model file." The details are on
[what is GGUF](what-is-gguf.md).

| | safetensors | GGUF |
|---|---|---|
| What it stores | tensors, plus an optional string map | tensors plus standardized typed metadata |
| Tokenizer and template | separate files next to it | inside the file |
| Quantized block types | not a goal of the format | native (Q4_K_M, Q8_0, IQ types...) |
| Loading | zero-copy, lazy loading of single tensors | mmap-friendly aligned layout |
| Main readers | Transformers, Diffusers, MLX, Candle and many more | llama.cpp, Ollama, LM Studio, GPT4All |
| Typical role | training, fine-tuning, publishing | local quantized inference |

## Which runtimes read which

The safetensors project lists a long set of users, among them `huggingface/transformers`,
`ml-explore/mlx`, `huggingface/candle` and `huggingface/diffusers`, and its comparison table
credits it with zero-copy reads, lazy loading and no file size limit. The Hugging Face Hub docs
call safetensors "a recommended model format for the Hub".

The same Hub docs list llama.cpp, LM Studio, GPT4All and Ollama as tools that use GGUF. Ollama
can import either: its import guide takes a GGUF file or a safetensors directory in a Modelfile.

Transformers can also load a GGUF with `from_pretrained(..., gguf_file=...)`, but its docs say
that outside one fast path on Apple Metal the model is dequantized at load time into a plain
dense model. That is useful to get weights back into PyTorch; it is not a way to run the
quantized file efficiently.

## Where quantization fits

This is the real dividing line. A safetensors file stores tensors in standard dtypes (the
project's table notes support for Bfloat16 and Fp8). GGUF was built alongside ggml's
block-quantization types, where weights are stored in small blocks with their scales, so a
4-bit model is simply a GGUF whose tensors have a 4-bit type. `llama-quantize` works GGUF to GGUF:
it takes a high-precision GGUF (typically F32 or BF16) and writes a quantized one. What the
type names mean is explained on [GGUF quantization types
explained](gguf-quantization-types-explained.md).

For a model that must run [locally without a GPU](run-an-llm-locally-without-a-gpu.md), that is
the reason GGUF wins by default: the 4-bit file is smaller, and on a CPU smaller usually means
faster.

## Converting between them

The usual direction is safetensors to GGUF. The llama.cpp repository ships
`convert_hf_to_gguf.py`, which reads a Hugging Face checkpoint and writes a GGUF, typically at
high precision, and then `llama-quantize` makes the smaller builds. The Hub also offers a
`gguf-my-repo` space that does both steps online.

The other direction exists through the Transformers GGUF loader, which dequantizes. Keep in mind
that a quantized GGUF turned back into floating point is not the original checkpoint: the
rounding is already in the weights.

## Which one should a decision service ship?

Being straight about it: it depends on what you plan to do with the model, not on which format
is better.

- **You will fine-tune or retrain on your labels.** Keep the safetensors checkpoint. Training
  frameworks read it, and quantized GGUF weights are the wrong starting point. The trade-off
  between zero-shot questions and a trained classifier is covered on
  [a yes/no LLM vs a fine-tuned BERT classifier](yes-no-llm-vs-fine-tuned-bert.md).
- **You will serve it on CPUs with llama.cpp.** Ship GGUF. One file, one hash, and the
  tokenizer and template cannot drift away from the weights.
- **You run a GPU serving stack built on PyTorch.** safetensors is the native input there.

jevos-v4 ships as GGUF, `jevos-v4-q4_k_m.gguf` and `jevos-v4-q8_0.gguf`, for
llama.cpp and the tools around it, and as `jevos-v4-openvino-int8.zip`, the 8-bit OpenVINO model
that the jev decision server runs on the CPU. There is no safetensors release to download.

## Short answers to the questions that lead here

**Is GGUF better than safetensors?** Neither is better in general. safetensors is the standard
for framework code and training; GGUF is the standard for quantized inference with llama.cpp.

**Is safetensors safe and is GGUF safe?** Both avoid pickle and store data, not code. safetensors
adds explicit limits such as the 100 MB header cap to resist malformed files.

**Can llama.cpp load safetensors directly?** llama.cpp runs GGUF files; a safetensors checkpoint
is converted first, with the `convert_hf_to_gguf.py` script from the same repository.

**Can I get a safetensors file back from a GGUF?** Transformers can load a GGUF and dequantize
it, and you can save the result. It keeps the quantization rounding.

**Does jevos come as safetensors?** No. The release has the two GGUF files, the OpenVINO model
that jev runs, and the jev binaries.

**See also:** [what is GGUF](what-is-gguf.md),
[llama.cpp vs Ollama for a classification service](llama-cpp-vs-ollama-for-classification.md)
and [self-hosted AI for decisions](self-hosted-ai-for-decisions.md).

## Sources

- Our own facts: the jevos release files, from the
  [release page](https://github.com/feder-cr/jev/releases/tag/jevos-v4).
- [safetensors repository README](https://github.com/huggingface/safetensors) and
  [safetensors docs](https://huggingface.co/docs/safetensors/index), fetched 2026-09-29: format,
  constraints, comparison table, list of projects using it.
- [GGUF specification](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md), fetched
  2026-09-29.
- [Hugging Face Hub docs: GGUF](https://huggingface.co/docs/hub/gguf) and
  [Transformers GGUF docs](https://huggingface.co/docs/transformers/gguf), fetched 2026-09-29.
- [llama-quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md),
  the [llama.cpp repository](https://github.com/ggml-org/llama.cpp) (conversion scripts) and the
  [Ollama import guide](https://docs.ollama.com/import), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which runs an 8-bit OpenVINO model
and ships GGUF files for every other tool.*
