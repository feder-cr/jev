---
title: "Reading a reliability diagram"
description: "How to draw a reliability diagram from your own labelled yes/no answers, what over- and under-confidence look like, and how many answers each bin needs."
parent: "Probability and thresholds"
nav_order: 6
---

# Reading a reliability diagram

**A reliability diagram plots, for bins of predicted P(yes), the fraction of cases that were
really yes against the mean prediction in the bin; a calibrated model sits on the diagonal.** A
curve flatter than the diagonal means the model is overconfident, a steeper one means it is
underconfident, and a curve that sits below the diagonal all along means it says yes too
readily. You draw it from your own labelled answers, and you read it together with the number
of answers in each bin, because a point made of eight cases is mostly noise.

It is the most useful single picture of a probability model, because it shows where the
numbers are wrong, not only that they are. One number such as ECE averages the bins away; the
diagram keeps them.

This page is how to draw one from your answers, the shapes to recognise, how many answers each
bin needs, why to draw one per kind of question, and what the diagram does not show.

## How to draw one from your own answers

1. **Collect labelled cases.** A few hundred real texts with the questions you will use in
   production, each answered yes or no by a person who read the text.
2. **Run them and keep every P(yes).** One request per text, one named question per condition.
3. **Bin.** scikit-learn's `calibration_curve` does this: it splits [0, 1] into `n_bins` bins
   (default 5) and returns, per bin, the mean predicted probability and the fraction of
   positives. Bins with no samples are dropped. `strategy="uniform"` gives equal widths;
   `strategy="quantile"` gives each bin the same number of samples.
4. **Plot** the mean prediction on the x-axis and the fraction of yes on the y-axis, with the
   diagonal from (0, 0) to (1, 1) for reference, and a histogram of the counts underneath.

```python
from sklearn.calibration import calibration_curve

frac_yes, mean_p = calibration_curve(y_true, p_yes, n_bins=10, strategy="quantile")
```

`y_true` is 1 where the true answer is yes; `p_yes` holds the probabilities your requests
returned.

## Four shapes and what each means

| What you see | What it means | What usually helps |
|---|---|---|
| points on the diagonal | calibrated on this data | nothing; keep checking |
| curve flatter than the diagonal (low bins above it, high bins below) | overconfident: numbers too close to 0 and 1 | a temperature above 1 |
| curve steeper than the diagonal (low bins below, high bins above) | underconfident: numbers too close to 0.5 | a temperature below 1 |
| curve below the diagonal across the range | says yes too readily at every level | a higher yes threshold, a Platt offset, or better questions |

The last row is worth a second look. Below the diagonal means that among the answers with a
given P(yes), fewer were yes than claimed. If only a few bins sit below, and they are made of one
kind of question, the fix is the question, not a curve. The two corrections in the right-hand
column are on [temperature scaling](temperature-scaling-for-llm-probabilities.md) and
[Platt scaling](platt-scaling-for-a-yes-no-model.md).

Published diagrams make the shapes concrete. The GPT-4 technical report shows two, for the
pre-trained and the post-trained model on a subset of MMLU, with ECEs of 0.007 and 0.074; the
second is visibly further from the diagonal.

## How many answers each bin needs

Guo and colleagues (2017) point out that a reliability diagram does not show how many samples
are in each bin, which hides whether a point is solid evidence. The arithmetic of a proportion
says how much to trust it. With n answers in a bin and a true frequency near p, the standard
error of the observed fraction is about the square root of p(1 - p) / n. For p = 0.8:

| Answers in the bin | Standard error | A point at 0.8 could plausibly be |
|---|---|---|
| 25 | 0.08 | anywhere from about 0.64 to 0.96 |
| 100 | 0.04 | about 0.72 to 0.88 |
| 400 | 0.02 | about 0.76 to 0.84 |

This is textbook arithmetic, not a measurement. It means a 10-point gap in a bin of 25 answers
is not yet evidence of anything, while the same gap in a bin of 400 is. Practical rules:

- Use quantile bins when your probabilities cluster near 0 and 1, which they usually do; equal
  widths leave the middle bins nearly empty.
- With a few hundred answers, use 5 to 10 bins, not 15.
- Always print the count per bin next to the plot.

## Draw one diagram per kind of question

On the natural yes/no questions of our held-out split, the first jevos had a calibration error of
0.009, which means a pooled diagram on that data hugs the diagonal. On 999 new questions,
labelled by the kind of reasoning they need, the first jevos's mean P(yes) on questions whose answer is no
ranged from 0.16 for tone to 0.59 for arithmetic. A pooled diagram of that set mixes a
well-behaved kind with a leaning one. Split by kind, you would expect the arithmetic and date
curves to sit below the diagonal, since their no-answers get an average P(yes) of 0.59 and
0.53, while tone and negation stay much closer to it. These per-kind figures were measured on the first jevos; per-kind numbers for jevos-v4 are not
published. They are on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md), and how to tag
your own questions by kind is on [accuracy by kind of question](accuracy-by-kind-of-question.md).

So tag each labelled case with the kind of question (reading a fact, tone, a date, a sum, a
rule) and draw a diagram per tag once each has enough answers.

## What the diagram does not show

- **Whether the model separates yes from no.** A model that returns 0.5 to everything on a
  half-yes set produces one point, on the diagonal. It is calibrated and useless. Check
  discrimination with [precision and recall at a threshold](precision-and-recall-at-a-threshold.md).
- **Errors that cancel inside a bin.** Two opposite mistakes averaged together look like a
  perfect point.
- **Anything about data you did not label.** The diagram describes the mix of cases you drew it
  from. If production traffic differs, draw it again on production traffic.

## Short answers to the questions that lead here

**What is a reliability diagram?** A plot of observed frequency against predicted probability,
bin by bin, with the diagonal as the calibrated reference.

**What does a point below the diagonal mean?** Among answers with that P(yes), fewer were yes
than predicted: the model overstates yes there.

**How many bins should I use?** With a few hundred labelled answers, 5 to 10, preferably with
equal counts per bin.

**Is a calibration curve the same as a reliability diagram?** Yes, the two names are used for
the same plot; scikit-learn calls it a calibration curve.

**Can a model be on the diagonal and still bad?** Yes. Calibration says the numbers are honest,
not that they are sharp.

**See also:** [expected calibration error, explained](expected-calibration-error-explained.md),
[LLM calibration explained](llm-calibration-explained.md) and
[building a yes/no test set](building-a-yes-no-test-set.md).

## Sources

- Our measurements: calibration error 0.009 on 6,397 natural yes/no held-out questions
  (first jevos); mean P(yes) on no-answer questions by kind, 999-question set (first jevos).
- The standard-error table is arithmetic for illustration, not a measurement.
- [scikit-learn calibration_curve](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html)
  and [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html),
  fetched 2026-09-29.
- Guo, Pleiss, Sun, Weinberger (2017),
  [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), fetched
  2026-09-29.
- OpenAI (2023), [GPT-4 Technical Report](https://arxiv.org/abs/2303.08774), Figure 8, fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where, on the first jevos, a pooled calibration error of
0.009 did not predict the yes-lean on new kinds of question, which is why this page insists on
splitting by kind.*
