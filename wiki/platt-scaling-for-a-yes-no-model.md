---
title: "Platt scaling for a yes/no model"
description: "Platt scaling fits a logistic curve to a model's scores on labelled cases: how it relates to temperature scaling and when to fit it on your own answers."
parent: "Probability and thresholds"
nav_order: 5
---

# Platt scaling for a yes/no model

**Platt scaling maps a model's score to a calibrated probability with a logistic curve,
P = 1 / (1 + exp(A f + B)), where f is the score and A and B are fitted on labelled cases by
maximum likelihood.** For a yes/no model, the natural f is the logit of P(yes). A rescales it,
like a temperature, and B shifts it, like a bias. Fit it on your own labelled cases when you
need the probabilities to match your data's frequencies, for example to compute expected cost
or to average answers; if you only need a yes/no cut-off, choosing the threshold directly does
the same job.

The offset B is what makes Platt scaling different from temperature scaling. It can move an
answer from one side of 0.5 to the other, so it can change accuracy, for better or worse. That
is useful when the model is shifted uniformly, and harmful when it is shifted only on some kinds
of question.

This page is the fit in one line, how it relates to temperature scaling, when it is worth doing
on your cases, how much data it needs, and a short scikit-learn sketch.

## The fit in one line

scikit-learn describes the sigmoid method as p(y = 1 | f) = 1 / (1 + exp(A f + B)), with f the
uncalibrated output and A and B determined by maximum likelihood. Guo and colleagues (2017) write
the same thing as q = sigma(a z + b), with a and b fitted on a validation set by minimising
negative log-likelihood. The two notations differ only in sign convention.

In practice this is a logistic regression with one input. You give it one feature per labelled
case, the logit of the P(yes) the model returned, and the true answer. What it learns is a
straight line on the logit scale, which becomes an S-curve on the probability scale; the scale
is explained on [logits, log-odds and P(yes)](logits-log-odds-and-p-yes.md).

## Platt scaling and temperature scaling

Guo and colleagues call temperature scaling "a single-parameter variant of Platt Scaling". The
relation is exact for a yes/no logit:

- **Temperature scaling** fixes B at 0 and fits only the slope. It pulls answers toward 0.5 or
  pushes them away, symmetrically, and never flips one.
- **Platt scaling** fits both. The slope does what the temperature does; the offset moves the
  point where the calibrated probability crosses 0.5.

So Platt can correct a model that says yes too readily across the board, which temperature
cannot. The risk is the other side of the same coin: a uniform shift fitted on data dominated by
one kind of question moves every other kind too. The mechanics of the one-parameter version are
on [temperature scaling for LLM probabilities](temperature-scaling-for-llm-probabilities.md).

## When fitting it on your own cases is worth it

Worth it when:

- **You use the number as a probability.** Expected-cost rules, averages over a batch, products
  for AND, and review bands sized in probability all assume calibration; see
  [combining yes/no answers](combining-yes-no-answers-and-or-not.md).
- **Your reliability diagram shows one smooth distortion.** A curve that is flatter or steeper
  than the diagonal, or sits uniformly above or below it, is what a two-parameter logistic can
  straighten.
- **Your base rate differs from the data the model was checked on.** The offset absorbs a
  change in how common yes is, as long as you refit when the mix changes; see
  [base rates](base-rates-and-yes-no-predictions.md).

Not worth it when:

- **You only threshold.** Platt scaling with a negative A is strictly increasing, so it keeps
  the order of the cases. Any cut-off on the calibrated scale corresponds to a cut-off on the
  raw scale. Choosing that raw cut-off from your labelled cases, as in
  [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md), gives the same
  decisions with one less model to maintain.
- **The error is a lean on specific kinds of question.** On our 999 new questions, with the first jevos, a
  temperature and bias fitted on the development split moved accuracy from 0.757 to 0.759; fitted
  on half the scenarios and tested on the other half, there was no gain. The lean lived in
  arithmetic and dates, not in the whole distribution.

## How much data, and which data

scikit-learn's guidance is that the sigmoid method is most effective for small sample sizes, and
that the non-parametric alternative, isotonic regression, performs as well or better only when
there is enough data (more than about 1,000 samples) to avoid overfitting. It also warns that a
calibrator should be fitted on data independent of the data used to fit the classifier, or it
learns probabilities closer to 0 and 1 than it should.

For a yes/no model you did not train, the translation is:

- Fit on labelled cases from your own traffic, not on the cases you will later report results
  on. Keep a separate split for the evaluation.
- Fit per question, or per kind of question, when they behave differently.
- A few hundred cases is enough for two parameters; more if you fit per kind.
- Refit when the inputs change: a new form, a new customer segment, a reworded question, a new
  model file.

## A sketch with scikit-learn

Assume `p` holds the P(yes) values your labelled requests returned and `y` the true answers, 1
for yes. This is a sketch, not code we ship:

```python
import numpy as np
from sklearn.linear_model import LogisticRegression

def logit(p):
    p = np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)

platt = LogisticRegression(C=np.inf).fit(logit(p_fit), y_fit)
p_calibrated = platt.predict_proba(logit(p_new))[:, 1]
```

`C=np.inf` turns off regularisation, which scikit-learn documents as unpenalised logistic
regression; with only two parameters and a few hundred cases, that is usually what you want.
Fit on one split (`p_fit`, `y_fit`), then compare the reliability diagram of a held-back split
before and after; if it did not improve there, drop the calibrator.

## Short answers to the questions that lead here

**What is Platt scaling?** A logistic regression fitted on a model's scores and the true labels,
used to turn the scores into calibrated probabilities.

**Is Platt scaling the same as temperature scaling?** Temperature scaling is Platt scaling
without the offset. The offset lets Platt shift the 0.5 point.

**Does Platt scaling change accuracy?** It can, through the offset. Temperature scaling alone
does not.

**Should I use isotonic regression instead?** With more than about 1,000 labelled cases it can
do as well or better; with fewer, it overfits more easily than the sigmoid.

**Can Platt scaling fix a yes-lean on arithmetic questions?** Not without hurting the questions
that were right. Move the arithmetic into code instead.

**See also:** [LLM calibration explained](llm-calibration-explained.md),
[reading a reliability diagram](reading-a-reliability-diagram.md) and
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Sources

- Our measurements: the recalibration experiments on the 999-question set, with the first jevos
  (0.757 as shipped, 0.759 with temperature and bias fitted on dev, no gain across scenario
  halves).
- [scikit-learn, Probability calibration](https://scikit-learn.org/stable/modules/calibration.html):
  sigmoid formula, small-sample guidance, isotonic above about 1,000 samples, independent
  calibration data, fetched 2026-09-29.
- [scikit-learn LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html),
  `C=np.inf` for unpenalised fits, fetched 2026-09-29.
- Guo, Pleiss, Sun, Weinberger (2017),
  [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose answers are probabilities
you can refit on your own labels without touching the model file.*
