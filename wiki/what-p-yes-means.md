---
title: "What P(yes) means, and what it does not"
description: "What a P(yes) of 0.9 from a yes/no model promises, what it does not tell you about one case, and when the number stops meaning what it says."
parent: "Probability and thresholds"
nav_order: 1
---

# What P(yes) means, and what it does not

**P(yes) is the model's probability that the answer to your question, about this text, is yes.
From a calibrated model, 0.9 means that among many answers of about 0.9 on similar data, about
nine in ten turn out to be yes.** It is not a certainty, it is not a measure of how much of
something the text contains, and it says nothing checkable about the one case in front of you
on its own. Its meaning lives in the long run, over many answers, and only on data like the data
it was checked on.

That last condition is the one people skip. A probability is a promise about frequencies, and
the promise is only as good as the match between your inputs and the inputs it was measured on.
When the inputs change, the number keeps looking the same while the promise quietly breaks.

This page is the three readings of a number like 0.9, what it promises over many answers, what
it cannot tell you about one, when it stops meaning what it says, and how to use it in code.

## Is 0.9 a probability, a confidence or a score?

The same number can be read three ways, and only one of them is right for a calibrated model.

- **A frequency over similar cases.** Of the texts and questions that get about 0.9, about 90
  percent are yes. This is the reading calibration is about, and the one scikit-learn's
  documentation uses: a well calibrated classifier is one where, among the samples given a value
  close to 0.8, about 80 percent belong to the positive class.
- **A certainty.** "The model is 90 percent sure." There is no inner feeling being reported. It
  is a number produced by the model for this input, and the only way to know what it is worth is
  to count how often such numbers were right.
- **A score or intensity.** "The customer is 0.73 upset." This reading is wrong. In the README
  example, `upset` came back at 0.73 for "The box arrived empty. This is the second time!". That
  is the probability that the answer to "Is the customer upset?" is yes, not a measure of how
  angry the customer is. A mildly annoyed customer and a furious one can both get a high P(yes);
  to ask about degree, ask a threshold question such as "is the customer very upset?", covered
  in [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).

A score that is not calibrated can still be useful for ranking: a higher number means more
likely yes. But you cannot read it as "nine in ten" until you have checked it.

## What 0.9 promises across many answers

On data like the data it was checked on, a calibrated P(yes) lets you plan. If you act on every
answer above 0.9, you can expect roughly one wrong action in ten or fewer among them; if you
average the probabilities over a batch, you get a fair estimate of how many are yes.

For jevos, the check we have is this: on 6,397 natural yes/no questions from a held-out split,
the calibration error (ECE) of `jevos-q8_0` was 0.009. In plain terms, on that data, the numbers
the model gave were very close to the frequencies it achieved. What ECE measures, and how, is on
[expected calibration error, explained](expected-calibration-error-explained.md).

## What it does not tell you about this one case

A single answer of 0.9 does not come with a 90 percent that you can verify. The case is either
yes or no. The 0.9 tells you which bucket of cases it belongs to, and the bucket has a track
record.

Two practical consequences:

- **One wrong 0.95 is not evidence of a broken model.** At that level you should expect about
  one in twenty to be wrong. Ten wrong 0.95s in a row is evidence.
- **The number does not explain itself.** The README refund example returned 0.78 for "Should
  this customer get a refund?" That is not "78 percent of a refund", and it does not say which
  part of the policy the model weighed. If you need to know why, split the question into its
  conditions and ask each one; see
  [combining yes/no answers](combining-yes-no-answers-and-or-not.md).

## When the number stops meaning what it says

Calibration is a property of a model on a kind of data, not of the model alone. On 999 yes/no
questions written from scratch after the model was finished, of new kinds and in new scenarios,
`jevos-q4_k_m` was right 0.757 of the time, and its probabilities leaned toward yes: on
arithmetic questions whose true answer was no, the average P(yes) was 0.59. A calibrated model
would put those near 0. The same model that looks calibrated on familiar data is not calibrated
on questions it cannot work out. The detail is on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md), and the gap
between the two test sets on
[our held-out benchmark said 0.855](held-out-benchmark-too-optimistic.md).

The base rate matters too. If yes is rare in your traffic, a model calibrated on a more balanced
mix will give yeses that are wrong more often than the number suggests;
[base rates](base-rates-and-yes-no-predictions.md) works through why.

## How to use it in code

Keep the number, threshold it, and log it. The README pattern is the whole idea:

```python
if answer["answers"]["billing"]["noul"] > 0.5:
    print("send to billing")
```

From there, three habits pay off. Choose the threshold from your own labelled cases, not by
taste ([how to choose a threshold](how-to-choose-a-threshold-for-p-yes.md)). Send the middle of
the range to a person when a mistake is expensive
([a review band](human-in-the-loop-ai-with-a-review-band.md)). And store the probability next to
the decision, so you can later check whether your 0.9s were right nine times in ten.

## Short answers to the questions that lead here

**Does P(yes) = 0.9 mean the model is 90 percent sure?** It means that, on similar data, about
nine in ten answers of that size were yes. It is a frequency you can check, not a feeling.

**Is a higher P(yes) a stronger yes?** It is a more likely yes, not a bigger one. To ask about
degree, ask a separate threshold question.

**Can I compare P(yes) across different questions?** Only if each question is calibrated on your
data. Some kinds of question lean toward yes, so the same 0.7 can mean different things.

**Why did a 0.95 answer turn out wrong?** At 0.95, about one in twenty should be. Judge the
number over many answers, not one.

**Is P(yes) the same as accuracy?** No. Accuracy is how often the thresholded answer is right;
P(yes) is the model's estimate for one case.

**See also:** [LLM calibration explained](llm-calibration-explained.md),
[reading a reliability diagram](reading-a-reliability-diagram.md) and
[LLM confidence scores: probabilities vs self-reports](llm-confidence-score-probability-vs-self-report.md).

## Sources

- Our measurements: ECE 0.009 on 6,397 natural yes/no held-out questions (`jevos-q8_0`); 0.757
  accuracy and mean P(yes) 0.59 on no-answer arithmetic questions from the 999-question set
  (`jevos-q4_k_m`).
- The billing, refund and upset values are the README examples of the
  [jev repository](https://github.com/feder-cr/jev).
- Definition of a well calibrated classifier:
  [scikit-learn, Probability calibration](https://scikit-learn.org/stable/modules/calibration.html),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which returns one number per yes/no question
and nothing else, so this page is about the only output there is.*
