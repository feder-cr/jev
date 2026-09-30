---
title: "Logits, log-odds and P(yes)"
description: "What a logit is, how the sigmoid turns it back into P(yes), and why shifting, scaling and averaging are easier and safer on the log-odds scale."
parent: "Probability and thresholds"
nav_order: 13
---

# Logits, log-odds and P(yes)

**A logit is the log of the odds, log(p / (1 - p)): it is 0 at a P(yes) of 0.5, positive for
yes, negative for no, and runs from minus to plus infinity; the sigmoid, 1 / (1 + e to the
minus z), turns it back into a probability.** Log-odds are the natural scale for working with
yes/no probabilities, because adding to a logit multiplies the odds, which behaves sensibly
near 0 and 1 where probabilities bunch up. Shifts, temperatures, base-rate corrections and
evidence from several sources are all simple additions or multiplications there.

You can compute a logit from any P(yes) a model returns, with one line of code. This page is
about that arithmetic on the number you get back, not about how any particular model computes
its number internally.

This page is the conversion both ways with a table, why shifts belong on the logit scale, the
choice between averaging probabilities and averaging logits, adding evidence, and the numerical
care the conversion needs.

## From probability to log-odds and back

Wikipedia gives the definitions: logit(p) = ln(p / (1 - p)) for p between 0 and 1, and its
inverse, the logistic function, 1 / (1 + e to the minus alpha). With the natural logarithm the
unit is the nat; base 2 would give bits.

| P(yes) | Odds | Logit (nats) |
|---|---|---|
| 0.01 | 1 to 99 | -4.60 |
| 0.10 | 1 to 9 | -2.20 |
| 0.50 | 1 to 1 | 0 |
| 0.83 | 4.9 to 1 | 1.59 |
| 0.90 | 9 to 1 | 2.20 |
| 0.93 | 13.3 to 1 | 2.59 |
| 0.95 | 19 to 1 | 2.94 |
| 0.99 | 99 to 1 | 4.60 |
| 0.999 | 999 to 1 | 6.91 |

Two things stand out. The scale is symmetric: 0.1 and 0.9 are the same distance from 0.5, in
opposite directions. And it stretches the ends: going from 0.9 to 0.99 is a step of 2.4 nats,
larger than going from 0.5 to 0.9. In probability terms that step looks like 0.09; in terms of
how often you would be wrong, it is the difference between one in ten and one in a hundred.

## Why shifts belong on the logit scale

Suppose you want to make a question slightly harder to answer yes, because the model leans
toward yes on it. Subtracting 0.05 from every P(yes) breaks at the edges: 0.03 would become
negative. Subtracting a constant from the logit cannot break, because every logit maps back to
a probability between 0 and 1.

Adding 1 nat to a logit multiplies the odds by e, about 2.72. On illustrative inputs:

| Before | After adding 1 nat |
|---|---|
| 0.50 | 0.73 |
| 0.90 | 0.96 |
| 0.99 | 0.996 |

The move is large in the middle and small near the ends, which is what an uncertain case and a
near-certain case should get. The two standard recalibration methods are exactly these
operations: [temperature scaling](temperature-scaling-for-llm-probabilities.md) divides the
logit by a number, and [Platt scaling](platt-scaling-for-a-yes-no-model.md) multiplies it and
adds a constant.

## Averaging: probabilities or logits?

Say you ask the same question in three phrasings, to check how stable the answer is, and get an
illustrative 0.6, 0.9 and 0.99.

- **Mean of probabilities**: (0.6 + 0.9 + 0.99) / 3 = 0.83.
- **Mean of logits**: (0.41 + 2.20 + 4.60) / 3 = 2.40, which maps back to 0.92.

The logit mean, which is the geometric mean of the odds, lets a very confident answer pull the
result further; the probability mean is more conservative. Neither is right by default. If the
phrasings disagree this much, the more useful conclusion is that the question is unstable, which
is what [why wording changes an LLM's answer](why-wording-changes-the-answer.md) is about. If you
do average, choose the method on labelled cases, with a reliability diagram of each.

## Adding evidence

Log-odds make combining evidence an addition. Wikipedia notes that log-odds can simply be summed
where probabilities would have to be multiplied. The pattern shows up in two places:

- **A base-rate correction.** If the share of yes in your traffic differs from the data a
  probability was calibrated on, and only the proportions changed, add log(new prior odds) minus
  log(old prior odds) to the logit. The worked example is on
  [base rates: why a 0.9 yes can still be wrong often](base-rates-and-yes-no-predictions.md).
- **Independent signals.** A model's answer and, say, a sender-reputation score can be combined
  by adding their log-likelihood ratios to a prior, as long as they are independent given the
  answer. For questions about the same text they usually are not, so treat the sum as an upper
  bound on confidence, and read [combining yes/no answers](combining-yes-no-answers-and-or-not.md)
  for the safer logical forms.

## Numerical care

The conversion has two edges that need handling in code:

```python
import math

def logit(p, eps=1e-6):
    p = min(max(p, eps), 1 - eps)
    return math.log(p / (1 - p))

def sigmoid(z):
    return 1 / (1 + math.exp(-z))
```

Clipping keeps a P(yes) of exactly 0 or 1 from producing an infinite logit. The value of `eps`
decides how far out the ends go (1e-6 caps a logit at about 13.8 nats); pick it once and use it
everywhere, or two parts of your code will disagree on the same answer. For very negative `z`,
`math.exp(-z)` can overflow; a production sigmoid branches on the sign of `z`.

## Short answers to the questions that lead here

**What is a logit?** The log of the odds of a probability, log(p / (1 - p)). It is 0 at 0.5.

**What is the difference between a logit and a probability?** The same information on a
different scale: probability runs from 0 to 1, the logit from minus to plus infinity.

**Why do calibration methods work on logits?** Because shifting or scaling a logit always gives
a valid probability, and it moves uncertain answers more than near-certain ones.

**Should I average P(yes) values or logits?** Either can be right; logit averaging favours
confident answers. Decide on labelled cases.

**Does jevos expose logits?** The documented answer is P(yes), as `noul`; you can convert that
to a logit yourself with the formula above.

**See also:** [what P(yes) means](what-p-yes-means.md),
[expected calibration error, explained](expected-calibration-error-explained.md) and
[thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).

## Sources

- All tables on this page are arithmetic, and the three-phrasing and shift examples are
  illustrative. The values 0.83 and 0.93 in the first table are the README's `upset` and
  `refund` examples in the [jev repository](https://github.com/feder-cr/jev).
- [Logit](https://en.wikipedia.org/wiki/Logit) on Wikipedia, as a secondary pointer for the
  definition, units and additivity of log-odds, fetched 2026-09-29.
- Temperature and Platt scaling as operations on logits: Guo, Pleiss, Sun, Weinberger (2017),
  [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which hands you a probability per
question; everything on this page is what you can do with it afterwards.*
