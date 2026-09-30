---
title: "How to choose a threshold for P(yes)"
description: "Start at 0.5, then pick each question's threshold from your own labelled cases, keep a separate split to check it, and re-check whenever the input changes."
parent: "Probability and thresholds"
nav_order: 7
---

# How to choose a threshold for P(yes)

**Start at 0.5, which is the neutral point when the model is calibrated and a wrong yes costs
the same as a wrong no; then move it using a few hundred labelled cases from your own
traffic.** Pick the threshold per question, because different questions lean differently,
check it on cases you did not use to pick it, and pick again whenever the input changes: a new
form, a reworded question, a new model file, a new mix of customers.

A threshold is where your costs meet the model's behaviour. Neither is known in advance: the
costs are a business decision, and the behaviour on your texts is something you measure. A
threshold picked by taste encodes neither.

This page is why 0.5 is only the starting point, how to choose from labelled cases, why one
threshold per question, when two thresholds beat one, and when to choose again.

## Why 0.5 is the starting point, not the answer

scikit-learn's documentation states the default plainly: a binary classifier predicts the
positive class when the probability is greater than 0.5. Elkan (2001) makes the same point about
standard learning algorithms, which implicitly decide at 0.5, and shows why that is only right
for one cost setting: the optimal cut-off depends on what each kind of mistake costs.

The README's own example uses 0.5:

```python
if answer["answers"]["billing"]["noul"] > 0.5:
    print("send to billing")
```

For a demo, where the next request is a new decision and nothing is lost for good, that is a
sensible default. For a refund,
a ban or an email sent to a customer, it is a placeholder. Two things move it away from 0.5:
unequal costs, covered on
[thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md), and a model
that is not calibrated on your data, which you find out by measuring.

## Choosing from labelled cases, step by step

1. **Collect 100 to 300 real cases per question**, answered yes or no by a person who read the
   text. [Building a yes/no test set](building-a-yes-no-test-set.md) covers how to sample them.
2. **Split them.** Use one part to choose the threshold and keep the other to check it.
   scikit-learn's threshold-tuning guide is blunt about this: never use the same data to train a
   classifier and to tune its decision threshold. For a model you did not train, the same logic
   applies to choosing and evaluating.
3. **Run the choosing split and keep every P(yes).**
4. **Sweep thresholds** from 0.05 to 0.95 and compute, at each, the number you care about:
   total cost, precision at a minimum recall, or errors of the expensive kind.
5. **Pick, then check** on the held-back split. If the result there is much worse, you had too
   few cases or the question is unstable; see
   [why wording changes an LLM's answer](why-wording-changes-the-answer.md).
6. **Write it down** with the date, the model file and the case count.

A sweep is a few lines once you have `p` (the probabilities) and `y` (1 for yes):

```python
import numpy as np

def cost(t, c_fp=1.0, c_fn=1.0):
    say_yes = p > t
    return c_fp * np.sum(say_yes & (y == 0)) + c_fn * np.sum(~say_yes & (y == 1))

best = min(np.arange(0.05, 0.96, 0.01), key=cost)
```

What the sweep trades is shown on
[precision and recall at a P(yes) threshold](precision-and-recall-at-a-threshold.md).

## One threshold per question

Questions do not behave alike. On 999 new yes/no questions labelled by the kind of reasoning
they need, `jevos-q4_k_m` ranged from 0.954 on stated facts and 0.938 on tone to 0.598 on dates
and 0.584 on arithmetic, and the mean P(yes) on questions whose answer was no ranged from 0.16
to 0.59. A single cut-off for all of them is right for none.

So keep thresholds in a table next to the questions:

```python
THRESHOLDS = {"refund": 0.8, "upset": 0.5, "wrong_item": 0.6}  # placeholders, choose yours
decisions = {k: v["noul"] > THRESHOLDS[k] for k, v in answer["answers"].items()}
```

The values above are placeholders for the shape of the code, not recommendations. The names
are the three questions of the README refund example.

If a question needs a threshold far from 0.5 to behave, consider whether the question itself is
the problem. A question that asks the model to compute a date or a total will lean toward yes
whatever the cut-off; move the computation into code and ask what the text says instead, as
[small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md) explains.

## Two thresholds are often better than one

A single cut-off forces a decision on every case, including those near it where the model is
least sure. Two cut-offs give three outcomes: act on yes above the high one, act on no below the
low one, and send the middle to a person. That pattern, and how to size the middle, is on
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

## When to choose again

A threshold is valid for the inputs it was chosen on. Choose again when:

- **The text changes shape.** A new form layout, a new ticket template, longer messages, a new
  channel.
- **The question changes.** Any rewording, even one that looks equivalent.
- **The mix changes.** If yes becomes rarer, the same threshold gives more false yeses per true
  one; see [base rates](base-rates-and-yes-no-predictions.md).
- **The model file changes.** `GET /health` reports the model's fingerprint, a SHA-256 over its files; log it with every
  decision so you know which file a threshold was chosen on. jev runs the 8-bit OpenVINO model;
  the two GGUF builds in the release, `jevos-q4_k_m` and `jevos-q8_0`, are for other tools and
  have not been compared on the same accuracy set, so treat a switch between any of them as a
  new model and re-check.

## Short answers to the questions that lead here

**What threshold should I use for P(yes)?** 0.5 to start; then the value that minimises your
cost on a few hundred of your own labelled cases, checked on a separate split.

**Should every question have the same threshold?** No. Questions of different kinds lean
differently, so choose per question.

**How many labelled cases do I need?** A hundred per question is a start; a few hundred makes
the choice stable.

**Can I choose the threshold on my test set?** Only if you then evaluate on different cases.
Choosing and scoring on the same cases overstates how well it works.

**When should I re-check a threshold?** When the text, the question, the mix of cases or the
model file changes.

**See also:** [what P(yes) means](what-p-yes-means.md),
[LLM calibration explained](llm-calibration-explained.md) and
[LLM regression tests in CI](llm-regression-tests-in-ci.md).

## Sources

- Our measurements: accuracy and mean P(yes) by kind of question, 999-question set,
  `jevos-q4_k_m`. The 0.5 rule in the README Python example, and the
  `/health` fingerprint, are from the [jev repository](https://github.com/feder-cr/jev).
- [scikit-learn, Tuning the decision threshold](https://scikit-learn.org/stable/modules/classification_threshold.html):
  default of 0.5, never tune and train on the same data, fetched 2026-09-29.
- Elkan (2001), [The Foundations of Cost-Sensitive Learning](https://cseweb.ucsd.edu/~elkan/rescale.pdf),
  IJCAI, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose README example acts at 0.5;
a refund queue deserves a threshold chosen on its own cases.*
