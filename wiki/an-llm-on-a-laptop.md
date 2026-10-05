---
title: "An LLM on a laptop: what it can do in real time"
description: "On an Intel Core Ultra 7 255H laptop, jevos answers yes/no questions in 22 to 130 ms. What that allows in real time, and what we did not measure."
parent: "Local and private AI"
nav_order: 10
---

# An LLM on a laptop: what it can do in real time

**On a laptop with an Intel Core Ultra 7 255H, 16 threads and no GPU, jevos answers a yes/no
question about a short text in 28 ms and a long text in 130 ms, fast enough to sit
inside a user action, a chat message or a game loop.** It runs on the CPU with 8-bit weights
through OpenVINO, and generates no text, so the time does not depend on the length of an answer. Real time here means one decision per event, a few per second: not
a stream of tokens, and not a video frame rate.

The useful way to read those numbers is as a budget. At 22 to 130 ms, the model fits inside
anything a person waits for, but a design that asks it dozens of questions per keystroke, or
feeds it long documents in a tight loop, will not feel instant.

This page is the measured numbers, what they allow, how a real-time loop has to wait for the
model, what it is like to share the laptop with the model, and the practical questions, battery and heat, that
we have not measured.

## The measured numbers

All on the same machine, `jev serve --threads 16`, through the HTTP API, median of 10 after 3
warm-up requests:

| Request | Text read from scratch | Same text asked again |
|---|---|---|
| one question, short request | 28 ms | not measured |
| one question, long request | 130 ms | 22 ms |
| one question on the README's example | 49 ms | not measured |
| three questions on the README's example (95 tokens) | 66 ms | 39 ms |

Two rules of thumb follow. Time grows with the text read from scratch, as explained on
[why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).
And extra questions about the same text are cheap, because the text is read once, and a text
asked about again is kept, so the next question reads only the question; the reason is on
[many questions about one text](many-questions-about-one-text.md).

## What does 22 to 130 ms allow?

Measured against what people and programs wait for:

- **A click or a form submit.** A decision under a quarter of a second fits inside the
  response to a user action: flag a message before it is posted, route a form as it is sent.
- **A chat message.** A moderation or routing check per message, before it is shown, is well
  inside the time a person takes to read the previous one.
- **An email or a ticket.** One request per item, several questions each, is a fraction of a
  second per message: a mailbox of a thousand messages is minutes, not hours.
- **A game or control loop.** A few decisions per second, not one per frame. The loop has to
  be designed around the model's time, as the next section explains.

What the same CPU-only profile allows away from a laptop, on small servers and branch machines,
is on [edge AI decisions on a CPU](edge-ai-decisions-on-a-cpu.md).

What it does not allow: a question per keystroke on long text, or many independent requests
fired at once and all expected back within the single-request time. The laptop figure is the
latency of one request; capacity under load is a different measurement. How to spend the budget
is on [latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md).

## A real-time loop has to wait for the model

A loop that asks the model something every few steps cannot pretend the answer is instant. The
honest design pauses the loop, or holds the last decision, until the answer comes back, and shows
the time per decision. At 22 to 130 ms that means a few decisions per second, about slow-changing
things, with the per-frame work left to code. That is the pattern for any real-time use of a
model: the loop is built around the decision time, not the other way round, and how to split the
work is on [gating AI agent tool calls](gating-ai-agent-tool-calls.md), which uses the same
describe, ask, act shape.

## Sharing the laptop with the model

The model is not alone on a laptop. Three practical points:

- **Memory.** The model stays in memory for as long as the server runs. On a machine that is
  also running a browser, an editor and a build, check what it takes on yours.
- **Threads.** `--threads` defaults to all logical CPUs. Set it lower if other heavy
  applications are running. On a laptop with other work going on, giving the model every thread
  can slow both the model and the rest.
- **One server, loaded once.** Starting the server loads the model; the first requests after
  start-up may be slower than the rest. Start it once, warm it up with a request or two, and
  keep it running rather than launching it per decision.

## Battery and heat: what we have not measured

We have not measured power draw, battery life or temperature with jevos running, on battery or
on mains. What can be said in general:

- The model uses the CPU only while it answers. Between requests the server waits. A workload
  of occasional decisions is a very different load from a batch job that keeps the CPU busy for
  minutes.
- Laptops can change CPU behaviour between mains power and battery, and under sustained heat.
  If your use depends on the latency figures above, measure on battery too, and after the
  machine has been busy for a while, not only on a cool machine plugged into the wall.
- Fewer threads may be the better trade on battery. We have not measured this, so treat it as a
  setting to test, not a recommendation.

When you measure, measure one thing at a time: two benchmarks sharing one CPU distort each
other. The method is on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

## Short answers to the questions that lead here

**Can a laptop run an LLM in real time?** A small one, for decisions: jevos answers in 22 to
130 ms on an Intel Core Ultra 7 255H without a GPU. Generating long text is a different job.

**How much memory does it take?** Measure it on your machine with the server running: the model
stays loaded between requests.

**Does it drain the battery?** We have not measured it. The CPU works only while a request is
being answered, so the effect depends on how often you ask.

**Will it be as fast on my laptop?** Not necessarily; ours is the only machine we have timed.
Warm it up and measure with your own inputs.

**Do I need a gaming laptop with a GPU?** No. jev runs on the CPU only; everything on this page ran without a GPU.

**See also:** [run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md),
[edge AI decisions on a CPU](edge-ai-decisions-on-a-cpu.md) and
[ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Sources

- Latency, the repeated-text and three-question timings: our measurements
  on an Intel Core Ultra 7 255H laptop, 16 threads, no GPU, reported in the
  [jev README](https://github.com/feder-cr/jev).
- Battery, heat and thread settings on battery: not measured.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The laptop on this page is the one
the README's benchmark numbers come from.*
