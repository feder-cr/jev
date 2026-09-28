---
title: "jevos vs LM Studio: a decision server, not a chat app"
description: "LM Studio is a desktop app to find, chat with and serve local models; jevos is a headless yes/no decision server. Different jobs, one machine."
parent: "Comparisons"
nav_order: 10
---

# jevos vs LM Studio: a decision server, not a chat app

**LM Studio is a desktop application for downloading, chatting with and serving local language
models; jevos is a headless server that answers yes/no questions about a text with a
probability.** They do different jobs. LM Studio is where you try models, talk to them, build
prompts and expose an OpenAI-compatible endpoint for generation. jevos is what an application
calls, thousands of times, when it needs a decision and a number to threshold, with no chat and
no generated text. On one machine they coexist fine, on different ports.

Conflict of interest, in one line: we build jevos; the LM Studio facts come from lmstudio.ai and
its documentation, fetched 2026-09-29.

The comparison comes up because both mean "a local LLM on my computer". The useful question is
who is on the other end: a person at a chat window, or a program waiting for a yes or a no.

This page is what LM Studio is for, what jevos is for, the overlap in serving, how to run them
side by side, and which to reach for by task.

## What LM Studio is for

Its documentation lists what the app does: download and run local LLMs, "use a simple and
flexible chat interface", "connect MCP servers and use them with local models", search and
download models via Hugging Face, "serve local models on OpenAI-like endpoints, locally and on
the network", and manage local models, prompts and configurations. It is available for macOS,
Windows and Linux, runs models with llama.cpp on all three and additionally with Apple's MLX on
Apple Silicon Macs, and "can operate entirely offline" once you have model files.

For developers there is more. The docs list OpenAI-compatible endpoints (`/v1/models`,
`/v1/responses`, `/v1/chat/completions`, `/v1/embeddings`, `/v1/completions`), an Anthropic
compatible Messages API, structured output with JSON schema, the `lmstudio-js` and
`lmstudio-python` SDKs, bearer token authentication, and a quick start on port 1234. Existing
OpenAI clients can be pointed at it "by switching up the 'base URL' property."

It also runs without the window. The headless docs describe `llmster`, "the core of the LM Studio
desktop app, packaged to be server-native, without reliance on the GUI", started with
`lms daemon up`, plus options to run the server on login and to load a model just in time when a
request names it.

## What jevos is for

jevos does one thing. A server started with

```bash
uv run jev serve --gguf jevos-q4_k_m.gguf --device cpu --threads 16
```

listens on 127.0.0.1:8017, loads one model file (about 1.2 GB of memory), and answers
`POST /v1/systemone`: a `state`, which is a text or any JSON object, plus named yes/no questions,
each answered with its own `noul`, the probability of yes. Nothing is generated, so
`output_tokens` is 0 and there is no text to parse. The wire format is TypeSafe Jev's, not
OpenAI's.

On an Intel Core Ultra 7 255H with 16 threads it answered a short request in 54 ms and a long one
in 220 ms. The idea behind answering without generating is on
[why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md).

## Where they overlap: serving

Both put a model behind a local HTTP port, and both can run headless. The overlap ends at what the
port returns.

| | LM Studio server | jev serve |
|---|---|---|
| Returns | generated text, JSON, embeddings | P(yes) per question |
| API shape | OpenAI-compatible, Anthropic-compatible | TypeSafe Jev's wire format |
| Models | any downloaded model, loaded on demand | one GGUF file per process |
| Interface | desktop app, CLI, daemon | command line only |
| Engines | llama.cpp, MLX on Apple Silicon | llama.cpp prebuilt binaries, CPU |
| Auth | bearer token | `JEV_API_KEY`, bearer token |

If you wanted yes/no decisions from LM Studio, you would load a general model, prompt it to
answer yes or no, and parse or schema-constrain the generated answer. That works, and it is the
route [structured output vs a probability](structured-output-vs-a-probability.md) compares with
reading a probability directly.

## Running them side by side

A reasonable developer setup: LM Studio on port 1234 with a general model for drafting, chatting
and experiments, and `jev serve` on 8017 for the decisions your code makes. An application can
call both, generation from one and a yes/no check before acting from the other, as on
[gating AI agent tool calls](gating-ai-agent-tool-calls.md).

Two practical notes. They share the CPU and memory, so set jevos' `--threads` to fewer than your
core count while a model is busy in LM Studio, as the jev README advises for other heavy apps.
And do not measure latency on one while the other is generating; you will measure the contention.

## Which to reach for, by task

- **Exploring which model suits a task, reading its answers, iterating on prompts by hand:**
  LM Studio. It is built for a person in the loop.
- **Summaries, drafts, extraction into free-form fields, other languages:** LM Studio with a
  suitable model. jevos generates no text and reads English only.
- **A decision in a request path, where your code thresholds a number:** jevos.
- **A decision service that must log exactly which model file answered:** jevos, whose `/health`
  reports the file's sha256 and the llama.cpp release.
- **Arithmetic or date logic inside the decision:** neither model should do it; compute in code.
  jevos scored 0.584 on arithmetic questions in our 999-question test.

## Short answers to the questions that lead here

**Is jevos like LM Studio?** No. LM Studio is an app to run and chat with many models; jevos is a
single-purpose yes/no decision server with no interface.

**Can LM Studio answer yes/no questions?** Yes, with a general model prompted to answer yes or no,
optionally with a JSON schema for the answer.

**Can I run jevos inside LM Studio?** We have not tested loading the jevos file in LM Studio, and
the jev server's endpoint and answers would not be available there.

**Can LM Studio run without the GUI?** Its docs describe `llmster`, a headless daemon started
with `lms daemon up`.

**Do they conflict on one machine?** Not on ports (1234 and 8017). They do share the CPU, so
adjust threads.

**See also:** [jevos vs Ollama](jevos-vs-ollama-for-yes-no-decisions.md),
[self-hosted AI for decisions](self-hosted-ai-for-decisions.md) and
[an LLM on a laptop](an-llm-on-a-laptop.md).

## Sources

- LM Studio features, platforms, engines and offline use: [LM Studio docs](https://lmstudio.ai/docs/app),
  fetched 2026-09-29; the llama.cpp and MLX runtime is also stated on [lmstudio.ai](https://lmstudio.ai),
  fetched 2026-09-29.
- Developer endpoints, SDKs, structured output, auth and port: [developer docs](https://lmstudio.ai/docs/developer)
  and [OpenAI compatibility](https://lmstudio.ai/docs/developer/openai-compat), fetched 2026-09-29.
- `llmster`, `lms daemon up`, run on login and just-in-time loading:
  [headless mode](https://lmstudio.ai/docs/developer/core/headless), fetched 2026-09-29.
- jevos server, endpoints, memory, latency and accuracy by kind: the
  [jev README](https://github.com/feder-cr/jev) and our own measurements.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a server with no window, meant to be
called by code rather than talked to.*
