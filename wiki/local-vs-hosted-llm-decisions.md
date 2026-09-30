---
title: "Local vs hosted LLM decisions: latency, cost, privacy"
description: "The trade-off between a local and a hosted model for yes/no decisions, with one measured example (26/112 ms vs 344/345 ms) and what shifts with scale."
parent: "Comparisons"
nav_order: 11
---

# Local vs hosted LLM decisions: latency, cost, privacy

**A local model wins on latency for short decisions, costs nothing per call and keeps the text on
your machine; a hosted model wins on accuracy for hard questions, on languages, and on not having
to run anything.** In our one measured example, from a laptop in Europe, jevos answered a short
request in 26 ms and a long one in 112 ms, while TypeSafe's hosted Jev took 344 and 345 ms with
the network included. On 2,000 rule questions, the hosted model was right 0.927 of the time
against 0.810 locally. Which of those rows matters most is the decision.

Conflict of interest, in one line: we build jevos, the local side of the one measurement on this
page.

The non-obvious part is that the two latency curves have different shapes. Local time grows with
the length of the text; hosted time is dominated by a fixed round trip and barely moves. So "local
is faster" is true for short inputs and can stop being true for long ones, and where the lines
cross depends on your region, your text and your hardware.

This page is the measurement, then latency, cost, privacy and accuracy one at a time, then what
changes with scale and region.

## The one measurement

| | short request (about 30 tokens) | long request (about 190 tokens) |
|---|---|---|
| jevos, local (Intel Core Ultra 7 255H, 16 threads, CPU) | 26 ms | 112 ms |
| TypeSafe Jev, hosted API from Europe, network included | 344 ms | 345 ms |

Same two requests, same laptop. The hosted numbers include everything an application
would see: connection, request, the provider's processing and the response. It is one hosted
service from one place, not a statement about hosted APIs in general, and a server closer to the
provider would see less.

## Latency: a slope against a floor

The local time is almost all prompt processing, and no generation, since jevos produces no output
tokens. More text takes longer: 26 ms for about 30 tokens, 112 ms for about 190 on that laptop,
unless the same text was read before (22 ms for the long one asked again). The mechanics are on [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).

The hosted time has a floor that has nothing to do with the model: DNS, TLS, the distance to the
data centre, queueing. OpenAI's latency guide makes the general point that "each time you make a
request, you incur some round-trip latency" and recommends fewer, combined requests. Above the
floor, a fast hosted model adds little per token, which is why Jev's two numbers are 1 ms apart.

Two consequences follow. For short, interactive decisions, such as a chat message, a form field
or a game loop, the local slope stays well under the hosted floor. For long documents the local
time keeps growing and the hosted floor does not, so past some length, which we have not
measured, the hosted call can be the faster one if your network is good.

## Cost: per token or per machine

A hosted API bills per token, with input and output priced separately; OpenAI's pricing page, for
example, lists rates per million tokens. A yes/no call pays for the text and the instructions every
time. The bill scales linearly with volume, and there is nothing to operate.

A local model has no per-call price. You pay for a machine with a CPU and about 1 GB of free
memory for the loaded model, and for the time to operate it. At low volume that is more expensive
than the API; at high volume on short decisions it tends to be much cheaper. Grouping questions
helps both sides: jevos reads the text once for every question in a request, so three questions
took about 66 ms against 49 ms for one.

## Privacy: what local solves and what it does not

Local means the text is not sent to a third party. The jev server listens on 127.0.0.1 by default,
and with `JEV_API_KEY` set every call except `/health` needs a bearer token. For customer
messages, health data or contracts, removing a processor from the chain can remove a lot of
paperwork.

Hosted can be acceptable too. OpenAI's data controls page, as one example, states that API data is
not used for training unless you opt in, that abuse monitoring logs are kept for up to 30 days, and
that zero data retention and regional storage are available with approval. Read your provider's
terms, not a summary.

What local does not solve: who can reach the server, what your own logs keep, and how long. See
[a private LLM for text classification](private-llm-for-text-classification.md).

## Accuracy: often the deciding row

On 2,000 yes/no questions about three business policies none of the models had been tuned on, Jev
was right 0.927 of the time and jevos 0.810. The gap was largest on additive point scores, several
signals summed and compared with a cut-off, which is arithmetic. On reading questions the local
model is much stronger than on computation: 0.954 on stated facts against 0.584 on arithmetic in
our 999-question test.

If a wrong decision is expensive and the questions involve rules and numbers, the hosted model's
extra accuracy may be worth all its latency and cost. If the questions are reading questions, the
local one may be enough. The way to know is a labelled sample of your own cases.

## What changes with scale, region and requirements

- **Volume.** Cost favours local as volume grows; the break-even depends on your prices and
  hardware. Capacity is a separate question from the latency above, which was measured one request
  at a time; see [throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).
- **Region.** A client near the provider sees a lower floor. A client far away sees a higher one.
- **Text length.** Short texts favour local; very long ones narrow or reverse the gap.
- **Languages and question types.** jevos is English, and answers yes/no and `choice`
  questions; `score` questions are refused with a `422`.
- **Both at once.** With the same wire format, you can answer confident cases locally and send the
  uncertain band to the hosted model, as on
  [a model cascade: small model first](model-cascade-small-model-first.md).

## Short answers to the questions that lead here

**Is a local LLM faster than an API?** For short decisions in our measurement, yes: 26 ms against
344 ms. For long texts the gap narrows, because local time grows with length and hosted time
barely does.

**Is a local LLM cheaper?** No per-call price, but you pay for and run the machine. At high volume
it usually is; at low volume the API often is.

**Is a local LLM more private?** The text stays on your machine. Access control and logs remain
your job.

**Is hosted more accurate?** In our test, yes: 0.927 against 0.810 on unseen rules.

**Can I use both?** Yes. Decide locally when confident and escalate the rest.

**See also:** [why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md),
[jevos vs the OpenAI API for yes/no classification](jevos-vs-openai-api-for-classification.md) and
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- Latency (26/112 ms, 344/345 ms), the three-question timing, memory and the
  2,000-question accuracy: our own measurements, published in the
  [jev README](https://github.com/feder-cr/jev).
- Accuracy by kind: our 999-question test set on `jevos-q4_k_m`.
- Round-trip latency advice: OpenAI, [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization),
  fetched 2026-09-29.
- Per-million-token pricing: OpenAI, [API pricing](https://developers.openai.com/api/docs/pricing),
  fetched 2026-09-29.
- Data use, retention and residency: OpenAI, [Data controls](https://developers.openai.com/api/docs/guides/your-data),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), measured from one laptop in Europe,
which is exactly as general as that sounds.*
