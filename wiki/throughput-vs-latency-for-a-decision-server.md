---
title: "Throughput vs latency for a decision server"
description: "Latency is how long one decision takes; throughput is how many a server completes per second. Why one laptop number is latency, not capacity."
parent: "Speed"
nav_order: 12
---

# Throughput vs latency for a decision server

**Latency is how long one decision takes; throughput is how many decisions a server completes
per second, and one does not tell you the other.** Our published jevos figures, 26 ms for a
short request and 112 ms for a long one on a laptop CPU, are latency: one request at a time, on
an idle machine. They say nothing about what happens when a hundred requests arrive together,
which depends on how the server schedules work, how long the queue gets, and how many copies of
it you run.

The link between the two is waiting. When requests arrive faster than they are served, latency
stops being the model's time and becomes the model's time plus the queue. A server can have
excellent latency at low load and poor latency at peak without anything about the model
changing.

This page is the two definitions, the one law that connects them, how jev serve handles
concurrent requests, the kinds of batching, and how to measure capacity for your own traffic.
The one concurrency measurement of jevos here is from one laptop: a starting point for yours,
not a capacity figure.

## Two numbers, two questions

| | Latency | Throughput |
|---|---|---|
| Question it answers | How long does my request wait? | How much traffic can this handle? |
| Unit | milliseconds per request | requests (or decisions) per second |
| Measured with | one request at a time, repeated | many concurrent requests, sustained |
| Who needs it | the user or caller waiting | whoever sizes the servers |

NVIDIA's benchmarking documentation defines requests per second as completed requests divided
by the duration of the test, measured across all simultaneous requests. That is a property of
the whole system under load, not of a single request.

## Little's law connects them

Little's law says that in a stable system the average number of items inside equals the
arrival rate times the average time each spends inside: L = lambda x W. It holds whatever the
arrival pattern or service order.

An illustrative example, with made-up traffic, to show how it works: if decisions arrive at 20
per second and each spends 0.25 s in the system, then on average 5 are in the system at any
moment. If the server can only work on one at a time and each takes 0.2 s, it can finish at most
5 per second, and 20 arriving per second means the queue grows without limit. Latency in that
situation is not 0.2 s; it is however long the queue has become.

The practical reading: a latency figure is only meaningful up to the load where the queue stays
short. Past that, more traffic means more waiting, not more throughput.

## How jev serve handles concurrent requests

jev serve reads small requests that arrive at the same time together, in one model call, up to
`--batch-tokens` (384 tokens by default). Past that, requests wait for the model. The time a
request waits is inside the `total` duration of the `Server-Timing` header, while `inference`
is only the model's work. So under load, a growing gap between `total` and `inference` is the
queue, visible per response.

We measured it with one-question requests from our 999-question set, on the reference laptop
(Intel Core Ultra 7 255H, 16 threads):

| Concurrent clients | Requests per second | Median latency |
|---|---|---|
| 1 | 8.7 | 110 ms |
| 4 | 9.8 | 390 ms |
| 8 | 10.1 | 780 ms |

Throughput barely moves past one client while latency grows with the queue, which is Little's
law on a server that is already busy. That is one laptop and one kind of request: real traffic
mixes sizes, and your CPU is not ours.

To go beyond one process's ceiling, the options are the usual ones: more processes on a machine
with cores to spare, more machines behind a load balancer, or a different serving stack. We measured
about 1 GB of extra memory with the model loaded in one process; until you have checked how
several processes share memory on your system, plan that much for each.

## Three kinds of batching

**Questions in one request.** Several questions about the same text share its reading. Three
questions took about 66 ms together against 49 ms for one alone. This is the batching you
control from the client, and it raises decisions per second without any server change; see
[many questions about one text](many-questions-about-one-text.md).

**Requests batched on the server.** General serving systems process many users' requests
together. The vLLM paper opens with "high throughput serving of large language models (LLMs)
requires batching sufficiently many requests at a time", and the llama.cpp server lists
"continuous batching" and parallel slots among its features. This raises throughput, usually at
some cost to each request's latency, and it is where GPUs shine; see
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md). jev serve does a small form of
this: small requests that arrive at the same time are read together in one model call.

**Batching over files.** For offline work, the unit is a file of requests and the measure is how
long the job takes. `jev decide` answers request files without a server; the workflow is on
[batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).

## How to measure capacity for your traffic

1. **Get the single-request baseline first**: median and p90 of your real requests, one at a
   time, as on [measuring LLM latency](measuring-llm-latency-median-and-p90.md).
2. **Add load in steps.** Send requests from several concurrent clients, starting at a rate well
   below the ceiling and raising it.
3. **Watch p90 and the queue**, not just the average. Record the `total` minus `inference` gap
   from `Server-Timing` on every response.
4. **Stop at the knee.** Capacity is the highest rate at which the p90 still fits your budget,
   not the rate at which the server stops failing.
5. **Leave headroom.** Traffic has peaks; size for them, not for the daily average.

Run the load generator on a different machine from the server if you can. A load generator on
the same CPU competes with the model and lowers both numbers.

## Which one should you optimise?

For a user waiting on a form, or an agent waiting before its next step, latency. For a nightly
job over a million records, throughput. For a webhook that fans out to many decisions, both: the
p90 has to fit the sender's deadline at the peak rate. The budgets for each case are on
[latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md).

## Short answers to the questions that lead here

**What is the difference between throughput and latency?** Latency is the time for one request;
throughput is how many requests a system completes per second under load.

**Does low latency mean high throughput?** Not by itself. It sets a ceiling when requests are
served one at a time; batching and more copies raise throughput beyond it.

**How many requests per second can jevos handle?** On our laptop, one process answered about 9
to 10 one-question requests per second, with the median latency growing from 110 ms at one
client to 780 ms at eight. Measure with your traffic.

**Does jev serve process requests in parallel?** Partly. Small requests that arrive together are
read in one model call; the others wait, and the wait is included in the `total` duration of
`Server-Timing`.

**How do I increase throughput?** Group questions per text, trim inputs, and run more processes
or machines once one is saturated.

**See also:** [the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md),
[prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md) and
[self-hosted AI for decisions](self-hosted-ai-for-decisions.md).

## Sources

- Single-request latencies, the three-question timing, the concurrent-client measurement,
  memory, and the `Server-Timing` header: our measurements and the
  [jev README](https://github.com/feder-cr/jev). Requests read together and queue time counted
  in `total`: the jev source.
- Little's law: [Little's law, Wikipedia](https://en.wikipedia.org/wiki/Little%27s_law), fetched
  2026-09-29.
- Requests per second definition:
  [NVIDIA NIM benchmarking metrics](https://docs.nvidia.com/nim/benchmarking/llm/latest/metrics.html),
  fetched 2026-09-29.
- Batching for throughput: Kwon et al., [PagedAttention](https://arxiv.org/abs/2309.06180), and
  the [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md),
  both fetched 2026-09-29.
- The traffic in the Little's law example is illustrative arithmetic, not a measurement.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose server says in its timing
header how long each request waited, which is where capacity planning should start.*
