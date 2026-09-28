---
title: "Latency budgets: where a 200 ms model fits"
description: "What a 50 to 220 ms decision fits and what it does not: interactive UI, webhooks, batch jobs and game loops, against published time limits."
parent: "Speed"
nav_order: 9
---

# Latency budgets: where a 200 ms model fits

**A decision that takes 50 to 220 ms fits almost everything except work that has to finish
inside a single animation frame.** It is well inside a webhook timeout of a few seconds, fast
enough to feel immediate behind a button, and cheap enough to run on every item of a batch
job. It does not fit a real-time loop at 60 frames per second, or a user interface that must
react within a tenth of a second to every keystroke. Those are the two edges of the budget.

The useful habit is to treat the model as one line of a budget, not the whole of it. The
request has to be built, sent, answered and acted on, and a 200 ms model inside a 250 ms budget
leaves nothing for the rest.

This page is the published limits people design to, how a 50 to 220 ms model sits in each
context, how to add up a budget, and what to do when it does not fit.

## The limits people design to

| Context | Budget | Source |
|---|---|---|
| Feels instantaneous | 0.1 s | Nielsen, response time limits |
| Flow of thought uninterrupted | 1 s | Nielsen, response time limits |
| Attention kept on the task | 10 s | Nielsen, response time limits |
| Visible response to input | 100 ms, process input within 50 ms | Google's RAIL model |
| One animation frame at 60 fps | about 16 ms, aim for 10 ms | Google's RAIL model |
| Slack event webhook | respond within 3 s | Slack Events API |

Nielsen's three limits date from 1993: 0.1 second is "the limit for
having the user feel that the system is reacting instantaneously", 1 second "for the user's flow
of thought to stay uninterrupted". RAIL asks web pages to process input within 50 ms so a
visible response can happen within 100 ms.

jevos, on our reference laptop (Intel Core Ultra 7 255H, 16 threads, `q4_k_m`), took 54 ms on a
request of about 30 tokens and 220 ms on one of about 190. That puts short requests near the
"instantaneous" line and long ones well inside the one-second line.

## Behind a button or a form

A user clicks "submit" on a support form and the app decides where the ticket goes. Under 1
second the user's flow is not broken, so a 220 ms decision fits with room for the rest of the
request. What does not fit is running the model on every keystroke to give live feedback: at
50 ms of model time plus the round trip, the 100 ms target is tight and a long text misses it.

For interactive use, show something immediately and let the decision arrive a moment later.
Keep the state short, since each prompt token costs about 1.1 ms on our laptop; the detail is on
[why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).

## Webhooks and chat bots

Event senders give you a deadline. Slack's Events API says an app "should respond to the event
request with an HTTP 2xx within three seconds", and retries if it does not. A 220 ms decision
fits several times over. Slack also asks apps to respond "as soon as you can", so acknowledging
first and deciding after is still the safer design: a slow moment elsewhere does not cause
retries.

Chat moderation fits the same way: a message arrives, the rules are asked as questions in one
request, and the bot acts before most people have read the message. That architecture is
sketched on [a Discord moderation bot with a local LLM](discord-moderation-bot-with-a-local-llm.md),
and for inboxes on [email triage with a local LLM](email-triage-with-a-local-llm.md).

## Batch jobs

Here latency becomes cost per item. At 220 ms per 190-token record, one process handles a few
records per second when requests run one after another; at that rate a million records would
take about 61 hours on one process, which is arithmetic, not a measured run. The budget is the length of the job window, not a reaction
time. For files on disk, [batch decisions with jev decide](batch-decisions-with-jev-decide.md)
covers running requests without a server, and how capacity differs from latency is on
[throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).

Two levers matter most in batch: grouping questions about the same record in one request (three
questions took about 165 ms together against 103 ms for one alone, see
[many questions about one text](many-questions-about-one-text.md)), and trimming each record to
the fields the questions need.

## Game loops and real-time control

This is where a 200 ms model does not fit. At 60 frames per second a frame is about 16 ms, and
RAIL suggests 10 ms of work per frame. Even the short request is several frames long.

The honest way around it is to let the loop wait for the model and show the time per decision,
which demonstrates decisions, not reaction speed. A real-time system
would ask the model less often, about slower-changing things (a strategy, not a jump), and keep
the per-frame logic in code.

## Adding up a budget

An illustrative example for a web request with a 500 ms target, with made-up numbers for
everything except the model:

| Step | Time |
|---|---|
| Receive request, load the record | 30 ms (illustrative) |
| Build the state, trim fields | 5 ms (illustrative) |
| Model, one request, three questions | about 165 ms (measured on our laptop, 95 tokens) |
| Act on thresholds, write a log line | 20 ms (illustrative) |
| Total | about 220 ms |

That leaves room for a slow moment, and for the difference between a median and a p90: budgets
should be set against the slow end, not the typical request. How to measure that end is on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

When it does not fit: shorten the input, group the questions, move the decision off the
critical path (decide after responding), or ask less often. A hosted model adds a round trip on
top of all of this, which is why it rarely fits the tight end; see
[why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md).

## Short answers to the questions that lead here

**Is 200 ms fast enough for a user interface?** For an action like submitting a form, yes: it
is well under the 1-second limit for uninterrupted flow. For reacting to every keystroke, it is
tight.

**Can a local LLM run inside a game loop?** Not per frame. At 60 fps a frame is about 16 ms. Ask
the model about slower decisions and keep per-frame logic in code.

**Does a 220 ms model fit a webhook?** Yes. Slack, for example, allows three seconds.

**How many decisions per second is 220 ms?** About four or five, if requests run one after
another on one process. Capacity under concurrency is a different measurement.

**What should I budget against, the median or the p90?** The slow end. A budget met by the
median is missed by one request in two.

**See also:** [the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md),
[an LLM on a laptop](an-llm-on-a-laptop.md) and
[AI agent guardrails with yes/no questions](ai-agent-guardrails-with-yes-no-questions.md).

## Sources

- jevos latencies (54 ms, 220 ms, 165 ms against 103 ms, about 1.1 ms per prompt token): our measurements and the [jev README](https://github.com/feder-cr/jev).
- Response time limits: Jakob Nielsen,
  [Response Times: The 3 Important Limits](https://www.nngroup.com/articles/response-times-3-important-limits/),
  1993, fetched 2026-09-29.
- Input and frame budgets: [RAIL model, web.dev](https://web.dev/articles/rail), fetched
  2026-09-29.
- Webhook deadline: [Slack Events API](https://docs.slack.dev/apis/events-api/), fetched
  2026-09-29.
- Rows marked illustrative in the budget table are made up for the example.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose own game demo pauses for the
model, because we would rather show the real decision time than hide it behind a frame rate.*
