---
title: "Thresholds when a wrong yes costs more than a wrong no"
description: "The expected-cost rule for a yes/no threshold, a table from cost ratio to cut-off, and why a model that leans toward yes needs a higher bar still."
parent: "Probability and thresholds"
nav_order: 8
---

# Thresholds when a wrong yes costs more than a wrong no

**Act on yes only when P(yes) is at least C_fp / (C_fp + C_fn), where C_fp is the cost of acting
on a wrong yes and C_fn the cost of a wrong no.** If a wrong yes costs four times a wrong no, the
threshold is 4 / 5 = 0.8, not 0.5. The rule is exact for a calibrated probability; for a model
that leans toward yes on some kinds of question, as small models measurably do, the bar on
those questions should be higher still, or the question should be rewritten so the model does
not have to guess.

The rule turns a vague instinct ("be careful with refunds") into a number you can write down,
defend and revisit. It also makes clear that the threshold belongs to the decision, not to the
model: the same P(yes) can justify sending an email and not justify closing an account.

This page is the derivation, a table from cost ratio to threshold, the calibration caveat with
our measured yes-lean, examples in both directions, and what to do when costs vary per case.

## The expected-cost rule

For one case with probability p that the true answer is yes:

- If you act on yes, you are wrong with probability 1 - p, so the expected cost is (1 - p)
  times C_fp.
- If you act on no, you are wrong with probability p, so the expected cost is p times C_fn.

Act on yes when the first is no larger than the second: (1 - p) C_fp <= p C_fn, which gives
p >= C_fp / (C_fp + C_fn).

This is the two-class case of Elkan's (2001) analysis of cost-sensitive decisions: the optimal
prediction is the positive class if and only if its expected cost is no greater than that of
predicting the negative class. His general formula also allows for costs of correct decisions;
with those at zero it reduces to the one above. Only the ratio of the two costs matters, which
is convenient, because the ratio is often easier to agree on than the amounts.

## From cost ratio to threshold

| A wrong yes costs ... a wrong no | Threshold on P(yes) |
|---|---|
| a quarter of | 0.2 |
| the same as | 0.5 |
| twice | 0.67 |
| three times | 0.75 |
| four times | 0.8 |
| nine times | 0.9 |
| nineteen times | 0.95 |

These follow from the formula, not from any measurement. Note how fast the threshold climbs:
the step from "the same" to "four times" moves it by 0.3, while every further doubling moves it
less. Past about 0.95 the question is less about the threshold and more about whether a machine
should take that decision alone; see
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

## The rule assumes calibration, and small models lean toward yes

The formula treats P(yes) as the real chance that the answer is yes. If the model's 0.8s are yes
only 65 percent of the time on your data, a threshold of 0.8 buys less safety than it claims.

For jevos, the relevant measurement is the direction of its errors on 999 yes/no questions
written after the model was finished, measured on the first jevos (per-kind numbers for jevos-v4,
78.9% overall on the same questions, are not published): 152 said yes when the answer was no, 91 said no when the
answer was yes. The lean sits mostly on questions that need a computation. On arithmetic
questions whose answer was no, the mean P(yes) was 0.59; on dates and times, 0.53. On tone and
negation it was 0.16 and 0.17.

Three consequences for an asymmetric threshold:

- **When a wrong yes is the expensive mistake, the model's bias works against you.** Raise the
  yes bar above what the formula gives, or calibrate on your own labelled cases first, as on
  [Platt scaling for a yes/no model](platt-scaling-for-a-yes-no-model.md).
- **Raising the bar does not fix computing questions.** On arithmetic, the questions whose
  answer is no get an average P(yes) above one half, and no threshold separates them cleanly. Compute the date or the total in
  code and ask the model only what the text says. The detail is on
  [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).
- **Trust a no more than a yes.** On that set with the first jevos, a no from the model was the more reliable answer.

## Examples in both directions

**A wrong yes costs more.** Auto-approving a refund, suspending an account, sending an email to
a customer, deleting a record. Take the README refund example: for an empty box delivered five
days ago, with a 30-day policy in the question, `refund` came back at 0.93. With a four-to-one
cost ratio the threshold is 0.8, so this case is approved automatically; one at 0.78 would not
be, even though the model leans yes. That one is a candidate for a quick human look, which is where
[refund request triage](refund-request-triage-with-a-local-llm.md) picks it up.

**A wrong no costs more.** Missing an urgent ticket, failing to flag a message for a moderator,
letting a possible fraud case skip review. Here the threshold goes below 0.5: if a missed flag
costs four times a needless one, flag from 0.2. Flagging is cheap because a person looks next;
the model's job is to not let things through.

The same question can sit on both sides. "Does this message ask for a refund?" can route to the
refund queue at a low threshold (a needless routing costs an agent a minute) and trigger an
automatic payout only at a high one.

## When costs are not the same for every case

Costs often depend on the case. Elkan's paper gives a credit card example in which approving a
fraudulent transaction costs the amount of the transaction, while refusing a legitimate one has
a fixed cost because it annoys a customer. The threshold then changes per case, and the natural place to
compute it is your code:

```python
def refund_threshold(amount, cost_wrong_no=5.0):
    cost_wrong_yes = amount          # paying out a refund that was not owed
    return cost_wrong_yes / (cost_wrong_yes + cost_wrong_no)

approve = answer["answers"]["refund"]["noul"] >= refund_threshold(order_total)
```

The cost figures in that sketch are placeholders. The structure is the point: the model says how
likely yes is, and your code, which knows the amount, decides what that likelihood is worth.

## Short answers to the questions that lead here

**How do I set a threshold when false positives are expensive?** Use p >= C_fp / (C_fp + C_fn).
A wrong yes that costs four times a wrong no gives 0.8.

**Is 0.5 ever the right threshold?** When both mistakes cost the same and the model is
calibrated on your data.

**Why raise the threshold further for a small model?** Because on new kinds of question it makes
more wrong yeses than wrong noes, so its P(yes) overstates yes there.

**Can the threshold depend on the case?** Yes. Compute it in code from case facts such as the
amount at stake.

**What if the cost ratio is huge?** Past about 0.95, route the case to a person instead of
automating it.

**See also:** [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md),
[precision and recall at a P(yes) threshold](precision-and-recall-at-a-threshold.md) and
[gating AI agent tool calls](gating-ai-agent-tool-calls.md).

## Sources

- Our measurements: 152 wrong yeses vs 91 wrong noes and mean P(yes) by kind of question on the
  999-question set, first jevos (`jevos-q4_k_m`). The refund value 0.93 is the README example of the
  [jev repository](https://github.com/feder-cr/jev).
- The cost-ratio table is arithmetic from the formula, not a measurement.
- Elkan (2001), [The Foundations of Cost-Sensitive Learning](https://cseweb.ucsd.edu/~elkan/rescale.pdf),
  IJCAI: optimal decision rule, threshold formula, credit card example, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev). A model that errs toward yes is
worth knowing about before you let its yes spend money.*
