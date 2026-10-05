---
title: "Expected calibration error (ECE), explained"
description: "How expected calibration error is computed from bins, a worked example with illustrative numbers, and the limits that make one ECE value easy to over-read."
parent: "Probability and thresholds"
nav_order: 3
---

# Expected calibration error (ECE), explained

**Expected calibration error is the average gap between what a model's probabilities claim and
how often they come true, computed over bins and weighted by how many answers fall in each
bin.** Sort the answers into bins by probability, take the absolute difference between each
bin's mean prediction and its observed frequency, and average those differences weighted by bin
size. Zero means the numbers match the frequencies; 0.05 means that, on average, the claim is
off by about five percentage points.

It is the most reported calibration number and one of the easiest to over-read. It depends on
the number of bins, it can hide errors that cancel inside a bin, and it describes one mix of
data. A low ECE is necessary for trusting probabilities, not sufficient.

This page is the definition, a worked example with made-up numbers, the two conventions you
will meet for yes/no models, a short piece of code, and the limits.

## The definition

Guo and colleagues (2017) give the form most papers use. Split the n predictions into M bins
B_1 to B_M by predicted confidence. For each bin, compute acc(B_m), the fraction of answers in
the bin that were right, and conf(B_m), the mean predicted confidence. Then:

ECE = sum over m of (|B_m| / n) times |acc(B_m) - conf(B_m)|

The related maximum calibration error (MCE) is the largest of those per-bin gaps instead of the
weighted average. Guo and colleagues used M = 15 bins in their experiments; scikit-learn's
`calibration_curve` defaults to 5.

## Two conventions for a yes/no model

For a model that returns P(yes), you can bin in two ways, and they give different numbers:

- **On P(yes) against the fraction of yes.** Bins run from 0 to 1 on P(yes), and each bin's
  mean P(yes) is compared with the share of its cases whose true answer is yes. This is what a
  reliability diagram of a binary classifier in scikit-learn plots.
- **On confidence against accuracy.** Confidence is max(P(yes), 1 - P(yes)), the probability
  of the answer the model would give; bins run from 0.5 to 1; each bin's mean confidence is
  compared with how often that answer was right. This is the multiclass form applied to two
  classes.

Neither is wrong. When you compare an ECE you computed with one someone else published, check
the convention and the number of bins before comparing the values.

## A worked example (illustrative numbers)

The table below is made up to show the arithmetic. It is not a measurement of jevos or of any
model. Imagine 200 labelled answers binned on P(yes) into 5 equal bins:

| Bin of P(yes) | Answers | Mean P(yes) | Fraction really yes | Gap |
|---|---|---|---|---|
| 0.0 to 0.2 | 60 | 0.08 | 0.05 (3 of 60) | 0.03 |
| 0.2 to 0.4 | 30 | 0.30 | 0.20 (6 of 30) | 0.10 |
| 0.4 to 0.6 | 20 | 0.50 | 0.45 (9 of 20) | 0.05 |
| 0.6 to 0.8 | 30 | 0.70 | 0.60 (18 of 30) | 0.10 |
| 0.8 to 1.0 | 60 | 0.92 | 0.95 (57 of 60) | 0.03 |

Weighted sum: (60 times 0.03 + 30 times 0.10 + 20 times 0.05 + 30 times 0.10 + 60 times 0.03)
/ 200 = 10.6 / 200 = 0.053. The MCE is 0.10.

Reading it: this illustrative model is fine at the extremes and too eager in the middle, where
its 0.3s and 0.7s both overstate yes by ten points. The ECE of 0.053 says "something is off";
only the per-bin table says where. On a [reliability diagram](reading-a-reliability-diagram.md)
those two middle bins would sit below the diagonal.

## Computing it on your own answers

With the probabilities from your labelled requests in `p` and the true answers (1 for yes) in
`y`:

```python
import numpy as np

def ece(p, y, bins=10):
    p, y = np.asarray(p), np.asarray(y)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.mean() * abs(p[m].mean() - y[m].mean())
    return total
```

This is the first convention above, with equal-width bins. Print the per-bin counts too: a bin
of four answers contributes noise, not evidence.

## The limits of ECE

- **It depends on the bins.** Nixon and colleagues (2019) show that conclusions, including the
  ranking of recalibration methods, change with the calibration measure and the number of bins,
  and that adaptive bins with equal counts are more stable than fixed ones.
- **Errors can cancel inside a bin.** If half a bin is overconfident and half underconfident,
  the bin's mean looks perfect.
- **It says nothing about accuracy.** A model that answers 0.5 to everything on a half-yes set
  has an ECE of zero.
- **It describes one mix of data.** On the natural yes/no questions of our held-out split, an
  earlier jevos had an ECE of 0.009. On 999 new questions, the first jevos gave a mean P(yes) of
  0.59 to arithmetic questions whose answer was no. Both are true; the first does not predict
  the second.
  Compute ECE per kind of question, as on
  [accuracy by kind of question](accuracy-by-kind-of-question.md).
- **Small samples inflate or deflate it.** With 200 answers and 15 bins, several bins hold a
  handful of cases. Use fewer bins, or equal-count bins, when data is scarce.

## Short answers to the questions that lead here

**What is a good ECE?** It depends on the data and the binning, but values of a few hundredths
mean the probabilities are close to the frequencies on that data. Always look at the per-bin
table too.

**How many bins should I use?** With a few hundred answers, 5 to 10. Guo and colleagues used 15
on much larger sets.

**Is ECE the same as the Brier score?** No. The Brier score is the mean squared difference
between P(yes) and the 0/1 answer, so it scores the whole probability, not calibration alone: a
model that always says 0.5 has an ECE of zero on half-yes data but a Brier score of 0.25.

**Does a low ECE mean the model is accurate?** No. A model that always says 0.5 on balanced data
has an ECE of zero.

**What ECE does jevos have?** An earlier jevos had 0.009 on 6,397 natural yes/no held-out
questions and 0.018 on the dev split; the ECE of jevos-v4 is not published. On new kinds of
question the first jevos leaned toward yes, which those numbers do not show.

**See also:** [LLM calibration explained](llm-calibration-explained.md),
[temperature scaling for LLM probabilities](temperature-scaling-for-llm-probabilities.md) and
[evaluation metrics for yes/no classifiers](evaluation-metrics-for-yes-no-classifiers.md).

## Sources

- Our measurements on earlier jevos versions, not remeasured for jevos-v4: ECE 0.009 (held-out,
  6,397 natural yes/no questions) and 0.018 (dev); mean P(yes) 0.59 on no-answer arithmetic
  questions, 999-question set, first jevos.
- The worked example table is illustrative and invented for this page.
- Guo, Pleiss, Sun, Weinberger (2017),
  [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599): ECE and MCE
  definitions, M = 15, fetched 2026-09-29.
- Nixon et al. (2019), [Measuring Calibration in Deep Learning](https://arxiv.org/abs/1904.01685),
  fetched 2026-09-29.
- [scikit-learn calibration_curve](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html),
  default of 5 bins, and
  [brier_score_loss](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where the same model has an ECE of
0.009 on one test set and a clear yes-lean on another.*
