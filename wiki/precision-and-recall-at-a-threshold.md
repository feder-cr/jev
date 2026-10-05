---
title: "Precision and recall at a P(yes) threshold"
description: "How moving a P(yes) threshold trades precision against recall, a worked example with illustrative numbers, and how to pick for spam filtering or refunds."
parent: "Probability and thresholds"
nav_order: 10
---

# Precision and recall at a P(yes) threshold

**Raising the P(yes) threshold usually raises precision, because fewer wrong yeses get through,
and lowers recall, because more true yeses fall below the bar; lowering it does the opposite.**
Precision is the share of your yeses that are right; recall is the share of the real yeses you
caught. Which one to favour depends on which mistake hurts: a spam filter that hides real mail
needs precision, while a queue that must not miss a refund request needs recall. The same
question can serve both, with a different threshold for each action.

There is no threshold that is best in general, only one that is best for a decision. The useful
habit is to name the action first ("move to spam", "route to the refund queue", "pay out") and
then ask which error that action can afford.

This page is the definitions, a worked example with toy numbers, two use cases that pull in
opposite directions, why precision depends on how common yes is, and how to draw the curve from
your own answers.

## Precision and recall, in terms of your decisions

scikit-learn defines them with the counts of true positives (tp), false positives (fp) and
false negatives (fn):

- **Precision** = tp / (tp + fp): of the cases you called yes, how many were yes. In the
  documentation's words, the ability not to label as positive a sample that is negative.
- **Recall** = tp / (tp + fn): of the cases that were yes, how many you called yes. The ability
  to find all the positive samples.

A threshold turns each P(yes) into a yes or a no, so every threshold has its own tp, fp and fn,
and its own precision and recall.

## What moving the threshold does, on toy numbers

The ten cases below are illustrative, made up to show the mechanics. Five are really yes, five
really no:

- really yes: P(yes) of 0.95, 0.88, 0.81, 0.66, 0.42
- really no: P(yes) of 0.72, 0.55, 0.35, 0.20, 0.08

| Threshold | Called yes | Right yeses (tp) | Wrong yeses (fp) | Precision | Recall |
|---|---|---|---|---|---|
| 0.30 | 8 | 5 | 3 | 0.63 | 1.00 |
| 0.50 | 6 | 4 | 2 | 0.67 | 0.80 |
| 0.70 | 4 | 3 | 1 | 0.75 | 0.60 |
| 0.85 | 2 | 2 | 0 | 1.00 | 0.40 |

Recall can only go down as the threshold rises, since you call fewer cases yes. Precision
usually goes up, but not always: on real data it can dip when a threshold drops a right yes
before the next wrong one. That is why you read the whole curve, not two points.

## Spam: precision first

Moving a real email to the spam folder can hide an invoice or a job offer; letting one spam
message into the inbox costs a second of the reader's attention. The expensive error is the
wrong yes, so pick the threshold for precision, and accept that some spam gets through.

Two things help beyond the threshold. Ask several narrow questions ("does it promote a product
the reader did not ask about?", "does it contain a link to an unrelated site?") instead of one
broad "is this spam?", and combine them with sender facts in code. The details are on
[spam detection with yes/no questions](spam-detection-with-yes-no-questions.md), and the
arithmetic of combining answers is on
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## Refund requests: recall to route, precision to pay

"Does this message ask for a refund?" drives two different actions:

- **Routing to the refund queue.** Missing a request leaves a customer waiting; a needless
  routing costs an agent a few seconds. Favour recall with a low threshold.
- **Paying out automatically.** A wrong yes sends money that was not owed. Favour precision with
  a high threshold, and send the middle to a person, as on
  [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

The README example shows the kind of number involved: for "The box arrived empty. This is the
second time!", `refund` came back at 0.93. That clears a routing threshold easily, while a payout threshold
set at 0.95 would still hold it for a person, which is the design working as intended.

A measured reason to set the payout bar high: on 999 yes/no questions written after the model
was finished, the first jevos made 152 wrong yeses against 91 wrong noes (not measured per kind on jevos-v4). On that set its mistakes cost
more precision than recall, and a payout decision needs precision most.

## Precision depends on how common yes is

Recall is computed only over the real yeses, so it does not change when yes becomes rarer.
Precision does: with the same model and threshold, fewer real yeses means the wrong yeses from
the large pool of noes make up a bigger share of everything you call yes. Saito and Rehmsmeier
(2015) argue for this reason that precision-recall plots are more informative than ROC plots on
imbalanced data, because they evaluate the fraction of true positives among positive
predictions. The worked arithmetic is on
[base rates: why a 0.9 yes can still be wrong often](base-rates-and-yes-no-predictions.md).

The practical rule: measure precision on a sample with your real mix of yes and no. A balanced
test set gives you a recall you can trust and a precision you cannot.

## Drawing the curve from your answers

With the true answers `y` (1 for yes) and the probabilities `p` from your labelled requests:

```python
from sklearn.metrics import precision_recall_curve

precision, recall, thresholds = precision_recall_curve(y, p)
```

scikit-learn returns one pair per distinct score; the first pair corresponds to calling
everything yes (precision equal to the share of yes, recall 1), and the last precision and recall
values are 1 and 0 with no threshold attached. Plot recall on the x-axis and precision on the
y-axis, mark the thresholds you are considering, and choose with the action in mind.

## Short answers to the questions that lead here

**What is the difference between precision and recall?** Precision is how many of your yeses
were right; recall is how many of the real yeses you found.

**Does a higher threshold always increase precision?** Usually, not always. Recall always goes
down or stays the same.

**Which should I optimise?** The one that protects against the expensive error of the action:
precision when a wrong yes is costly, recall when a miss is.

**Can one question have two thresholds?** Yes. Use a low one for cheap actions such as routing,
and a high one for costly actions such as paying out.

**Why is my precision lower in production than in testing?** Probably because yes is rarer in
production than in your test set.

**See also:** [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md),
[evaluation metrics for yes/no classifiers](evaluation-metrics-for-yes-no-classifiers.md) and
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md).

## Sources

- Our measurements: 152 wrong yeses vs 91 wrong noes, 999-question set, measured on the first jevos. The
  refund value 0.93 is the README example of the [jev repository](https://github.com/feder-cr/jev).
- The ten-case table is illustrative, invented for this page.
- [scikit-learn precision_recall_curve](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_curve.html),
  definitions and boundary values, fetched 2026-09-29.
- Saito and Rehmsmeier (2015),
  [The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432),
  PLOS ONE, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The refund question is the same
question at both thresholds; only the action it triggers changes.*
