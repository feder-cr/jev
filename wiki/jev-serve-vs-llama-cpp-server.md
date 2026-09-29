---
title: "jev serve vs llama.cpp server for classification"
description: "llama-server is a general completion and chat server; jev serve is one decision endpoint. What you would build yourself on llama-server to get P(yes)."
parent: "Comparisons"
nav_order: 9
---

# jev serve vs llama.cpp server for classification

**llama.cpp's `llama-server` is a general server for completions, chat, embeddings and reranking;
`jev serve` runs one yes/no model through llama.cpp behind one decision endpoint, `POST
/v1/systemone`, that returns P(yes) per question.** Both are local, both use llama.cpp, and
llama-server gives you every building block a decision service needs. What it does not give you is
the service: the prompt, the reading of a yes/no probability from token alternatives, several
questions sharing one text, and a stable request and answer format. If you want those built,
`jev serve` has them; if you want full control or a different model, llama-server is the
foundation to build on.

Conflict of interest, in one line: we build jev; the llama-server facts are from its README in
the llama.cpp repository, fetched 2026-09-29.

The two are not rivals in the usual sense. jev uses official prebuilt llama.cpp binaries, fetched
by `uv run jev download --only runtime` and driven through ctypes, so the question is how much of
the layer above llama.cpp you want to own.

This page is what llama-server provides, the gap to a decision endpoint, a sketch of filling it
yourself, the extras `jev serve` adds, and when llama-server is the better choice.

## What llama-server gives you

Its README calls it a "fast, lightweight, pure C/C++ HTTP server based on httplib, nlohmann::json
and llama.cpp." The feature list includes OpenAI-compatible chat completion, completion and
embedding routes, an Anthropic Messages compatible route, a reranking endpoint, parallel decoding
with multiple users through slots, grammar and JSON schema constraints, prompt caching, and token
probabilities. It listens on 127.0.0.1:8080 by default, takes `--api-key` for authentication, and
exposes `/health` and `/tokenize`.

For classification, three options on `/completion` matter most:

- **`n_predict`**: the maximum number of tokens to generate. The README notes that at 0 "no
  tokens will be generated but the prompt is evaluated into the cache."
- **`n_probs`**: "If greater than 0, the response also contains the probabilities of top N tokens
  for each generated token."
- **`cache_prompt`**: re-use the KV cache from a previous request so that "the common prefix does
  not have to be re-processed."

There are also `grammar` and `json_schema` for constraining generation, and `logit_bias` for
nudging specific tokens.

## The gap between a completion server and a decision endpoint

To turn llama-server into a yes/no service you would write:

1. **A prompt** that frames the text and the question for your chosen model, including its chat
   template, and makes a one-token answer the natural continuation.
2. **A probability reader.** With `n_predict` at 1 and `n_probs` set, you get the top alternatives
   for the first generated token. You then find which of them mean yes and which mean no, across
   tokenizer variants such as "Yes", " yes" and "YES", and turn their probabilities into one
   P(yes). If neither appears in the top N, you need a policy for that.
3. **A request format** for several named questions about one text, and code that sends them so
   the shared text benefits from `cache_prompt`.
4. **Validation and errors**: what a missing field, an over-long text or an unknown question type
   returns.
5. **Calibration checks** on your own labelled cases, because a general chat model's token
   probabilities for "yes" are not necessarily calibrated for your questions.

None of this is hard in isolation. Together it is a small project, and each piece has edge cases.

## A sketch of the first two steps

An untested sketch, to show the shape, not a recipe. It asks llama-server for one token with its
top alternatives:

```bash
curl http://127.0.0.1:8080/completion -H 'Content-Type: application/json' -d '{
  "prompt": "<your template around the text and the question>",
  "n_predict": 1,
  "n_probs": 10,
  "cache_prompt": true
}'
```

The `completion_probabilities` field of the response holds, for the generated token, a
`top_logprobs` list of up to `n_probs` entries with the token text and its log probability. From
there, step 2 above is your code. The general reason this route still costs a decode step is on
[why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md).

## What jev serve adds

`jev serve --gguf jevos-v2-q4_k_m.gguf --device cpu --threads 16` gives you, on 127.0.0.1:8017:

- **One endpoint, one answer shape.** `state` (text or any JSON) plus named questions in; each
  question back as `{"type": "noul", "noul": ...}`, with `output_tokens` always 0.
- **Shared reading of the text.** Questions in one request share the state, which is read once:
  three questions took about 165 ms against 103 ms for one on our reference laptop.
- **A wire format someone else defined.** It is TypeSafe Jev's, so clients written for Jev's SDK
  work unchanged for yes/no questions, as described on
  [an open-source alternative to Jev](open-source-alternative-to-jev.md).
- **Provenance.** `GET /health` reports the model file's sha256, the llama.cpp release and the
  device; every response carries a `Server-Timing` header.
- **A model built for yes/no questions**, not a general chat model prompted into answering
  them, with calibration measured on held-out questions (0.009 on 6,397 natural yes/no
  questions).
- **Server-free batch use.** `jev decide` answers a request file with no server, and a request
  without `model` returns the engine's full output, including probabilities, prompt hashes and
  timings.

What it does not add: generation, chat, embeddings, other models, or `choice` and `score`
questions, which are refused with a `422` for now.

## When llama-server is the better choice

- You want a different or larger model, or several.
- You need generation, embeddings or reranking from the same process.
- You need parallel slots for many concurrent users; jev's documented numbers are single-request
  latency, not capacity, a distinction made on
  [throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).
- You want to own every line of the prompt and the probability logic.

## Short answers to the questions that lead here

**Can llama.cpp server do classification?** Yes, with your own prompt and code that reads token
probabilities from `n_probs`. It gives the parts, not the classifier.

**Does jev serve use llama-server?** No. It drives official prebuilt llama.cpp binaries through
ctypes and exposes its own endpoint.

**How do I get a yes/no probability from llama-server?** Generate one token with `n_probs` set,
then add up the probabilities of the tokens that mean yes and those that mean no, and normalise.

**Which one is faster?** We have not measured llama-server with a comparable setup. jevos took 54
and 220 ms on our two requests on an Intel Core Ultra 7 255H.

**Can I run both?** Yes; they default to different ports, 8080 and 8017.

**See also:** [llama-cpp-python vs ctypes](llama-cpp-python-vs-ctypes.md),
[using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md) and
[curl examples for a local LLM decision API](curl-examples-for-a-local-llm-api.md).

## Sources

- llama-server description, features, default host and port, `--api-key`, `/health`,
  `/tokenize`, `n_predict`, `n_probs`, `cache_prompt`, `grammar`, `json_schema`, `logit_bias` and
  `completion_probabilities`: the
  [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
  fetched 2026-09-29.
- `jev serve`, `jev decide`, the endpoints, `Server-Timing` and the 422: the
  [jev README](https://github.com/feder-cr/jev); latency figures are our own measurements.
- Calibration error 0.009: our held-out split, 6,397 natural yes/no questions, `jevos-q8_0`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which stands on llama.cpp and says so.*
