---
title: "Human in the loop AI with a review band"
description: "Automate the confident ends of P(yes), send the uncertain middle to a person: how to size the review band, what to log, and how to keep it honest."
parent: "Probability and thresholds"
nav_order: 9
---

# Human in the loop AI with a review band

**The simplest working form of human in the loop AI is a review band: act automatically when
P(yes) is below a low threshold or above a high one, and send everything in between to a
person.** The band's edges come from your own labelled cases: pick them so the automated ends
meet an error target you can live with, and so the middle fits the hours your reviewers have.
Every decision is logged, and every human decision becomes a new labelled case.

The point is not to split work fairly between person and machine. It is to put people exactly
where the model is least reliable, and to make that share a number you can plan for, instead of
an escalation that happens whenever someone notices a problem.

This page is why a band beats a single threshold, how to size it, what to log, why the band is
often lopsided for a small model, how to keep it honest over time, and when a band is not
enough.

## Why a band instead of one threshold

A single cut-off forces a decision on every case, including those right next to it where the
model's answer is closest to a coin. A band lets the system decline those.

This is an old idea in machine learning, usually called a reject option or selective
classification. Geifman and El-Yaniv (2017) describe it for deep networks as trading coverage
for risk: the classifier abstains on the cases it is unsure of and, in exchange, makes fewer
errors on the cases it does answer. Their example reaches a 2 percent top-5 error on ImageNet
at almost 60 percent coverage. A review band is the same trade, with a person handling what the
model declines.

For a model that returns a probability per question, the band is two numbers and an `if`:

```python
p = answer["answers"]["refund"]["noul"]
if p >= HIGH:
    outcome = "auto_yes"
elif p <= LOW:
    outcome = "auto_no"
else:
    outcome = "review"
```

## Sizing the band: error target against reviewer hours

Two quantities move together as you widen the band: the error rate on the cases you automate
goes down, and the share of cases sent to people goes up. Measure both on labelled cases from
your own traffic, for candidate pairs of thresholds, and pick the pair that meets your error
target at a review load you can staff.

The table below is illustrative, invented to show the shape of the trade. It is not a
measurement of jevos:

| Auto-no below / auto-yes above | Share sent to review | Errors among automated cases |
|---|---|---|
| 0.5 / 0.5 (no band) | 0 percent | 8.0 percent |
| 0.3 / 0.7 | 12 percent | 4.5 percent |
| 0.2 / 0.85 | 22 percent | 2.5 percent |
| 0.1 / 0.95 | 38 percent | 1.2 percent |

Then translate into hours. With an illustrative 2,000 cases a day and the third row, 440 cases
go to review; at about a minute each, that is more than seven hours of someone's day. If you
have three hours, you need either a narrower band or a better question. Cost asymmetry pulls the
edges further; the arithmetic of that is on
[thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).

## What to log for every decision

The log is what makes the loop a loop. For each case, record:

- a hash of the state (the text or JSON) and the questions asked;
- every P(yes) returned, not only the outcome;
- the thresholds in force and the outcome (auto yes, auto no, review);
- the model name and the model's fingerprint, which `GET /health` reports;
- the inference time from the `Server-Timing` header;
- for reviewed cases, the person's decision and when it was made.

The reviewed cases are your best source of fresh labels, since they are exactly the ones the
model found hard. More on the format is on
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## Why the band is often lopsided

On 999 yes/no questions written after the model was finished, the first jevos made 152 errors by saying yes
when the answer was no, and 91 the other way (not published for jevos-v4). Its no was the more reliable answer. For a band,
that suggests an asymmetric shape: a low edge close to 0.5 is safer than a high edge close to
0.5, so the yes side of the band usually needs to extend further up than the no side extends
down.

The lean is concentrated on questions that need a computation, dates and sums above all. If
most of your review traffic comes from those, the better fix is upstream: compute in code and
ask the model what the text says, as on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md). A band absorbs
uncertainty; it is a poor place to absorb a systematic error.

## Keeping the band honest over time

- **Audit the automated ends.** Send a small random sample of auto-yes and auto-no cases to
  review too. Without it, you only ever see errors in the middle and never learn how wrong the
  confident ends have become.
- **Consider hiding the probability from reviewers.** A reviewer shown "0.83" may simply agree.
  If the purpose is an independent label, show the text and the question, not the number.
- **Re-size when the inputs move.** A new form, a new product line or a seasonal change in the
  mix can fill the band or empty it. Watch the review share daily; a sudden change is a signal.
- **Recompute thresholds from the reviewed cases**, on a schedule, with the same method you used
  to set them, as in [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).

## When a band is not enough

Some decisions should not be automated at either end: where the stakes for the person affected
are high, where a rule or regulation requires a human decision, or where the model cannot read
the answer from the text at all. In those cases use the model to prepare the case (flag,
summarise facts as yes/no answers, order the queue) and let a person decide every one. For the
legal side in the EU, see [GDPR and automated decision-making](gdpr-and-automated-decision-making.md),
which is not legal advice either.

A band also only catches what the model is unsure about. Whether records with a missing fact
actually land in it is measured on
[does an LLM know when a fact is missing?](does-an-llm-know-when-a-fact-is-missing.md).

## Short answers to the questions that lead here

**What is human in the loop AI?** A system where people make or check some of the decisions,
usually the uncertain or high-stakes ones, and their decisions feed back into the system.

**How wide should the review band be?** As wide as your error target requires and your reviewers
can handle, measured on your own labelled cases.

**Should the band be symmetric around 0.5?** Not necessarily. A model that errs toward yes needs
a higher bar on the yes side.

**What should reviewers see?** The text and the question. Showing the probability can anchor
them.

**How do I know the automated decisions are still right?** Sample some of them for review
regularly, and track the error rate over time.

**See also:** [precision and recall at a P(yes) threshold](precision-and-recall-at-a-threshold.md),
[a model cascade: small model first](model-cascade-small-model-first.md) and
[content moderation with a local LLM](content-moderation-with-a-local-llm.md).

## Sources

- Our measurements: 152 wrong yeses vs 91 wrong noes on the 999-question set, first jevos.
  The `/health` fields and the `Server-Timing` header are documented in the
  [jev repository](https://github.com/feder-cr/jev).
- The band table and the reviewer-hours example are illustrative and invented for this page.
- Geifman and El-Yaniv (2017),
  [Selective Classification for Deep Neural Networks](https://arxiv.org/abs/1705.08500),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev). A model fast enough to answer every
case is also fast enough to decide which cases a person should see.*
