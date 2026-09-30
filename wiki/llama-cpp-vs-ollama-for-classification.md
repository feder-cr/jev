---
title: "llama.cpp vs Ollama for a classification service"
description: "llama-server gives you low-level control, Ollama gives you model management. What each offers when the job is one yes/no probability per request."
parent: "llama.cpp and GGUF"
nav_order: 4
---

# llama.cpp vs Ollama for a classification service

**For a classification service, llama.cpp's `llama-server` gives you more control over how the
model runs, and Ollama gives you easier model management; neither returns a class
probability out of the box, so with both you generate one token and read its probability.**
Ollama's README credits llama.cpp as its supported backend, so the difference is less the
engine than the layer on top: flags and a pinned release on one side, `ollama pull`, a model
store and automatic loading and unloading on the other.

Conflict of interest: we build jevos and `jev serve`, a dedicated decision server for
exactly this job. We build neither llama.cpp nor Ollama, and both are good at what they are for.

The point that decides most choices is not speed but the contract. A classifier needs the same
prompt, the same model file and the same parsing on every call, and a number at the end. Both
servers are designed around chat and text generation, so that contract is something you build
on top.

This page is what each project is, what a classification endpoint needs, how to get a
probability from each, the operational differences, and when neither is the simplest answer.

## What each project is

**llama.cpp** describes itself as "LLM inference in C/C++". Its `llama-server` is a "fast,
lightweight, pure C/C++ HTTP server" with OpenAI-compatible chat completions, responses and
embeddings routes, a native `/completion` route, `/tokenize`, `/reranking`, `/health`,
continuous batching, parallel slots and schema-constrained JSON output. You choose the model
file, the context size (`-c`), the threads (`-t`), the devices (`--device`) and the number of
slots (`-np`) on the command line.

**Ollama** is a model runner with a CLI (`pull`, `run`, `create`, `serve`, `ps`, `list`, `rm`)
and a REST API on port 11434, with `/api/generate` and `/api/chat`. It manages a local model
store, imports GGUF or safetensors through a Modelfile, and loads models on demand. Its FAQ
states the defaults that matter for a service: it binds 127.0.0.1:11434, keeps a model in memory
for 5 minutes after use, processes 1 request per model at a time
(`OLLAMA_NUM_PARALLEL`), and uses a 4096-token context unless told otherwise.

## What a classification endpoint actually needs

Whatever the server, a yes/no or label decision needs five things:

1. **A fixed prompt.** The text and the question are placed in the same template every time.
2. **A number, not a word.** You want P(yes), so you can set a threshold; parsing "Yes.",
   "yes" or "Yes, because..." is the fragile part.
3. **Cheap extra questions.** Several questions about one text should not each pay to read the
   text again.
4. **A pinned model.** The file hash and the runtime version should be known for every answer.
5. **Predictable latency.** No cold load in the middle of traffic.

Neither server offers items 2 and 3 as a ready-made classification feature; both give you the
pieces.

## Getting a probability from each

With **llama-server**, the native `/completion` route takes `n_probs`, which returns "the
probabilities of top N tokens for each generated token", and `post_sampling_probs` turns them
into probabilities between 0 and 1 after the sampling chain. You ask for one token, read the
probability of the "yes" token and of the "no" token, and normalize.

With **Ollama**, `/api/generate` accepts `logprobs` ("whether to return log probabilities of
the output tokens") and `top_logprobs`. Same approach: one output token, read the candidates.

The pieces you then write yourself, on either server, are the same:

- the prompt template, and `raw` mode or the model's chat template applied consistently;
- the list of tokens that mean yes and no for that tokenizer (with and without a leading space,
  upper and lower case), since a probability split across variants undercounts both;
- a fallback when neither yes nor no is among the top candidates;
- one call per question, unless you manage prompt caching yourself.

That is the gap `jev serve` fills; the detail of what you would build on llama-server is on
[jev serve vs llama.cpp server](jev-serve-vs-llama-cpp-server.md). The underlying reason one
forward pass is enough, and generating is not needed, is on
[why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md).

## The operational differences

| | llama-server | Ollama |
|---|---|---|
| Model source | a GGUF path, or `-hf` from the Hub | `ollama pull` or a Modelfile import |
| Context | from the model unless `-c` is set | 4096 tokens by default |
| Idle model | not documented as unloaded | unloaded after 5 minutes by default |
| Concurrency | parallel slots, continuous batching | 1 parallel request per model by default |
| Probabilities | `n_probs` on `/completion` | `logprobs`, `top_logprobs` on `/api/generate` |

Two rows matter most for classification. The **context default**: a long document plus
instructions can exceed 4096 tokens, so on Ollama set the context explicitly. The **idle
unload**: a classifier that runs every few minutes will pay a model load on some requests unless
`keep_alive` is raised. Both are one setting; both are easy to miss.

## When each one fits

- **Ollama** fits if you already run it for chat, want several models on one machine, or value
  `pull` and automatic memory management over flags. A handful of classifications through
  `logprobs` is reasonable there.
- **llama-server** fits if you want one pinned model file and one pinned release per service,
  explicit threads and devices, and parallel slots under load.
- **A dedicated decision server** fits if the whole job is yes/no answers. jevos returns P(yes)
  per question with `output_tokens` always 0, reads the shared text once for several questions
  (three questions take about 66 ms against 49 ms for one on the reference laptop), and
  reports the served model in `/health`. It is English only and answers
  yes/no questions only; a comparison at the product level is on
  [jevos vs Ollama for yes/no decisions](jevos-vs-ollama-for-yes-no-decisions.md).

## Short answers to the questions that lead here

**Does Ollama use llama.cpp?** Ollama's README lists "llama.cpp project founded by Georgi
Gerganov" under supported backends.

**Can llama-server return class probabilities?** Not as classes. `/completion` with `n_probs`
returns the probabilities of the top tokens for each generated token; you map tokens to labels.

**Can Ollama return logprobs?** Yes. `/api/generate` takes `logprobs` and `top_logprobs`.

**Which is faster for classification?** There is no general answer. It depends on the file,
the context, the threads and whether the model was already loaded. Measure both on your
hardware with the same GGUF and the same prompt.

**Why not just ask the model to answer "yes" or "no" in text?** You can, but then you parse
text, lose the confidence, and pay for decoding.

**See also:** [structured output vs a probability](structured-output-vs-a-probability.md),
[using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md) and
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).

## Sources

- Our own facts: jevos outputs one probability per question with zero output tokens; the 66 ms
  and 49 ms timings on the reference laptop; `/health` contents. From the
  [jev README](https://github.com/feder-cr/jev) and source code.
- [llama.cpp repository](https://github.com/ggml-org/llama.cpp) and
  [llama-server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
  fetched 2026-09-29: features, endpoints, `n_probs`, `post_sampling_probs`, command-line options.
- [Ollama README](https://github.com/ollama/ollama), [Ollama FAQ](https://docs.ollama.com/faq),
  [Ollama generate API](https://docs.ollama.com/api/generate) and
  [Ollama import guide](https://docs.ollama.com/import), fetched 2026-09-29: CLI, port, defaults
  for keep-alive, parallelism and context, `logprobs`.
- [Hugging Face docs: GGUF with llama.cpp](https://huggingface.co/docs/hub/gguf-llamacpp),
  fetched 2026-09-29: the `-hf` option.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a decision server whose model also
ships as GGUF files that either of them can load.*
