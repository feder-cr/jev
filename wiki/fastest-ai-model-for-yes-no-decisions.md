---
title: "The fastest AI model for yes/no decisions"
description: "What the fastest AI or fastest LLM can honestly mean, which speed metric matters for a yes/no decision, and what we measured on a laptop CPU."
parent: "Speed"
nav_order: 1
---

# The fastest AI model for yes/no decisions

**There is no single fastest AI model: "fastest" only means something once you name the task,
the metric, the hardware and the request.** For a yes/no decision the metric that matters is
the time from sending the question to having the answer, and a model that returns a probability
instead of writing text has an advantage there, because it never has to generate a token. On
our reference laptop, jevos answered a short request in 28 ms and a long one in 130 ms, the
fastest of the four systems we measured on those two requests.

The non-obvious point is that most "fastest LLM" rankings measure something else: how many
tokens per second a model writes once it has started. That number is useful for chat and
irrelevant for a decision whose answer is one bit. A model can top a tokens-per-second chart
and still be slower than a small local model at telling you whether a ticket is about billing.

A conflict of interest, stated first: we build jevos. This page is what people mean by fast,
which of those meanings fits a decision, what we measured and how, why generating nothing wins
this particular race, and when something else will be faster for you.

## Is there a fastest LLM in the world?

Not in any sense that can be measured once and stated for good. Speed depends on the hardware,
the size of the input, the length of the output, how many other requests share the machine,
and, for a hosted model, how far you are from the data centre. Change any of these and the
ranking changes.

A claim to be the fastest anywhere would need every model, on every relevant piece of hardware,
on your requests. Nobody has that measurement. What can be said honestly is narrower: fastest
of the systems measured, on named requests, on named hardware. That is the only kind of claim
on this page.

## Three things "fast" can mean

Benchmarking guides separate several metrics, and they answer different questions:

| Metric | What it measures | Who cares |
|---|---|---|
| Time to first token | Wait before any output appears; includes queueing, prompt processing and network | Chat, streaming |
| Output speed (tokens per second) | How fast text arrives once it has started | Long answers, code, essays |
| End-to-end latency | Request sent to complete answer received | Any program waiting on the result |
| Throughput | Requests or tokens completed per second across all users | Whoever pays for the servers |

NVIDIA's benchmarking documentation defines end-to-end latency as time to first token plus
generation time, and Artificial Analysis defines output speed as tokens received per second
after the first token. Both definitions are about generating text, because that is what most
models do.

The last row is its own subject: a server can have high throughput and poor latency at the
same time, which is covered on [throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).

## For a yes/no decision, only one number counts

A program that asks "should this refund be approved?" does nothing until the answer arrives. It
does not stream the answer to a reader, so time to first token and tokens per second are not
the point. End-to-end latency is.

For a chat model, end-to-end latency for "answer yes or no" is at least one full step of
generation after the prompt is processed, plus the network if it is hosted, plus the code that
parses the word back into a boolean. For a model that returns P(yes) directly, it is the
prompt processing and nothing else. The mechanics are on
[prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md).

## What we measured, and on what

Two requests, the same for every system, on one laptop: an Intel Core Ultra 7 255H with 16
threads and no GPU in use. Each figure is the median of 10 requests through the HTTP API after 3
warm-up requests, with each text read from scratch. They were measured with jevos-v3, which has
the same size and speed as jevos-v4.

| | short request | long request |
|---|---|---|
| jevos (jev, CPU, 8-bit weights, text read from scratch) | 28 ms | 130 ms |
| Laya | 129 ms | 480 ms |
| Jev, hosted API, network included | 311 ms | 314 ms |
| Qwen3.5-4B | 3,060 ms | 4,761 ms |

Being straight about the limits: two requests, one machine, one location. The hosted numbers
would be lower from a server closer to the provider, and the local numbers would change on a
different CPU. Accuracy is a separate question with a different winner: on all six tasks we
tested, Jev scored higher than jevos-v4, for example 1.00 against 0.95 on Admission policy
(yes/no rules) and 0.69 against 0.50 on Fraud points (sums). The full comparison, both
directions, is on [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

To reproduce numbers like these, see
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

## Why a model that writes nothing wins this race

Three costs disappear when the answer is a probability instead of a word.

- **No generation step.** Writing text is a loop, one token at a time, and each pass is paid
  after the prompt has been read. jevos stops after reading: `output_tokens` is always 0.
- **No parsing.** There is no "Yes.", "yes, because..." or "I cannot determine" to map back to
  a boolean, and no retry when the format is wrong.
- **No network, when it runs locally.** A round trip to a hosted API costs time before any
  model runs; on our measurement the hosted time barely moved between the short and the long
  request (311 and 314 ms), which is the signature of a fixed cost. Why that floor exists is on
  [why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md).

Size matters too; see [what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md)
and, against generating even one word,
[why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md).

## When something else is faster for you

- **Long documents.** Local latency grows with the text, from 28 ms for the short request to 130 ms
  for the long one on our laptop, while a hosted model's time was nearly flat. On long inputs the gap narrows and can
  reverse; see [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).
- **Many requests at once.** Capacity is a throughput question. A serving stack that batches
  many users' requests, usually on a GPU, is built for it; one laptop is not. We did not measure
  jev under concurrent load.
- **Hard reasoning.** If the small model gets the answer wrong, it was not fast, it was early.
  Arithmetic and multi-step rules are its weak spot, measured on
  [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).
- **Anything that is not English yes/no or multiple choice.** jevos reads English only, and its
  `score` answers are early: the most probable level was right on 58.5% of 2,350 held-out score
  questions and within one level on 86%, weak on points that add up (Fraud points 0.50 against 0.69 for Jev).

## Short answers to the questions that lead here

**What is the fastest AI model?** There is no answer without a task, a metric and hardware. For
yes/no decisions on a laptop CPU, jevos was the fastest of the four systems we measured on our
two requests.

**What is the fastest LLM for classification?** For single yes/no labels, one that returns a
probability without generating text, running close to the data. Measure end-to-end latency on
your own inputs.

**Are tokens per second a good measure for decisions?** No. They measure writing speed. A
decision has no text to write, so what matters is time to the complete answer.

**Is a local model always faster than an API?** No. On short inputs from our laptop it was, by
a wide margin. On long documents, or against an API in your own region, measure.

**Is the fastest model also the most accurate?** Not here. On all six of our tasks the hosted
Jev scored higher than jevos-v4.

**See also:** [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md),
[latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md) and
[ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Sources

- Latency and accuracy of jevos, Jev, Qwen3.5-4B and Laya, and the reference laptop: our own
  measurements, published in the [jev README](https://github.com/feder-cr/jev).
- Definitions of time to first token, end-to-end latency and throughput:
  [NVIDIA NIM benchmarking metrics](https://docs.nvidia.com/nim/benchmarking/llm/latest/metrics.html),
  fetched 2026-09-29.
- Definition of output speed:
  [Artificial Analysis performance methodology](https://artificialanalysis.ai/methodology/performance-benchmarking),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where every speed claim names its
two requests and its one laptop, because that is all a speed claim can honestly cover.*
