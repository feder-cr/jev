---
title: "Measuring LLM latency: median, p90 and warm-up"
description: "How to measure LLM latency honestly: warm up, take the median and p90 of many runs, compare Server-Timing with wall clock, and run one benchmark at a time."
parent: "Speed"
nav_order: 10
---

# Measuring LLM latency: median, p90 and warm-up

**To measure LLM latency honestly, warm the model up first, send the same realistic request many
times, and report the median and the p90 rather than the mean or a single run.** Record both
the server's own timing and the wall-clock time your client sees, because the difference is the
network and your client. And never benchmark two things on the same CPU at the same time: they
slow each other down and both numbers become fiction.

Most published latency figures fail one of these. A first request that includes loading the
model, an average pulled up by one stall, a number taken while a browser compiled a web page in
the background: each can move a result by more than the difference being claimed.

This page is a procedure to copy, why each step exists, a short script, what to report so
someone else can reproduce it, and the mistakes that make numbers worthless.

## The procedure

1. **Wait for ready.** Start the server and poll `GET /health` until it returns
   `{"status": "ready", ...}`. Loading is not latency.
2. **Warm up.** Send a handful of requests and throw the timings away.
3. **Use real requests.** Take requests of the size you will send in production, and state
   their token counts; every jev response reports `usage.input_tokens`.
4. **Repeat.** Send each request dozens of times, one after another.
5. **Report median and p90**, per request size, with both server and wall-clock time.
6. **Keep the machine quiet.** One benchmark at a time, no other heavy work.

## Why warm up?

The first requests after a start pay for things later requests do not: memory being touched for
the first time and caches filling, among others. None of that is what a user
waits for in steady state. `/health` tells you the model is loaded; the warm-up takes care of
the rest.

The opposite mistake is also common: a benchmark that only ever sends one identical request can
look faster than real traffic if anything is reused between calls. Vary the inputs across a
realistic set, or at least say that you did not.

## Why median and p90, not the mean?

Latency distributions have a long right tail: most requests are close to typical, a few are much
slower. The mean mixes both and describes neither. The median says what a typical request costs;
the p90 says what one request in ten is worse than.

The tail is what users notice and what timeouts hit. Dean and Barroso's "The Tail at Scale"
(Communications of the ACM, 2013) is the classic argument that rare slow responses dominate the
experience of large services, and that systems should be designed to tolerate them. For a budget,
set it against the p90 or higher, as argued on
[latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md).

## Server-Timing vs wall clock

The W3C Server-Timing specification, a Working Draft dated 2026-04-07, lets a server "communicate
performance metrics about the request-response cycle" in a response header, as named metrics
with an optional `dur`. Every jev response carries one, with an `inference` and a `total`
duration.

Measure both, and read them together:

| Measurement | What it includes |
|---|---|
| `Server-Timing` inference | the model's work on the request |
| `Server-Timing` total | the server's handling of the request, inference included |
| wall clock in your client | all of the above plus connection, transfer and client overhead |

On a local server the gap between total and wall clock should be small. If it is not, look at
the client: a new connection per request, a slow JSON library, or a proxy. Against a hosted API
the gap is the network, which is the subject of
[why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md).

## A short script

A sketch with Python and `requests`, against a local jev server. It reuses one connection,
discards warm-up runs and keeps the Server-Timing header of each response:

```python
import statistics, time, requests

URL = "http://127.0.0.1:8017/v1/systemone"
body = {"model": "jev-latest",
        "state": "I was charged twice for the same order.",
        "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}}}

s = requests.Session()
for _ in range(5):                                  # warm-up, not recorded
    s.post(URL, json=body, timeout=10)

wall, server = [], []
for _ in range(50):
    t0 = time.perf_counter()
    r = s.post(URL, json=body, timeout=10)
    wall.append((time.perf_counter() - t0) * 1000)
    server.append(r.headers.get("Server-Timing"))

print("median ms", statistics.median(wall))
print("p90 ms", statistics.quantiles(wall, n=10)[8])
```

For more robust clients, with retries and error handling, see
[a Python client for local LLM decisions](python-client-for-local-llm-decisions.md); from the
shell, `curl -D -` prints the headers, as on
[curl examples for a local LLM decision API](curl-examples-for-a-local-llm-api.md).

## One benchmark at a time

A CPU running two benchmarks is two benchmarks sharing memory bandwidth and cores, and a model
that reads its weights from memory for every pass is sensitive to both. The result is two slower
numbers, neither of which describes either system alone. The same goes for a build, a video
call, or an indexing job in the background.

When comparing systems, run them in turn on the same idle machine, with the same requests, and
say so. Our three-way comparison used the same two requests on the same laptop for all three:
jevos at 54 and 220 ms, Laya at 104 and 449 ms, and the hosted Jev at 344 and 345 ms.

## What to report

- **Hardware and settings**: CPU model, thread count, device. Ours: Intel Core Ultra 7 255H,
  16 threads, `--device cpu`.
- **The model file**: name and quantization. `GET /health` reports the model file's sha256, the
  llama.cpp release and a fingerprint; paste them into the report.
- **Requests**: their token counts, or better the files themselves.
- **Statistics**: number of runs, median, p90, and whether times are server-side or wall clock.
- **What was not measured.** Concurrency, other machines, other request sizes.

The same fields are what an audit log of decisions should carry; see
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## Short answers to the questions that lead here

**How do I benchmark LLM latency?** Warm up, repeat a realistic request many times, report
median and p90, and keep the machine otherwise idle.

**Why is my first LLM request so slow?** It pays one-time costs. Wait for `/health` to report
ready, then discard the first few timings.

**What is p90 latency?** The time that 90 in 100 requests beat. It describes the slow requests
users actually notice.

**Should I use Server-Timing or my own timer?** Both. The header tells you what the server spent;
your timer tells you what your application waits.

**Can I benchmark two models at once to save time?** Not on one CPU. They compete for the same
cores and memory, and both results are wrong.

**See also:** [the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md),
[throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md)
and [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- `/health` fields, `Server-Timing` metrics, `usage.input_tokens`, and the comparison latencies:
  the [jev README](https://github.com/feder-cr/jev), jev source and our own measurements.
- Server-Timing: [W3C Server Timing](https://www.w3.org/TR/server-timing/), Working Draft
  2026-04-07, fetched 2026-09-29.
- Tail latency: Dean and Barroso,
  [The Tail at Scale](https://research.google/pubs/the-tail-at-scale/), CACM 2013, abstract
  fetched 2026-09-29.
- The script is a sketch, not a tool we ship.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where the house rule for benchmarks is
one at a time on a laptop left otherwise alone: slower to do, and the only way the numbers mean
anything.*
