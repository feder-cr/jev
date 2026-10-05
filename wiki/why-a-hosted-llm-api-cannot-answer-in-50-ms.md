---
title: "Why a hosted LLM API cannot answer in 50 ms"
description: "Network round trips, TCP and TLS setup and queueing cost time before a hosted model starts. Why our hosted timing was flat at 311 and 314 ms."
parent: "Speed"
nav_order: 6
---

# Why a hosted LLM API cannot answer in 50 ms

**A hosted LLM API usually cannot answer in 50 ms because the request has to cross the network
and back before the answer exists, and on a fresh connection it crosses more than once.**
Light in fibre covers about 200 km per millisecond, a new HTTPS connection needs round trips for
TCP and TLS before the request is even sent, and the provider may queue the request behind
others. From our laptop in Europe, the hosted Jev API took 311 ms on a short request and 314 ms
on a long one, while the same requests ran locally in 28 and 130 ms.

The flatness is the tell. When a request with six times more text takes the same time, the
model is not what you are waiting for. That also means a hosted API can be the right choice for
long texts or hard questions, where its fixed cost is spread over more work.

This page is the ledger of where the time goes, the physics nobody can optimise away, how to
read our two numbers, what you can shave off, and when hosted is still the better option.

## Where the time goes before the model runs

A call to a hosted API over HTTPS, from a client that has not talked to the server recently:

| Step | Cost | Can it be avoided? |
|---|---|---|
| DNS lookup | a round trip to a resolver, often cached | usually cached after the first call |
| TCP connection | one round trip (the three-way handshake) | reuse the connection |
| TLS 1.3 handshake | one more round trip for a full handshake | reuse the connection; 0-RTT resumption with caveats |
| Request and response | one round trip plus transfer time | no |
| Queueing at the provider | anything from nothing to seconds | not from your side |
| The model itself | prefill, plus decode if it writes | smaller model, shorter input |

RFC 9293 calls TCP's setup the "three-way (or three message) handshake". RFC 8446, which
defines TLS 1.3, describes a full handshake completed in one round trip and adds a zero
round-trip mode for resumed sessions, noting that its "security properties ... are weaker". So
a cold HTTPS request costs about three round trips before the first byte of the answer, and a
warm one on a reused connection costs one.

## The physics nobody can optimise away

Signals in optical fibre travel at around 200,000 km per second, as the Wikipedia article on
optical fibre puts it, about two thirds of the speed of light in a vacuum. That is 200 km per
millisecond, one way. Its own example: a 16,000 km fibre path between Sydney and New York means
a minimum delay of 80 ms.

For a 50 ms budget, that gives a hard ceiling on distance. A single round trip to a data centre
5,000 km away uses 50 ms in fibre alone, before routers, before TLS, before the model; real
cable routes are not straight lines, so the practical distance is shorter. Nearby regions fit;
an ocean away does not.

## Reading 311 and 314

| Same two requests | short (about 30 tokens) | long (about 190 tokens) |
|---|---|---|
| jevos on the laptop, text read from scratch | 28 ms | 130 ms |
| Jev, hosted, from Europe, network included | 311 ms | 314 ms |

Locally, going from 30 to 190 tokens more than quadrupled the time, because the model reads every
token. Hosted, it added three milliseconds. The length-dependent part of the hosted call was lost in the
fixed part: connection, round trips, and whatever happens before the provider's model starts.

What the numbers do not tell you is how that fixed part splits. We do not know where
TypeSafe's servers are, and we measured from one location; from a client closer to them the
floor would likely be lower. This is what one application in Europe sees, not a property of
the service.

## What you can shave off

- **Reuse connections.** HTTP/1.1 "defaults to the use of persistent connections", per RFC 9112.
  A client that opens a new connection per call pays the TCP and TLS round trips every time;
  a pooled session pays them once. Check that your HTTP client keeps connections open between
  calls.
- **Call from the right region.** Put the code that calls the API close to the API. The cheapest
  round trip is a short one.
- **Batch questions.** Several questions about one text in one request pay the network once.
  With a Jev-compatible API, that is the same `questions` object with more entries.
- **Move the decisions that need speed off the network.** A local model has no round trip at
  all. The general trade-off is on
  [local vs hosted LLM decisions: latency, cost, privacy](local-vs-hosted-llm-decisions.md).

What you cannot shave is the distance and the provider's queue. If your budget is 50 ms and the
nearest region is far, no client-side change fits it.

## When hosted is still the right call

- **Accuracy matters more than milliseconds.** On our six tasks the hosted Jev was ahead each time,
  for example 1.00 against 0.95 for jevos on admission rules. The comparison is on
  [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).
- **The texts are long.** Local latency grows with every token read on our laptop; a hosted
  model's fixed cost matters less the more work each request carries.
- **You need score answers past jevos's early ones**, or languages other than English.
- **The latency budget is seconds, not milliseconds.** A nightly job or a webhook with a
  three-second timeout has room for a round trip; see
  [latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md).

Because jevos speaks Jev's wire format, the two can split the work: answer locally when the
probability is confident, and send the uncertain middle to the hosted model with a change of
URL. The pattern is on
[a model cascade: small model first, large model on doubt](model-cascade-small-model-first.md).

## Short answers to the questions that lead here

**Why is my LLM API call slow even for a one-word answer?** Much of the time is network and
setup, not the model. On our measurement from Europe, a 30-token and a 190-token request took
about the same 311 to 314 ms.

**Can any hosted API answer in 50 ms?** Only from close by, on a reused connection, with little
queueing and a fast model. The distance alone rules it out from far away.

**Does streaming fix it?** Streaming shows the first token sooner, but the first token still
waits for the round trip and the prompt. For a yes/no decision you need the whole answer anyway.

**How do I measure the network part?** Compare wall-clock time on your side with any timing the
server reports; for a local jev server, the `Server-Timing` header gives the server's own
durations. See [measuring LLM latency](measuring-llm-latency-median-and-p90.md).

**Is a local model always faster?** No. It was on our two requests. On long documents, from a
server near the provider, measure both.

**See also:** [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md),
[the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md) and
[jevos vs the OpenAI API for yes/no classification](jevos-vs-openai-api-for-classification.md).

## Sources

- Local and hosted latencies and the six-task accuracy comparison: our own measurements,
  published in the [jev README](https://github.com/feder-cr/jev).
- TCP handshake: [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293), fetched 2026-09-29.
- TLS 1.3 handshake and 0-RTT: [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446), fetched
  2026-09-29.
- Persistent connections: [RFC 9112, section 9.3](https://www.rfc-editor.org/rfc/rfc9112#name-persistence),
  fetched 2026-09-29.
- Signal speed in fibre and the Sydney to New York example:
  [Optical fiber, Wikipedia](https://en.wikipedia.org/wiki/Optical_fiber), fetched 2026-09-29.
- Slack's three-second response requirement:
  [Slack Events API](https://docs.slack.dev/apis/events-api/), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), written on a laptop in Europe, which
is where the 311 ms came from and the only place we can vouch for it.*
