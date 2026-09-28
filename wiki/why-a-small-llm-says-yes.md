---
title: "Why a small LLM says yes when the answer is no"
description: "On 999 new yes/no questions, a 1B LLM gave 152 wrong yeses and 91 wrong noes. Where the yes-bias lives, and why recalibrating does not fix it."
parent: "Measurements"
nav_order: 1
---

# Why a small LLM says yes when the answer is no

**A small language model asked yes/no questions it cannot work out does not answer at random:
it leans toward yes.** On 999 questions written after training, half with the answer yes and
half no, jevos made 152 mistakes by saying yes when the answer was no, and 91 by saying no when
it was yes. The lean is not spread evenly. It sits almost entirely on questions that need a
computation, dates and sums, and on those the average P(yes) for a question whose answer is no
is above one half.

And it is not a threshold problem. Moving the cut-off from 0.5, or recalibrating the
probabilities, recovers almost nothing, because the model is not uncertain on those questions:
it is wrong in a consistent direction.

This page is the measurement, where the bias lives, the recalibration that did not work, and
what to do about it in an application.

## The test set

999 yes/no questions written from scratch after the model was finished: 10 scenarios, 10 texts
per scenario of 40 to 150 words (emails, tickets, logs, reviews, forms), 10 questions per
text. Each question is labelled with the kind of reasoning it needs, and exactly
half of the answers are yes. Nothing in the set was used to tune anything.

On it, `jevos-q4_k_m` is right 0.757 of the time.

## The errors are not symmetric

| | count |
|---|---|
| said yes, answer was no | **152** |
| said no, answer was yes | 91 |

With a balanced set, an unbiased model would split its mistakes roughly evenly. A 152 to 91
split means that when the model is wrong, it is wrong toward yes five times out of eight.

## Where the yes lives

The clearest view is the average probability the model gives to "yes" on questions whose answer
is no. For an ideal model it is 0; for a coin, 0.5.

| Kind of question | Accuracy | Mean P(yes) when the answer is no |
|---|---|---|
| arithmetic | 0.584 | **0.59** |
| dates and durations | 0.598 | **0.53** |
| paraphrase | 0.893 | 0.39 |
| number against a threshold | 0.654 | 0.34 |
| applying a rule | 0.721 | 0.31 |
| stated fact | 0.954 | 0.29 |
| intent | 0.859 | 0.28 |
| not stated in the text | 0.847 | 0.23 |
| negation | 0.858 | 0.17 |
| tone | 0.938 | 0.16 |

On arithmetic and on dates the model gives a no-answer question a probability of yes above one
half, on average. Those two kinds are 318 of the 999 questions and they carry most of the bias.
On tone and negation the same number is 0.16 and 0.17: where the model can read the answer, it
says no when it should.

The reading of this table is the useful part. The yes-bias is not a general optimism of the
model. It is what the model does when it cannot compute the answer: a question such as "Was the
parcel delivered within 5 working days?" about a text with an order date and a delivery date
reads like a question whose answer is yes, and without doing the subtraction, the model goes
with how it reads.

## Recalibrating does not fix it

The obvious fix for a bias is to shift the threshold or rescale the probabilities. We tried the
standard post-hoc recalibration, a temperature and a bias fitted on our development split, and
applied it to the 999 questions:

| | accuracy |
|---|---|
| as shipped | 0.757 |
| temperature and bias fitted on dev | 0.759 |
| best bias chosen on the 999 set itself | 0.763 |
| fitted on half of the 999 scenarios, tested on the other half | no gain |

The third row is cheating on purpose: the bias is picked by looking at the test answers, which
is the most any threshold change could ever recover. It recovers 0.006.

The reason is visible in the previous table. A single shift moves every question at once, and
the questions that need it (arithmetic, dates) and the ones that do not (tone, negation) are
far apart. Push the threshold up enough to fix the sums and you start saying no to facts the
model had right.

A calibration measurement on familiar data is no help here either. On the natural yes/no
questions of our held-out split the model's calibration error is 0.009, which is very good, and
it does not predict this: that split resembles the training data, and the 999 questions do not.
The gap between the two is the subject of [our held-out benchmark said 0.855](held-out-benchmark-too-optimistic.md).

## What to do about it in an application

- **Do not ask the model to compute.** Extract dates, totals and counts and compare them in
  code. This is the single change that removes most of the bias, and it is covered on
  [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).
- **Trust a no more than a yes.** On this set the model's no is the more reliable answer. If a
  wrong yes is the expensive mistake, require more than 0.5 to act on yes, and treat the band
  from 0.5 to about 0.7 as "check".
- **Measure on your own questions.** The bias depends on the kind of question. A set of a
  hundred of your real cases, labelled by hand and split by kind, tells you where your
  thresholds should be.
- **Phrase for reading.** "Does the customer say the parcel was late?" is a reading question;
  "Was the parcel late?" may require a date calculation. The first is answered well.

## Short answers to the questions that lead here

**Why do LLMs say yes too often?** In our measurement, a small model says yes when it cannot
work out the answer, mostly on arithmetic and dates. On questions it can read, it does not.

**Is it a threshold problem?** No. A temperature and bias fitted on held-out data moved accuracy
from 0.757 to 0.759; the best possible bias, chosen on the test set, reached 0.763.

**Is the model badly calibrated?** On data like its training data it is well calibrated
(calibration error 0.009). On new kinds of questions, calibration does not carry over.

**Which questions are safe?** Facts stated in the text (0.954), tone (0.938), negation (0.858),
and whether the text states something at all (0.847).

**How do I fix it?** Keep computation in code, and set a higher bar for acting on yes than on
no.

**See also:** [small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md),
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md)
and [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md).

## Sources

- All numbers on this page are our own measurements: the 999-question set on
  `jevos-q4_k_m` for accuracy, error counts and mean probabilities (recomputed from the
  per-question results for this page), and the recalibration experiments run on the same set.
- Held-out calibration error: 6,397 natural yes/no questions, `jevos-q8_0`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. We publish the weakness because a threshold chosen without knowing it is a
threshold chosen wrong.*
