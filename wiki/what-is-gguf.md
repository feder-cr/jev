---
title: "What is GGUF, for someone deploying a classifier"
description: "GGUF is one binary file holding a model's tensors and the metadata needed to run it with llama.cpp. What is inside and why it simplifies deployment."
parent: "llama.cpp and GGUF"
nav_order: 1
---

# What is GGUF, for someone deploying a classifier

**GGUF is a single binary file that holds a model's weights together with everything needed to
load and run it: the architecture name, the tokenizer, the prompt template and the quantization
type.** It is the native format of llama.cpp and of the engines built on ggml. For deployment
that means the model is one artifact: you copy one file, check one hash, and point a runtime at
it. No folder of configs and tokenizer files has to travel with it.

The non-obvious point for a classifier is that the file is also the model's identity. If the
hash of the file is the same, the weights, the tokenizer and the template are the same, so the
same request gives the same answer on the same runtime. That makes the file hash the thing to
log, to pin in a deployment and to check after a download.

This page is what is inside a GGUF file, why the single-file design matters when you ship a
decision model, which metadata is worth reading, where GGUF files come from, and what the
format does not tell you.

## What is inside one GGUF file

The format is specified in the ggml repository. A file is laid out in order:

- a magic number (the bytes "GGUF") and a format version, currently 3;
- the number of tensors and a list of metadata key-value pairs;
- one info record per tensor: name, dimensions, type and offset;
- padding to an alignment boundary (32 bytes unless the file says otherwise);
- the tensor data itself.

The spec lists its own goals plainly: single-file deployment ("do not require any external
files"), extensibility without breaking old readers, mmap compatibility so models load fast,
ease of use without external libraries, and "all information needed to load a model is
contained in the model file." GGUF replaced three earlier ggml formats (GGML, GGMF and GGJT),
which lacked versioning, a way to name the architecture, or both.

## Why one file matters when you ship a decision model

A classifier in production is usually a small service that must be reproducible and boring.
Three properties of GGUF help directly.

**One artifact to verify.** The jevos release includes the model as two GGUF files, for
llama.cpp, Ollama, LM Studio and other tools: `jevos-v2-q4_k_m.gguf` (619 MB) and
`jevos-v2-q8_0.gguf` (943 MB), plus a `SHA256SUMS.txt`. Checking one file against one line of
that list tells you the whole model arrived intact, which is what makes
[offline and air-gapped use](offline-ai-for-decisions.md) practical.

**One artifact to identify.** One sha256 covers the weights, the tokenizer and the template
together. If you run a GGUF and [log decisions for audit](logging-llm-decisions-for-audit.md),
that hash is the field that says which model produced a probability.

**Fast, cheap loading.** Because tensors sit at aligned offsets, a runtime can memory-map the
file instead of parsing and copying it. llama.cpp's default load mode maps the model unless the
device does not support it.

## The metadata keys worth reading

Most of what a deployer wants to know is in the key-value section, before any weights:

| Key | What it tells you |
|---|---|
| `general.architecture` | which model family the runtime must implement |
| `general.file_type` | the overall quantization of the file |
| `general.quantization_version` | required when tensors are quantized |
| `general.name`, `general.version` | human labels set by whoever converted it |
| `tokenizer.ggml.model` | the tokenizer type |
| `tokenizer.chat_template` | the Jinja template that turns messages into a prompt |

You do not need to write a parser to see them. The Hugging Face Hub has a viewer that shows a
GGUF file's metadata and tensor list on the model page, and the `@huggingface/gguf` JavaScript
package reads the header of a remotely hosted file without downloading the weights.

jev itself does not read GGUF files: it runs the same model with 8-bit (INT8) weights through
OpenVINO, from the `model` folder beside the binary. Its tokenizer is llama.cpp's, compiled in,
so its token ids match the GGUF files.

## Where GGUF files come from and what reads them

Models are usually developed in PyTorch and stored as safetensors. The llama.cpp repository
ships `convert_hf_to_gguf.py` to turn such a checkpoint into GGUF, and the `llama-quantize` tool
to turn a high-precision GGUF (F32 or BF16) into a smaller quantized one. The quantization names
you see on file names, such as Q4_K_M, are explained on
[GGUF quantization types explained](gguf-quantization-types-explained.md).

On the reading side, the Hugging Face docs list llama.cpp, LM Studio, GPT4All and Ollama as
tools that use GGUF. Ollama's import guide takes a GGUF path in a Modelfile and says plainly
that Ollama does not quantize GGUF files during import. What Ollama adds on top of llama.cpp,
and whether a classification service needs it, is on
[llama.cpp vs Ollama for a classification service](llama-cpp-vs-ollama-for-classification.md). Transformers can also load a GGUF, but
on most devices it dequantizes the weights at load time into an ordinary dense model, which
gives up the size advantage. The comparison with the other common format is on
[GGUF vs safetensors](gguf-vs-safetensors.md).

## What GGUF does not tell you

Being straight about the limit: GGUF is a container, not a certificate.

- **It does not say how well the model does your task.** Two files with the same metadata can
  answer your questions very differently. Only a [test set built from your own
  cases](building-a-yes-no-test-set.md) tells you that.
- **The file name is a convention.** The spec recommends a naming pattern (base name, size
  label, version, encoding) but nothing enforces it. Read `general.file_type` and the hash, not
  the name.
- **It does not pin the runtime.** A new llama.cpp release can read the same file with
  different kernels. For reproducible answers, pin the runtime release as well as the file.

## Short answers to the questions that lead here

**Is GGUF only for llama.cpp?** It is llama.cpp's native format, and the Hugging Face docs
list other local tools that use it, including Ollama and LM Studio. Transformers can load it too, usually by dequantizing it.

**Can I use my own GGUF with jev?** No. jev does not read GGUF files. To run a GGUF, your own
or the two jevos release files, use llama.cpp, Ollama or LM Studio directly.

**How do I check a downloaded GGUF is intact?** Compare its sha256 with the published list. For
jevos that is `SHA256SUMS.txt` on the release page.

**Does a GGUF file contain the tokenizer?** Yes. The tokenizer and, usually, the chat template
are metadata keys inside the file.

**What does the version number in the header mean?** It is the format version, currently 3. It
says nothing about the model's own version, which lives in `general.version` if set.

**See also:** [GGUF quantization types explained](gguf-quantization-types-explained.md),
[using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md) and
[self-hosted AI for decisions](self-hosted-ai-for-decisions.md).

## Sources

- Our own facts: the release file names, sizes and `SHA256SUMS.txt`, from the
  [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos-v2); the INT8 model and
  the llama.cpp tokenizer, from the jev source code.
- [GGUF specification, ggml repository](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md),
  fetched 2026-09-29: layout, goals, metadata keys, naming convention, predecessor formats.
- [Hugging Face Hub docs: GGUF](https://huggingface.co/docs/hub/gguf), fetched 2026-09-29:
  metadata viewer, `@huggingface/gguf`, tools that use GGUF.
- [llama-quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)
  and [llama.cpp completion README](https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/README.md)
  (load modes), fetched 2026-09-29.
- [Ollama import guide](https://docs.ollama.com/import) and
  [Transformers GGUF docs](https://huggingface.co/docs/transformers/gguf), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships its model as an OpenVINO
build for its own binary and, for other tools, as two GGUF files and a text file with their
hashes.*
