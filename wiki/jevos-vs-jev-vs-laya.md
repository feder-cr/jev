---
title: "jevos vs Jev vs Laya for yes/no decisions"
description: "jevos, TypeSafe's hosted Jev and the local Laya model compared on the same requests: latency, accuracy on six tasks, context, cost."
parent: "Comparisons"
nav_order: 1
---

# jevos vs Jev vs Laya for yes/no decisions

**For yes/no decisions on a CPU, jevos-v4 is the fastest of the three on short and long requests,
TypeSafe's hosted Jev is the most accurate, and Laya is the one to pick when you need many
languages.** On the same laptop and the same requests, jevos answered
in 28 ms and 130 ms, Laya in 129 ms and 480 ms, and Jev in about 311 and 314 ms, most of it
network. On six tasks, Jev scored higher than jevos-v4 on every one, for example 1.00 against
0.95 on Admission policy (yes/no rules), and jevos-v4 scored higher than Laya on every one
(0.95 against 0.54 on the same task).

A conflict of interest, stated first: we build jevos. Every number below was measured on the
same requests or the same questions for all three, and the places where jevos loses are in the
tables, not in footnotes.

This page is what each one can answer, the speed and accuracy measurements and how they were
taken, and which one fits which job.

## What each one does

| | **jevos** | Jev | Laya |
|---|:---:|:---:|:---:|
| Yes/no questions | yes | yes | yes |
| Multiple choice | yes | yes | yes |
| Scores | early | yes | yes |
| Runs on | your machine | TypeSafe's cloud | your machine |
| Cost | free | per token | free |
| Context | 8,192 tokens | not stated | 512 tokens (English checkpoint) |
| Languages | English | see TypeSafe's docs | 100+ |
| Runtime | OpenVINO, CPU | hosted API | PyTorch, CPU or GPU |

All three answer the same three primitives in principle: `noul` (yes/no, as a probability),
`choice` and `score`, and none of them generates text to get there. jevos speaks the same wire
format as Jev, so code written for Jev's SDK runs against a jevos server unchanged for yes/no
and `choice` questions, and for `score` questions, whose answers are early (58.5% on held-out score
questions, 86% within one level).

Laya is an encoder model (ModernBERT-large, 421M parameters, per its own README) with an English
checkpoint and a multilingual one. The numbers here use the English checkpoint as shipped.

## Speed

Same two requests on the same laptop, an Intel Core Ultra 7 255H with 16 threads and no GPU in
use; Jev through its hosted API. Each figure is the median of 10 requests through the HTTP API
after 3 warm-up requests, each text read from scratch, measured with jevos-v3, which has the same
size and speed as jevos-v4:

| | short request | long request |
|---|---|---|
| **jevos** (OpenVINO, CPU, INT8) | **28 ms** | **130 ms** |
| Laya, English checkpoint (PyTorch, CPU) | 129 ms | 480 ms |
| Jev (hosted API, network included) | 311 ms | 314 ms |
| Qwen3.5-4B | 3,060 ms | 4,761 ms |

The two local models grow with the length of the text; Jev's time barely changes, because it is
dominated by the round trip, so on a very long document the hosted model's relative cost falls.
From a server closer to TypeSafe's, Jev's numbers would likely be lower; this is what an
application sees from our laptop. If the same text is asked again (the text cache is on by
default), the long request takes 22 ms. What "fastest" can honestly mean, and why nobody can claim the fastest model
in general, is on [the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md).

## Accuracy on six tasks

Six tasks, with the same questions and the same HTTP client for all of them (the answers come
from the rules, from annotators or from experts):

| task | **jevos-v4** | Jev | Qwen3.5-4B | Laya |
|---|---|---|---|---|
| Admission policy (yes/no) | 0.95 | **1.00** | 0.82 | 0.54 |
| Rental policy (choice) | 0.76 | **0.91** | 0.60 | 0.31 |
| Rules and scenarios, ShARC (yes/no) | 0.76 | **0.88** | 0.72 | 0.55 |
| Authority rules, SemIf (choice) | 0.81 | **0.98** | 0.78 | 0.64 |
| Fraud points (score) | 0.50 | **0.69** | 0.45 | 0.25 |
| Patent phrases (score, expert ratings) | 0.37 | **0.59** | 0.18 | 0.32 |

No task text was used to train jevos. Five of the six sets (all but patent phrases) helped
choose the released checkpoint, so jevos's scores there may be slightly optimistic.

Jev is clearly stronger on rules, and the gap is widest on Fraud points, where several signals
are summed, which is arithmetic, the weakest skill of a small model
([measured here](small-llm-arithmetic-yes-no-questions.md)).

Laya was used as shipped, English checkpoint, with no tuning on these tasks, so its numbers are
not a measure of Laya on the tasks it was built and documented for.

## Which one to use

**jevos-v4** if the decision is yes/no or multiple choice, the text is English, and you want it local: on a laptop,
in CI, on a server without a GPU, or anywhere the text should not leave the machine. It is the
fastest of the three on both request sizes, and free. Plan around its weak spot, computation,
by doing arithmetic in code.

**Jev** if accuracy on hard rules matters more than latency and cost, if you need scores
better than jevos's early ones, or if you do not want to run anything. Because the wire format is the
same, starting with jevos and moving the hard cases to Jev is a change of URL, not of code. The switch itself, step by step, is on
[an open-source alternative to Jev](open-source-alternative-to-jev.md), and the same trade-off
against a general hosted chat API is on [jevos vs the OpenAI API](jevos-vs-openai-api-for-classification.md).

**Laya** if you need many languages and your texts fit its context.

## Short answers to the questions that lead here

**Is jevos an alternative to Jev?** For yes/no and multiple-choice questions, yes: same wire
format, local, free and faster from a laptop. Scores are answered too, but early. Jev is more
accurate on rules (for example 1.00 against 0.95 on Admission policy).

**Which is fastest?** jevos: 28 ms and 130 ms against 129/480 ms for Laya and about 311/314 ms
for Jev on our two requests.

**Which is most accurate?** Jev, on all six of our tasks.

**Can jevos replace Laya?** For English yes/no decisions with texts longer than 512 tokens, it
is faster and more accurate in our test. For other languages, not yet. On the two score tasks jevos-v4
was ahead of Laya (0.50 against 0.25, 0.37 against 0.32).

**Does my data leave my machine?** With jevos and Laya, no. With Jev, the text is sent to
TypeSafe's API.

**Are jevos and TypeSafe related?** No. jevos is an independent project; "TypeSafe" and Jev
belong to TypeSafe AI.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md)
and [our held-out benchmark said 0.855](held-out-benchmark-too-optimistic.md), which explains
why we distrust a test split built like the training data.

## Sources

- Latency and accuracy tables, and the feature table: the
  [jev README](https://github.com/feder-cr/jev), measured by us on the same requests and
  questions for all of them (jevos-v4, Jev, Qwen3.5-4B and Laya).
- Laya's model, languages, context and runtime: the
  [Laya repository](https://github.com/NandhaKishorM/laya), fetched 2026-09-29.
- Jev's question types: [TypeSafe's documentation](https://docs.typesafe.ai), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. We would rather you picked the right one of the three than the one we build.*
