---
title: "jevos vs Jev vs Laya for yes/no decisions"
description: "jevos, TypeSafe's hosted Jev and the local Laya model compared on the same requests: latency, accuracy on 2,000 unseen-policy questions, context, cost."
parent: "Comparisons"
nav_order: 1
---

# jevos vs Jev vs Laya for yes/no decisions

**For yes/no decisions on a CPU, jevos is the fastest of the three on short and long requests,
TypeSafe's hosted Jev is the most accurate, and Laya is the one to pick when you need many
languages or multiple choice today.** On the same laptop and the same requests, jevos answered
in 54 ms and 220 ms, Laya in 104 ms and 449 ms, and Jev in about 345 ms both times, most of it
network. On 2,000 yes/no questions about business policies none of them had been tuned on,
Jev was right 0.927 of the time, jevos 0.815, and Laya 0.489.

A conflict of interest, stated first: we build jevos. Every number below was measured on the
same requests or the same questions for all three, and the places where jevos loses are in the
tables, not in footnotes.

This page is what each one can answer, the speed and accuracy measurements and how they were
taken, and which one fits which job.

## What each one does

| | **jevos** | Jev | Laya |
|---|:---:|:---:|:---:|
| Yes/no questions | yes | yes | yes |
| Multiple choice | soon | yes | yes |
| Scores | soon | yes | yes |
| Runs on | your machine | TypeSafe's cloud | your machine |
| Cost | free | per token | free |
| Context | 8,192 tokens | not stated | 512 tokens (English checkpoint) |
| Languages | English | see TypeSafe's docs | 100+ |
| Runtime | llama.cpp, CPU | hosted API | PyTorch, CPU or GPU |

All three answer the same three primitives in principle: `noul` (yes/no, as a probability),
`choice` and `score`, and none of them generates text to get there. jevos speaks the same wire
format as Jev, so code written for Jev's SDK runs against a jevos server unchanged for yes/no
questions; `choice` and `score` are refused with a `422` until they ship.

Laya is an encoder model (ModernBERT-large, 421M parameters, per its own README) with an English
checkpoint and a multilingual one. The numbers here use the English checkpoint as shipped.

## Speed

Same two requests on the same laptop, an Intel Core Ultra 7 255H with 16 threads and no GPU in
use; Jev through its hosted API from Europe:

| | short request | long request |
|---|---|---|
| **jevos** (llama.cpp, CPU, q4_k_m) | **54 ms** | **220 ms** |
| Laya, English checkpoint (PyTorch, CPU) | 104 ms | 449 ms |
| Jev (hosted API, network included) | 344 ms | 345 ms |

The short request is about 30 tokens and the long one about 190. The two local models grow with
the length of the text; Jev's time barely changes, because it is dominated by the round trip, so
on a very long document the hosted model's relative cost falls. From a server closer to
TypeSafe's, Jev's numbers would likely be lower; from a laptop in Europe, this is what an
application sees. What "fastest" can honestly mean, and why nobody can claim the fastest model
in general, is on [the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md).

## Accuracy on rules none of them was tuned on

2,000 yes/no questions on three business policies, with every answer computed by code from the
rule and the facts, identical for all three:

| | accuracy |
|---|---|
| Jev | **0.927** |
| **jevos** | 0.815 |
| Laya (zero-shot, English checkpoint) | 0.489 |

Jev is clearly stronger on rules, and the gap is largest on additive point scores, where
several signals are summed and compared with a threshold, which is arithmetic, the weakest skill
of a small model ([measured here](small-llm-arithmetic-yes-no-questions.md)).

Laya's result needs its context: it was used as shipped, with no tuning on these tasks, and its
512-token context truncates the longer rule texts, which explains most of its score. It is not a
measure of Laya on the tasks it was built and documented for.

## Which one to use

**jevos** if the decision is yes/no, the text is English, and you want it local: on a laptop,
in CI, on a server without a GPU, or anywhere the text should not leave the machine. It is the
fastest of the three on both request sizes, and free. Plan around its weak spot, computation,
by doing arithmetic in code.

**Jev** if accuracy on hard rules matters more than latency and cost, if you need multiple
choice or scores now, or if you do not want to run anything. Because the wire format is the
same, starting with jevos and moving the hard cases to Jev is a change of URL, not of code. The switch itself, step by step, is on
[an open-source alternative to Jev](open-source-alternative-to-jev.md), and the same trade-off
against a general hosted chat API is on [jevos vs the OpenAI API](jevos-vs-openai-api-for-classification.md).

**Laya** if you need many languages, or local multiple choice and scores today, and your texts
fit its context.

## Short answers to the questions that lead here

**Is jevos an alternative to Jev?** For yes/no questions, yes: same wire format, local, free and
faster from a laptop. Jev is more accurate on unseen rules (0.927 against 0.815) and answers
multiple choice and scores.

**Which is fastest?** jevos: 54 ms and 220 ms against 104/449 ms for Laya and about 345 ms for
Jev on our two requests.

**Which is most accurate?** Jev, on our 2,000 policy questions.

**Can jevos replace Laya?** For English yes/no decisions with texts longer than 512 tokens, it
is faster and more accurate in our test. For other languages or for choice and score, not yet.

**Does my data leave my machine?** With jevos and Laya, no. With Jev, the text is sent to
TypeSafe's API.

**Are jevos and TypeSafe related?** No. jevos is an independent project; "TypeSafe" and Jev
belong to TypeSafe AI.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md)
and [our held-out benchmark said 0.855](held-out-benchmark-too-optimistic.md), which explains
why we report the 2,000-question number.

## Sources

- Latency and accuracy tables, and the feature table: the
  [jev README](https://github.com/feder-cr/jev), measured by us on the same requests and
  questions for all three.
- Laya's model, languages, context and runtime: the
  [Laya repository](https://github.com/NandhaKishorM/laya), fetched 2026-09-29.
- Jev's question types: [TypeSafe's documentation](https://docs.typesafe.ai), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. We would rather you picked the right one of the three than the one we build.*
