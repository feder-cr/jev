---
title: "Local vs hosted LLM decisions: latency, cost, privacy"
description: "The trade-off between a local and a hosted model for yes/no decisions, with one measured example (28/130 ms vs 311/314 ms) and what shifts with scale."
parent: "Comparisons"
nav_order: 11
---

# Local vs hosted LLM decisions: latency, cost, privacy

**A local model wins on latency for short decisions, costs nothing per call and keeps the text on
your machine; a hosted model wins on accuracy for hard questions, on languages, and on not having
to run anything.** In our one measured example, from a laptop in Europe, jevos answered a short
request in 28 ms and a long one in 130 ms, while TypeSafe's hosted Jev took 311 and 314 ms with
the network included. On admission-policy yes/no rules, the hosted model was right 1.00 of the
time against 0.95 locally. Which of those rows matters most is the decision.

Conflict of interest, in one line: we build jevos, the local side of the one measurement on this
page.

The non-obvious part is that the two latency curves have different shapes. Local time grows with
the length of the text; hosted time is dominated by a fixed round trip and barely moves. So "local
is faster" is true for short inputs and can stop being true for long ones, and where the lines
cross depends on your region, your text and your hardware.

This page is the measurement, then latency, cost, privacy and accuracy one at a time, then what
changes with scale and region.

## The one measurement

| | short request | long request |
|---|---|---|
| jevos, local (Intel Core Ultra 7 255H, 16 threads, CPU) | 28 ms | 130 ms |
| TypeSafe Jev, hosted API from Europe, network included | 311 ms | 314 ms |

Same two requests, same laptop, median of 10 requests after 3 warm-up requests (measured with
jevos-v3, which has the same size and speed as jevos-v4). The hosted numbers include everything an application
would see: connection, request, the provider's processing and the response. It is one hosted
service from one place, not a statement about hosted APIs in general, and a server closer to the
provider would see less.

## Latency: a slope against a floor

The local time is almost all prompt processing, and no generation, since jevos produces no output
tokens. More text takes longer: 28 ms for a short request, 130 ms for a long one on that laptop,
unless the same text was read before (22 ms for the long one asked again). The mechanics are on [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).

The hosted time has a floor that has nothing to do with the model: DNS, TLS, the distance to the
data centre, queueing. OpenAI's latency guide makes the general point that "each time you make a
request, you incur some round-trip latency" and recommends fewer, combined requests. Above the
floor, a fast hosted model adds little per token, which is why Jev's two numbers are 3 ms apart.

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

On six tasks, with the same questions and HTTP client for all models, Jev was ahead of jevos-v4 on
every one: 1.00 vs 0.95 on admission policy (yes/no), 0.88 vs 0.76 on ShARC rules and scenarios,
0.91 vs 0.76 on rental policy (choice), 0.98 vs 0.81 on authority rules (choice), 0.69 vs 0.50 on
fraud points (score, several signals summed and compared with a cut-off, which is arithmetic) and
0.59 vs 0.37 on patent phrases (score, expert ratings). The gap is smallest on plain yes/no
rules and widest on the score and choice tasks. Five of the six sets helped choose the released
checkpoint, so jevos's scores there may be slightly optimistic.

If a wrong decision is expensive and the questions involve rules and numbers, the hosted model's
extra accuracy may be worth all its latency and cost. If the questions are reading questions, the
local one may be enough. The way to know is a labelled sample of your own cases.

## What changes with scale, region and requirements

- **Volume.** Cost favours local as volume grows; the break-even depends on your prices and
  hardware. Capacity is a separate question from the latency above, which was measured one request
  at a time; see [throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).
- **Region.** A client near the provider sees a lower floor. A client far away sees a higher one.
- **Text length.** Short texts favour local; very long ones narrow or reverse the gap.
- **Languages and question types.** jevos is English, and answers yes/no, `choice` and `score`
  questions; its `score` answers are early (58.5% of 2,350 held-out score questions right, 86%
  within one level).
- **Both at once.** With the same wire format, you can answer confident cases locally and send the
  uncertain band to the hosted model, as on
  [a model cascade: small model first](model-cascade-small-model-first.md).

## Short answers to the questions that lead here

**Is a local LLM faster than an API?** For short decisions in our measurement, yes: 28 ms against
311 ms. For long texts the gap narrows, because local time grows with length and hosted time
barely does.

**Is a local LLM cheaper?** No per-call price, but you pay for and run the machine. At high volume
it usually is; at low volume the API often is.

**Is a local LLM more private?** The text stays on your machine. Access control and logs remain
your job.

**Is hosted more accurate?** In our test, yes: on all six tasks, for example 1.00 against 0.95 on
admission policy and 0.88 against 0.76 on ShARC rules.

**Can I use both?** Yes. Decide locally when confident and escalate the rest.

**See also:** [why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md),
[jevos vs the OpenAI API for yes/no classification](jevos-vs-openai-api-for-classification.md) and
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- Latency (28/130 ms, 311/314 ms), the three-question timing, memory and the six-task accuracy
  table: our own measurements, published in the
  [jev README](https://github.com/feder-cr/jev).
- Round-trip latency advice: OpenAI, [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization),
  fetched 2026-09-29.
- Per-million-token pricing: OpenAI, [API pricing](https://developers.openai.com/api/docs/pricing),
  fetched 2026-09-29.
- Data use, retention and residency: OpenAI, [Data controls](https://developers.openai.com/api/docs/guides/your-data),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), measured from one laptop in Europe,
which is exactly as general as that sounds.*
