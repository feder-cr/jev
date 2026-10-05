---
title: "Temperature scaling for LLM probabilities"
description: "Temperature scaling divides a logit by T to fix over- or under-confidence. What it repairs, what it cannot, and why it moved us from 0.757 to 0.759."
parent: "Probability and thresholds"
nav_order: 4
---

# Temperature scaling for LLM probabilities

**Temperature scaling recalibrates a model by dividing its logit by a single number T before
turning it back into a probability: T above 1 pulls answers toward 0.5, T below 1 pushes them
toward 0 and 1.** T is fitted on held-out labelled cases by minimising log loss, and because it
never moves an answer across 0.5, it changes how confident the model looks without changing
which answer it gives. It fixes a model that is uniformly too sure or too shy. It cannot fix a
model that leans in one direction on some kinds of question.

That second sentence is the reason for this page. When we fitted a temperature and a bias on
our development split (first jevos) and applied them to 999 new questions, accuracy moved from 0.757 to
0.759. The model's problem on those questions was not its confidence level; it was a lean
toward yes on questions it could not compute, and a global correction cannot reach that.

This page is the mechanism for a single yes/no probability, where the method comes from, what it
repairs, what it cannot, and whether to apply it to your own answers.

## How it works for one yes/no probability

A logit is the log-odds of the probability, z = log(p / (1 - p)). Temperature scaling replaces
p with sigmoid(z / T). For a yes/no answer this has a neat form: the odds are raised to the
power 1/T.

A worked example with illustrative numbers. Take P(yes) = 0.9, odds 9 to 1:

| T | New odds | New P(yes) |
|---|---|---|
| 0.5 | 81 to 1 | 0.988 |
| 1 | 9 to 1 | 0.9 (unchanged) |
| 2 | 3 to 1 | 0.75 |
| 4 | about 1.73 to 1 | about 0.63 |

A P(yes) of 0.5 stays 0.5 for every T, and a 0.1 moves exactly as far toward or away from 0.5 as
the 0.9 does. That symmetry is what makes the method safe, and also what limits it. The logit
scale itself is explained on [logits, log-odds and P(yes)](logits-log-odds-and-p-yes.md).

## Where the method comes from

Guo and colleagues (2017) found that modern neural networks are poorly calibrated, compared
several post-processing fixes, and concluded that on most datasets temperature scaling, "a
single-parameter variant of Platt Scaling", is surprisingly effective. scikit-learn's
documentation describes the same method for multiclass problems: T is learned by minimising log
loss on a hold-out calibration set, and since it does not move the maximum of the softmax, it
does not alter accuracy.

The relative with one more parameter is [Platt scaling](platt-scaling-for-a-yes-no-model.md),
which also fits an offset. That offset can move answers across 0.5, which is exactly the part
that can change accuracy.

## What it repairs

- **Uniform overconfidence.** If the model's 0.95s are right 85 percent of the time and its
  0.05s are yes 15 percent of the time, a T above 1 pulls both in.
- **Uniform underconfidence.** If the 0.7s are right 90 percent of the time, a T below 1 pushes
  them out.
- **Probabilities you want to use as probabilities.** Expected-cost thresholds and averages
  over a batch need calibrated numbers; see
  [thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).

In every one of these cases, a [reliability diagram](reading-a-reliability-diagram.md) of your
labelled answers shows the shape first: a curve flatter than the diagonal for overconfidence,
steeper for underconfidence.

## What it cannot repair: a lean in one direction

On 999 yes/no questions written after the model was finished, the first jevos made 152 errors
saying yes when the answer was no and 91 the other way. The lean is not spread evenly: the mean
P(yes) on questions whose answer is no is 0.59 for arithmetic and 0.53 for dates, but 0.17 for
negation and 0.16 for tone.

These per-kind numbers were measured on the first jevos; per-kind numbers for jevos-v4 (78.9%
overall on the same 999 questions) are not published. A temperature cannot fix that, because it treats a wrong 0.7 on a sum and a right 0.7 on a
fact the same way. A bias term shifts every answer at once, so a shift large enough to fix the
sums starts saying no to facts the model had right. What we measured:

| Correction | Accuracy on the 999 questions |
|---|---|
| none (first jevos) | 0.757 |
| temperature and bias fitted on dev | 0.759 |
| best bias chosen on the 999 set itself (cheating on purpose) | 0.763 |
| fitted on half the scenarios, tested on the other half | no gain |

The cheating row is the ceiling of what any global shift could recover: 0.006. The fix for a
directional error lives in the question, not the probability: keep arithmetic and dates in code
and ask the model what it reads, as described in
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

## Should you apply it to your own answers?

Only if your own labelled cases show a uniform miscalibration, and only with care:

- Fit T on cases that you do not then use to judge it. scikit-learn's guidance for calibrators
  in general is to fit them on data independent of what the model was fitted on, and the same
  logic applies to your test set.
- Fit it per question or per kind of question if they behave differently. One T for a fact
  question and a date question averages two different problems.
- Refit when the inputs change. A temperature fitted on last quarter's tickets describes last
  quarter's tickets.

A minimal fit by grid search, on labelled P(yes) values `p` and answers `y` (1 for yes):

```python
import numpy as np

z = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
def log_loss(T):
    q = 1 / (1 + np.exp(-z / T))
    return -np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))
T = min(np.linspace(0.25, 4, 76), key=log_loss)
```

If the best T comes out near 1, the model was already calibrated on that data, and the answer is
to leave it alone.

## Short answers to the questions that lead here

**What is temperature scaling?** Dividing a model's logits by a fitted number T before the
sigmoid or softmax, to make its probabilities match observed frequencies.

**Does temperature scaling change accuracy?** Not on its own: it never moves an answer across
0.5. Adding a bias term, as in Platt scaling, can.

**Is this the same temperature as in text generation?** It is the same operation on logits, used
for a different purpose: sampling diversity there, calibration here.

**Why did recalibration not help jevos on new questions?** Because the errors were a lean toward
yes on specific kinds of question, not a uniform overconfidence.

**How many labelled cases do I need to fit T?** One parameter is cheap to fit; a few hundred
labelled cases is a reasonable start, and more if you fit per kind of question.

**See also:** [expected calibration error, explained](expected-calibration-error-explained.md),
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md) and
[LLM calibration explained](llm-calibration-explained.md).

## Sources

- Our measurements: the 999-question set on the first jevos, `jevos-q4_k_m` (accuracy, 152 vs
  91 errors, mean P(yes) by kind) and the recalibration experiments on it.
- The T table is illustrative arithmetic, not a measurement.
- Guo, Pleiss, Sun, Weinberger (2017),
  [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), fetched
  2026-09-29.
- [scikit-learn, Probability calibration](https://scikit-learn.org/stable/modules/calibration.html),
  temperature scaling and independent calibration data, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev). We tried the textbook fix on our own
weakness, it moved accuracy by two thousandths, and we wrote down why.*
