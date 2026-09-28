---
title: "Reducing LLM cost with local yes/no decisions"
description: "Move the many small decisions in an LLM app, such as routing, checks and labels, off a paid API onto a local yes/no model, and keep the rest there."
parent: "Agents and routing"
nav_order: 8
---

# Reducing LLM cost with local yes/no decisions

**The cheapest large-model call is the one that was only ever a decision: "is this spam?",
"does this need a human?", "did the reply answer the question?". Those calls can move to a
local yes/no model that costs no money per token and generates no output tokens, while the large
model keeps the work that needs generation or reasoning.** In pipelines and agents the small
decisions can be a large share of the calls, because they run on every message and every agent
step, while the long generations run once per conversation.

The saving is not free. A local model is less accurate than a large one on hard questions, it
needs a CPU and some memory, and you need a test set to know which decisions are safe to move.
This page is about moving the right ones.

This page is how to find the decision calls, what a local decision costs instead, a
back-of-envelope estimate you can fill in with your own numbers, what should stay on the large
model, and the costs of moving that are easy to forget.

## Where the calls in an LLM app actually go

List every call your application makes to a paid model and give each a verb. Typical ones:

| Call | Verb | Output needed |
|---|---|---|
| intent or queue routing | decide | a label |
| "is this safe to send?" | decide | yes or no |
| relevance of a retrieved passage | decide | yes or no per passage |
| "is the task done?" in an agent loop | decide | yes or no |
| evaluation of outputs in CI | decide | yes or no per criterion |
| drafting the reply | generate | text |
| summarising a document | generate | text |
| extracting fields into JSON | generate | structured text |

Everything in the "decide" rows is a candidate. A retrieval step that checks ten passages makes
ten decisions per user question; a guardrail on every agent step makes one per step. How to spot
these in an existing codebase is on
[replacing chat LLM calls with yes/no questions](replacing-llm-calls-with-yes-no-questions.md).

## What a local decision costs instead

Hosted models are billed per token. OpenAI's API pricing page, for example, lists prices per
million input tokens and per million output tokens separately, with output tokens priced higher
for its text models. A decision made by a chat model pays for the prompt and for the answer,
even when the answer is one word.

A local yes/no decision has a different cost shape:

- **No per-token bill.** jevos is free to run, and the code is MIT.
- **No output tokens.** Every response reports `output_tokens: 0`; the answer is a probability,
  not text.
- **CPU time.** On our reference laptop (Intel Core Ultra 7 255H, 16 threads, no GPU), 54 ms for
  a short request and 220 ms for a long one, about 1.1 ms per prompt token.
- **Memory.** About 1.2 GB with the model loaded.
- **Shared reading.** Several questions about one text are cheaper together: three took about
  165 ms against 103 ms for one alone. Grouping questions per text is the main lever, covered
  on [many questions about one text](many-questions-about-one-text.md).

So the cost moves from a bill that grows with every call to a machine that you already run or
can size. The question becomes capacity, not price.

## A back-of-envelope estimate

Fill this in with your own numbers; nothing below is a measurement.

- D = decision calls per day that you could move
- T = average tokens per decision call, prompt plus answer
- P = your provider's blended price per token for those calls
- Today's cost of those calls, per day, is about D times T times P.
- After moving them, that line goes to zero, and you add the CPU time: D times the local latency
  for requests of that length, spread over however many cores or servers you give it.

An **illustrative** example: 200,000 decisions a day of 150 tokens each is 30 million tokens a
day on the bill. Locally, a 150-token request falls between the 54 ms we measured at 30 tokens
and the 220 ms at 190 tokens, around 180 ms, so the same decisions add up to about 36,000
seconds, roughly ten hours, of one laptop answering one request at a time. Whether that is cheaper depends on your prices and your hardware, which is why
the formula is more useful than the example.

The latency side often matters as much as the bill. A hosted call pays a network round trip on
every decision; the hosted Jev took about 344 ms on our short request from Europe, almost all of
it network. The trade-off in general is on
[local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md).

## What should stay on the large model

- **Anything generated.** Replies, summaries, extraction into fields, code.
- **Decisions that need reasoning or knowledge beyond the text.** A small model reads; it does
  not know your domain beyond what you put in the question.
- **Rules with sums and dates.** On 2,000 yes/no questions from three business policies neither
  model was tuned on, the hosted Jev was right 0.927 of the time against 0.815 for jevos, and the
  gap was largest on additive point scores. Either compute those parts in code first, or keep the
  decision on the large model.
- **Languages other than English.** jevos reads English only.
- **Low-volume, high-stakes decisions.** If a decision runs ten times a day and a mistake is
  expensive, the saving is small and the accuracy matters more.

A middle path is to keep both: answer locally when the probability is clear and send the
uncertain middle to the large model. That is
[a model cascade](model-cascade-small-model-first.md).

## The costs of moving that are easy to forget

- **A test set.** Before moving a decision, run the local model on a hundred or more real,
  hand-labelled cases and compare with the current model. On our own set of 999 questions
  written after training, accuracy ranged from 0.954 on stated facts to 0.584 on arithmetic;
  your decisions will land somewhere in that spread.
- **Rewriting the prompt.** A decision prompt usually becomes one or more yes/no questions with
  the rule written in. That is design work, and it pays off in accuracy.
- **Operations.** A local server is a process to deploy, monitor and update. Pinning the model
  file by hash and logging it is covered on
  [logging LLM decisions for audit](logging-llm-decisions-for-audit.md).
- **Capacity.** Our figures are latency for one request at a time on one laptop, not throughput.
  Size the machine on your own load.

## Short answers to the questions that lead here

**How do I reduce LLM API costs?** Find the calls that are decisions, move those that pass a test
on your own cases to a local yes/no model, and keep generation on the paid model.

**Why do output tokens matter?** Providers bill them, often at a higher rate than input. A local
yes/no model produces none.

**Is a local model free?** Free of per-token charges. It costs CPU time and about 1.2 GB of
memory.

**Will accuracy drop?** On hard rule questions, yes: 0.815 for jevos against 0.927 for the hosted
Jev on our 2,000-question comparison. On reading questions the gap is smaller. Measure yours.

**What should never move?** Generation, reasoning beyond the text, non-English input, and rare
decisions where a mistake costs more than the calls ever did.

**See also:** [an LLM router with yes/no questions](llm-router-with-yes-no-questions.md),
[structured output vs a probability](structured-output-vs-a-probability.md) and
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- Our measurements: latency, per-token latency, memory, the three-question timing, the hosted
  Jev timing and the 2,000-question accuracy comparison, from the
  [jev README](https://github.com/feder-cr/jev); accuracy by kind from our 999-question set.
- OpenAI, [API pricing](https://developers.openai.com/api/docs/pricing), for the structure of
  per-token billing (input and output listed separately), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. Its responses report zero output tokens, which is the whole cost argument in one
field.*
