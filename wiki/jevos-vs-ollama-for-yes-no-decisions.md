---
title: "jevos vs Ollama for yes/no decisions"
description: "Ollama runs general local models that generate text; jevos returns one probability per yes/no question. When each fits, and how to run both."
parent: "Comparisons"
nav_order: 4
---

# jevos vs Ollama for yes/no decisions

**Ollama is a general way to run many open models locally and have them generate text; jevos is
one small model behind one endpoint that answers yes/no questions with a probability and
generates nothing.** Both keep the text on your machine. If you want to
chat, summarise, extract fields or switch between models, Ollama is the tool. If your
application asks the same kind of yes/no question thousands of times and wants a number to
threshold, jevos does that one job with less to parse.

Conflict of interest, in one line: we build jevos; the Ollama facts below come from its GitHub
repository and documentation, fetched 2026-09-29.

They are not really competitors. Many setups that use Ollama for generation would still benefit
from a separate decision endpoint for the small checks around it, and the two can run on the same
machine on different ports.

This page is what each one returns, how you would get a yes/no out of Ollama, where the time
goes, what model management each offers, and a way to run both.

## What each one returns

Ollama's API has `/api/generate` and `/api/chat` on port 11434. You send a model name and a
prompt or a list of messages, and the response carries the generated text in `response` (or in
the message), with timings and token counts: `prompt_eval_count`, `eval_count`,
`prompt_eval_duration` ("time spent evaluating uncached prompt tokens") and `eval_duration`
("time spent generating tokens").

jevos has `POST /v1/systemone` on port 8017. You send a `state` and named questions, and each
question comes back as its own `noul`, the probability that the answer is yes, with
`output_tokens` at 0. It speaks TypeSafe Jev's wire format, not Ollama's or OpenAI's.

| | Ollama | jevos |
|---|---|---|
| Job | run and serve many models | answer yes/no questions |
| Output | generated text (or JSON) | P(yes) per question |
| Models | a library, pulled by name | one model per server |
| Default port | 11434 | 8017 |
| Engine | llama.cpp as its supported backend | OpenVINO, INT8 weights, CPU |
| Platforms | macOS, Windows, Linux, Docker | Windows x64, Linux x64, macOS on Apple silicon |
| License | MIT | MIT (code) |

## Getting a yes/no out of Ollama

Ollama gives you three tools for it, all documented on its API page:

- **`format`**: "json" or a JSON schema object, for structured output. A schema with one boolean
  field makes the answer machine readable.
- **`num_predict`** in `options`: the maximum number of tokens to generate. Keeping it small
  keeps a one-word answer short.
- **`logprobs` and `top_logprobs`**: log probabilities of the output tokens and the most likely
  alternatives at each position.

With those, a general chat model can approximate a decision endpoint: ask the question, force a
short or schema-shaped answer, and read the probability of the answer token. What is left to you
is the prompt that makes a general model answer consistently, finding the yes and no tokens
among the alternatives, and deciding what a malformed answer means. The case for skipping that
layer is on [why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md).

## Where the time goes

Ollama's own timing fields split a request into prompt evaluation and generation, and that
split is the useful way to think about both tools. Reading the prompt costs time proportional to
its length; each generated token costs a further step. A yes/no answer from a chat model pays
the first and at least one of the second, plus whatever the chat template adds to the prompt.

jevos pays only for reading. On an Intel Core Ultra 7 255H with 16 threads it took 26 ms on a
request of about 30 tokens and 112 ms on one of about 190, each read from scratch. We
have not measured Ollama on the same requests, so there is no head-to-head number here, and any
comparison would depend on which model you load. [Prefill vs decode](prefill-vs-decode-llm-latency.md)
explains the two costs in general.

## Models and management

This is where Ollama is the more complete product. Models are pulled from a library by name
(`ollama run gemma4` in its README), you can switch between them per request, and `keep_alive`
controls how long a model stays in memory after use, 5 minutes by default. SDKs for Python and
JavaScript and many integrations exist around it.

jevos has none of that, on purpose. A server loads one model, keeps it resident and answers
only with it. `GET /health` reports the served model, so a decision in a log can be tied to it.
Updating means replacing the `model` folder beside the binary, which suits a service more than a
workstation.

## When each one fits

**Ollama** when you need generation, many models, other languages through a multilingual model,
or a single local runtime for a team's experiments. Also when the question genuinely needs a
larger model's reasoning, which a 1B decision model will not replace.

**jevos** when the task is a stream of English yes/no questions about texts, you want a
probability for thresholds and review bands, and you want nothing to parse. Its measured
strengths are reading questions: 0.954 on facts stated in the text and 0.938 on tone in our
999-question test. Its weakness is computation, 0.584 on arithmetic, which you should do in code
whichever tool you use.

## Running both on one machine

Nothing stops you from running Ollama on 11434 for generation and `jev serve` on 8017 for
decisions: an agent built on an Ollama model can call jevos before each tool call with "is this
action what the user asked for?", as on [gating AI agent tool calls](gating-ai-agent-tool-calls.md).
Two caveats. Both use the same CPU and memory, so set jevos' `--threads` below your core count if
the other is busy, as the README advises. And never benchmark one while the other is working:
the numbers will measure the contention, not the tools. The desktop counterpart of Ollama is
compared on [jevos vs LM Studio](jevos-vs-lm-studio.md).

## Short answers to the questions that lead here

**Is jevos an Ollama model?** No. It is a separate server with its own endpoint and wire format;
it runs jevos-v2 with 8-bit weights through OpenVINO. The release also ships the model as GGUF
files, which Ollama can load, without jev's endpoint.

**Can Ollama answer yes/no questions?** Yes, with a general model, a prompt that asks for yes or
no, and optionally `format`, `num_predict` and `logprobs` to constrain and score the answer.

**Which is faster for a yes/no decision?** We have not measured Ollama on our requests. jevos
generates no tokens and took 26 to 112 ms on our laptop; a chat model pays for at least one
generated token on top of reading the prompt.

**Can I use both?** Yes: on different ports, with thread counts set so they do not fight for the
CPU.

**Which one supports more languages?** Ollama, through whichever multilingual model you load.
jevos reads English only.

**See also:** [llama.cpp vs Ollama for a classification service](llama-cpp-vs-ollama-for-classification.md),
[run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md) and
[ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Sources

- jevos latency (26 and 112 ms) and accuracy by kind: our own
  measurements, see the [jev README](https://github.com/feder-cr/jev).
- Ollama's platforms, port, llama.cpp backend, license and `ollama run` example: the
  [Ollama repository](https://github.com/ollama/ollama), fetched 2026-09-29.
- `/api/generate` and `/api/chat` parameters (`format`, `options`, `num_predict`, `keep_alive`)
  and response fields: [Ollama API docs on GitHub](https://github.com/ollama/ollama/blob/main/docs/api.md)
  and [docs.ollama.com/api/generate](https://docs.ollama.com/api/generate), including `logprobs`,
  `top_logprobs` and the duration fields, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a one-endpoint server that is happy to
share a machine with a general one.*
