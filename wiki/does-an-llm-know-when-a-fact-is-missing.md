---
title: "Does an LLM know when a fact is missing?"
description: "When a record lacks a fact the decision needs, does the model's confidence drop? Measured on jevos-v4, Jev, Qwen3.5-4B and Laya over four tasks."
parent: "Measurements"
nav_order: 4
---

# Does an LLM know when a fact is missing?

**A model that is asked to decide on a record with a missing fact should become less sure of
itself, and on our four tests jevos-v4 did so far more reliably than the other systems we
measured.** Its confidence told answerable questions from unanswerable ones with an AUROC of 0.81
to 0.95, where 0.5 means it cannot tell them apart at all. TypeSafe's hosted Jev, the most accurate
of the four on ordinary questions, scored 0.42 to 0.68 on the same test, below 0.5 on two tasks.

Accuracy and this measurement answer different questions. Accuracy asks whether the answer is
right. This one asks whether the model knows when no answer can be right, which is what decides
whether a confidence threshold can keep a bad case away from an automatic decision.

This page is the experiment, how to read the number, the results task by task, what they mean
for an application, and what they do not show.

![Knows when a record is missing a fact the decision needs: AUROC of each system's confidence, answerable questions against unanswerable ones. Admission policy: jevos-v4 0.90, Jev 0.68, Qwen3.5-4B 0.60, Laya 0.58. Fraud points: 0.94, 0.46, 0.55, 0.50. Policy ratings: 0.95, 0.68, 0.83, 0.79. Support tickets: 0.81, 0.42, 0.53, 0.47.](https://raw.githubusercontent.com/feder-cr/jev/main/assets/jevos_missing_facts.png)

## The experiment

Each task is a set of records, such as an event attendee, a payment or a support ticket, with a
written rule and a question the rule decides. In some of the records a fact the rule needs has been
taken out: the attendee's age, a risk signal, the customer's tier. For those records no answer is
right, because the information to decide is not there.

Every system gets the same records and the same questions through the same HTTP client, and
answers with its own confidence. The test then asks one thing of that confidence: is it lower on
the records with a missing fact than on the complete ones?

## How to read the number

The number is an AUROC: pick one complete record and one record with a fact missing at random, and
it is the probability that the system is more confident on the complete one.

- **1.0**: the system is always less sure when a fact is missing.
- **0.5** (the red dashed line in the chart): it cannot tell; its confidence is the same either way.
- **Below 0.5**: it is *more* sure when a fact is missing, which is worse than guessing.

The thin vertical lines are 95% intervals. Where two bars' intervals do not overlap, the gap is
not an accident of the sample.

The measure does not depend on any one threshold, which is why it suits this question: it says how
well confidence *could* separate the two kinds of record, for every threshold at once. It is the
same idea as [a reliability diagram](reading-a-reliability-diagram.md), asked of a different
property: not whether 0.8 means 80%, but whether low confidence lands on the cases that deserve it.

## Results by task

| Task | Records lacking a fact | jevos-v4 | Jev | Qwen3.5-4B | Laya |
|---|---|---|---|---|---|
| Admission policy | 76 of 576 | **0.90** | 0.68 | 0.60 | 0.58 |
| Fraud points | 100 of 600 | **0.94** | 0.46 | 0.55 | 0.50 |
| Policy ratings | 40 of 493 | **0.95** | 0.68 | 0.83 | 0.79 |
| Support tickets | 400 of 800 | **0.81** | 0.42 | 0.53 | 0.47 |

- **Admission policy** and **Fraud points** are the records of the
  [benchmark tasks in the README](https://github.com/feder-cr/jev), with a field the rules need
  left out of some of them.
- **Policy ratings** comes from [sys1bench](https://pypi.org/project/sys1bench/): support tickets,
  server logs, phishing emails and other records rated by a written policy; some tickets lack the
  customer tier.
- **Support tickets**, also from sys1bench: 800 tickets whose priority depends on the customer
  tier, removed from half of them.

The two sys1bench sets were never used to train or to choose jevos.

The same result in plainer terms: with the fact missing, jevos-v4 still answered with 75%
confidence or more on 0 to 42% of those questions, depending on the task. Jev did so on 60 to 71%.

## What it means for an application

A confidence threshold is only a safety net if low confidence falls on the cases that need a
person. On these tasks, a record with a missing fact is exactly such a case, and jevos-v4's
confidence mostly put it below the line.

That makes the [review band](human-in-the-loop-ai-with-a-review-band.md) work as intended: cases
under the threshold go to a person, and those cases include most of the records where the data was
incomplete. With a system whose confidence stays high when a fact is missing, the same threshold
would let those records through as confident automatic decisions.

It does not replace asking directly. When a fact is easy to name, a gate question such as "Does
the record state the customer's tier?" is cheaper and clearer than relying on a drop in confidence;
the pattern is on [ask whether the text says it at all](ask-whether-the-text-says-it.md). The
confidence drop is what catches the facts you did not think to ask about.

## What this measurement does not show

- **It is not accuracy.** On ordinary questions Jev is more accurate than jevos-v4 on all six
  README tasks; the comparison is on [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md). A system can
  be more accurate and worse at knowing when it cannot answer, and these results say that is what
  happens here.
- **Four tasks, one kind of gap.** Each task removes one named fact from a structured record. Texts
  where the gap is subtler, or where several facts are missing, were not measured.
- **Two of the four sets are ours.** Admission policy and Fraud points belong to the benchmark
  tasks, five of whose six sets helped choose the released jevos-v4 checkpoint; the two sys1bench
  sets were not used for that.
- **Each system's own confidence.** The test uses whatever confidence each system reports. It says
  how useful that number is for this purpose, not why it behaves as it does.

## Short answers to the questions that lead here

**Do LLMs know when information is missing?** It depends on the model. On our four tests, jevos-v4's
confidence separated complete records from records with a missing fact with an AUROC of 0.81 to
0.95; Jev's was 0.42 to 0.68.

**What does an AUROC of 0.5 mean here?** That the system is equally confident whether the fact is
there or not, so its confidence cannot be used to catch the missing cases.

**Is the more accurate model also better at this?** Not in our measurement. Jev is more accurate
on ordinary questions and worse at lowering its confidence when a fact is missing.

**Can I rely on confidence alone?** Use it as a net, together with explicit questions about the
facts a decision needs. It catches the gaps you did not anticipate.

**Was the test data used to train jevos?** The two sys1bench sets were never used to train or
choose jevos. The other two belong to sets that helped choose the released checkpoint.

**See also:** [ask whether the text says it at all](ask-whether-the-text-says-it.md),
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md) and
[LLM calibration explained](llm-calibration-explained.md).

## Sources

- All numbers on this page are our own measurements, published in the
  [jev README](https://github.com/feder-cr/jev) of 2026-10-05 with the chart above: the same records
  and questions for every system, through the same HTTP client.
- [sys1bench](https://pypi.org/project/sys1bench/), the source of the Policy ratings and Support
  tickets sets.

---

*From the notes of [jev](https://github.com/feder-cr/jev). We measure this because a model that is
confident when it should not be is more dangerous than one that is simply wrong more often.*
