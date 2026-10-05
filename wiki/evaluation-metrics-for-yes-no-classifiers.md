---
title: "Evaluation metrics for yes/no classifiers"
description: "Which metrics to report for a yes/no classifier or LLM: accuracy, precision and recall, accuracy per kind, error direction, calibration and uncertainty."
parent: "Evaluation"
nav_order: 8
---

# Evaluation metrics for yes/no classifiers

**For a yes/no classifier that returns a probability, report at least four things: accuracy per
kind of question, the split between wrong yeses and wrong noes, precision and recall at the
threshold you will actually use, and a calibration measure.** Each one answers a different
question, and each one can look fine while another is bad. Add an uncertainty range to every
number computed on fewer than a few hundred cases.

The trap is the single accuracy figure. On our 999 hand-written questions the first jevos scored 0.757 overall,
which describes no real use: the same model was right 0.954 of the time on stated facts and
0.584 on arithmetic, and when it was wrong it was wrong toward yes five times out of eight.

This page is the confusion matrix every metric comes from, a table of which metric answers which
question, the three reports people most often skip, threshold-free scores, and how much a number
on a small set can be trusted.

## Every metric starts from the same four counts

With a threshold (say P(yes) above 0.5 means yes), every answer falls in one of four cells. An
illustrative example, not a measurement, for 200 cases with 100 of each answer:

| | answer is yes | answer is no |
|---|---|---|
| model says yes | 85 (true yes) | 30 (wrong yes) |
| model says no | 15 (wrong no) | 70 (true no) |

From these four numbers:

- **accuracy** = (85 + 70) / 200 = 0.775: share of answers that are right.
- **precision** = 85 / (85 + 30) = 0.74: of the yeses, how many were right.
- **recall** = 85 / (85 + 15) = 0.85: of the real yeses, how many were found.
- **specificity** = 70 / (70 + 30) = 0.70: of the real noes, how many were kept as no.

Move the threshold and all four cells change. That trade is worth a page of its own:
[precision and recall at a P(yes) threshold](precision-and-recall-at-a-threshold.md).

## Which metric answers which question?

| You want to know | Report |
|---|---|
| how often is it right overall, on this mix | accuracy |
| when it says yes, can I act on it | precision |
| does it find the cases I care about | recall |
| which kinds of question can I trust it with | accuracy per kind |
| which way does it fail | wrong yes vs wrong no counts |
| can I read 0.8 as "about 80% likely" | calibration error, reliability diagram |
| how good is it before I pick a threshold | log loss, Brier score, ROC AUC |
| how much would the number move on another sample | a confidence interval |

## Accuracy per kind: the report that changes decisions

Tag every test question with the reasoning it needs (stated fact, tone, negation, rule, number,
date, arithmetic) and report accuracy for each tag. On our set the spread runs, on the first jevos, from 0.954 to
0.584 (per-kind numbers for jevos-v4 are not published; its overall figure is 78.9%), and the line between reading and computing is sharp. That split decides what you route to
the model and what you keep in code, which one overall number never can. How to design the tags
is on [accuracy by kind of question](accuracy-by-kind-of-question.md).

## Error direction: the report nobody asks for

Accuracy treats a wrong yes and a wrong no as equal. Applications almost never do: a wrong yes
might refund a fraudster, a wrong no might ignore an urgent ticket. So count them separately.

On our 999 questions, half yes and half no, the first jevos made 152 wrong yeses and 91 wrong noes. On a
balanced set, an unbiased model would split its errors roughly evenly. A clearer view is the mean
P(yes) on questions whose answer is no, per kind: 0.59 on arithmetic, 0.16 on tone. The details
are on [why a small LLM says yes](why-a-small-llm-says-yes.md). If you report only accuracy, this
is invisible.

## Calibration: can the probability be read as a probability?

A calibrated model's answers of about 0.8 are right about 80% of the time. The usual summary is
the expected calibration error (ECE), the weighted average gap between confidence and accuracy
across bins. On the natural yes/no questions of our held-out split an earlier jevos had an ECE of 0.009, and
that number did not predict the lean toward yes on new kinds of question, which is why calibration
belongs next to per-kind accuracy and not in place of it. The definition and a worked example are
on [expected calibration error, explained](expected-calibration-error-explained.md); drawing the
picture is on [reading a reliability diagram](reading-a-reliability-diagram.md).

## Scores that need no threshold

When you have not picked a threshold yet, or want to compare two models independently of one,
use the probabilities directly:

- **Log loss**: the mean of minus the log of the probability given to the right answer. It
  punishes confident mistakes hard: on a case whose answer is no, a P(yes) of 0.99 costs about
  4.6, a P(yes) of 0.6 about 0.9, and a P(yes) of 0.1 about 0.1.
- **Brier score**: the mean squared gap between the probability and the answer (1 or 0). Easier to
  read than log loss, gentler on confident mistakes.
- **ROC AUC**: the probability that a random yes case gets a higher P(yes) than a random no case.
  It measures ranking only, so a model can have a good AUC and be badly calibrated.

These are good for comparing builds or prompts. They are poor for explaining results to people who
will act on thresholds; there, the confusion matrix at the chosen threshold is clearer.

## How much can I trust a number on a small set?

Less than it looks. A rough 95% interval for an accuracy `p` on `n` cases is plus or minus
`1.96 * sqrt(p * (1 - p) / n)`.

- 0.8 on 100 cases: about plus or minus 0.08.
- our arithmetic kind, 0.584 on 221 questions: about plus or minus 0.065.
- our tone kind, 0.938 on 32 questions: about plus or minus 0.08, and the formula is optimistic
  this close to 1.

So a per-kind accuracy on 30 questions tells you "high" or "low", not the second decimal, and a
difference of a few points between two prompts on 100 cases is usually noise. More cases per kind
is the fix; generated questions with computed answers are the cheap way to get them, described on
[generating test questions with answers computed by code](generating-test-questions-with-code.md).

## Short answers to the questions that lead here

**What metrics should I use for a binary classifier?** Accuracy per kind, error direction,
precision and recall at your threshold, and a calibration measure, each with an uncertainty range.

**Is accuracy enough?** No. Our overall 0.757 for the first jevos hid a range from 0.954 to 0.584 and a lean toward
wrong yeses.

**What is the difference between precision and recall?** Precision is the share of predicted yeses
that are right; recall is the share of real yeses that were found.

**When should I use log loss or AUC?** To compare models or prompts before choosing a threshold.
Once a threshold is set, report the confusion matrix at it.

**How many test cases do I need?** Enough per kind that the interval is narrower than the
differences you care about. About 100 gives plus or minus 8 points.

**See also:** [building a yes/no test set for your own data](building-a-yes-no-test-set.md),
[LLM calibration explained with yes/no answers](llm-calibration-explained.md) and
[our held-out benchmark said 0.855, new questions said 0.757](held-out-benchmark-too-optimistic.md).

## Sources

- Overall and per-kind accuracy, error counts and mean P(yes) on no-answer questions: our
  999 hand-written questions, measured on the first jevos.
- Calibration error 0.009: our held-out split, 6,397 natural yes/no questions, measured on an
  earlier jevos.
- The confusion matrix and the log-loss examples are illustrative arithmetic, not measurements.
  The interval formula is the standard normal approximation for a proportion.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which returns a probability rather than
a label, so every metric on this page can be computed from its answers.*
