---
title: "Combining yes/no answers with AND, OR and NOT"
description: "Ask one condition per question and combine the probabilities in code: 1 - p for NOT, product or min for AND, max for OR, and when independence fails."
parent: "Probability and thresholds"
nav_order: 12
---

# Combining yes/no answers with AND, OR and NOT

**Ask one condition per question and do the logic in code: NOT is 1 - p; AND is the product
p1 times p2 if the conditions are independent, and can never exceed the smaller of the two; OR
is 1 - (1 - p1)(1 - p2) if independent, and can never be less than the larger.** When you do not
know whether the conditions are independent, and for questions about the same text you usually
do not, min for AND and max for OR are the safe reference points, and the truth lies within
bounds you can compute from the two numbers alone.

Doing the logic yourself, instead of asking one compound question, buys three things: you see
which condition failed, each question stays simple enough for a small model to read, and the
rule itself lives in code where it can be tested and changed without touching a prompt.

This page is why to split compound questions, the three rules with their bounds, what goes wrong
when the conditions depend on each other, the simpler alternative of deciding first, and the
special case of OR across many chunks.

## Why not ask one compound question

"Is the customer upset and asking for a refund, and not complaining about a wrong item?" has
three conditions and one answer. If the answer is 0.4, you cannot tell which part pulled it
down, and the model has to hold the logic, the negation included, in one reading. On 999 new
yes/no questions, jevos scored 0.858 on questions involving negation, against 0.954 on plain
stated facts; every extra clause in a question is another chance to misread it. The general
advice is on [one condition per question](one-condition-per-question.md), and negation in
particular on [negation in yes/no questions](negation-in-yes-no-questions.md).

Splitting costs little in time. Questions in the same request share the state, which is read
once: the README's three-question example takes about 66 ms against 49 ms for one question
alone, on the reference laptop.

## The three rules, with and without independence

| Operation | If independent | Always true, whatever the dependence | Common shortcut |
|---|---|---|---|
| NOT A | 1 - p | 1 - p | 1 - p |
| A AND B | p1 times p2 | between max(0, p1 + p2 - 1) and min(p1, p2) | min(p1, p2) |
| A OR B | 1 - (1 - p1)(1 - p2) | between max(p1, p2) and min(1, p1 + p2) | max(p1, p2) |

The middle column is the Frechet inequalities, which bound the probability of a conjunction or
disjunction without any assumption about how the events depend on each other. Two readings
follow. For AND, min(p1, p2) is the most optimistic value possible, reached when one condition
implies the other, and the product sits inside the interval. For OR, max(p1, p2) is the most
pessimistic, reached under the same kind of dependence.

## A worked example on the README request

The README refund example asks three questions about one message ("The box arrived empty. This
is the second time!") and returns `refund` 0.93, `upset` 0.83 and `wrong_item` 0.04. Combining
those published numbers:

- **NOT wrong_item**: 1 - 0.04 = 0.96.
- **refund AND upset**: product 0.77; bounds 0.76 to 0.83.
- **refund AND NOT wrong_item**: product 0.89; bounds 0.89 to 0.93.
- **refund OR upset**: independent 0.99; bounds 0.93 to 1.

The arithmetic is ours; the three inputs are the README's. The AND interval for refund and
upset runs from 0.76 to 0.83. Whether you report 0.77 or 0.83 depends entirely on an
assumption about independence, and for two questions about one angry customer, the assumption
is doubtful.

In code, this is short:

```python
a = answer["answers"]
refund, upset, wrong = (a[k]["noul"] for k in ("refund", "upset", "wrong_item"))
not_wrong = 1 - wrong
p_and = refund * not_wrong           # assumes independence
p_and_upper = min(refund, not_wrong) # no assumption: the most it can be
```

## When independence fails

Questions about the same text are rarely independent. An upset customer is more likely to be
asking for a refund; a message about a missing parcel is less likely to be about a wrong item.

- **Positively related conditions** make the product too low for AND and the independent
  formula too high for OR. With many conditions the product shrinks fast: five conditions at 0.9
  each give 0.59 if independent, while the true value could be anywhere from 0.5 to 0.9.
- **Calibration matters for every formula.** Products and sums of probabilities are only as
  good as the inputs. On new kinds of question jevos leans toward yes, most of all on arithmetic
  and dates, so an AND of two leaning answers inherits both leans. See
  [LLM calibration explained](llm-calibration-explained.md).

If a combined probability drives a decision, check it the same way as a single one: on labelled
cases, with a [reliability diagram](reading-a-reliability-diagram.md) of the combined number.

## Often simpler: decide first, then combine

For many workflows you do not need a combined probability at all. Threshold each answer on its
own, with its own threshold, and combine the booleans:

```python
refund_ok = a["refund"]["noul"] > 0.8 and a["wrong_item"]["noul"] < 0.3
```

This is easier to audit ("refund was above 0.8, wrong item below 0.3"), easier to tune per
question, and avoids the independence question entirely. Keep the probabilities in your log so
you can revisit the thresholds, as described on
[how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md). Reach for the
probability formulas when you need a single score to rank or to send to a review band.

## OR across many chunks of a long document

A long document split into chunks turns "does the contract mention auto-renewal?" into one
question per chunk and an OR across them. Here the independence formula is dangerous. With an
illustrative 20 chunks that each get a P(yes) of 0.05 from noise, 1 - 0.95 to the power 20 is
about 0.64: a confident yes built from nothing. Use the max across chunks, or threshold each chunk
and ask whether any passed. More on chunking is on
[yes/no questions about long documents](yes-no-questions-about-long-documents.md).

## Short answers to the questions that lead here

**How do I compute NOT from P(yes)?** 1 - P(yes). It is the only rule that needs no assumption.

**Should I multiply probabilities for AND?** Only if the conditions are independent. Otherwise
the true value lies between max(0, p1 + p2 - 1) and min(p1, p2).

**Is max a good OR?** It is the lowest the OR can be. The independent formula is higher, and
overstates the OR when many weak answers are combined.

**Why not ask one question with AND in it?** Because you lose which condition failed, and each
clause is another chance for a small model to misread.

**Is combining in code slower?** Barely. Extra questions in the same request share the text,
which is read once.

**See also:** [logits, log-odds and P(yes)](logits-log-odds-and-p-yes.md),
[scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md) and
[a yes/no LLM vs a business rules engine](yes-no-llm-vs-business-rules-engine.md).

## Sources

- The inputs 0.93, 0.83 and 0.04, and the 66 ms vs 49 ms timing, are from the README of the
  [jev repository](https://github.com/feder-cr/jev); the combinations are arithmetic.
- Our measurement: 0.858 on negation and 0.954 on stated facts, 999-question set,
  `jevos-q4_k_m`.
- [Frechet inequalities](https://en.wikipedia.org/wiki/Fr%C3%A9chet_inequalities) on
  Wikipedia, as a secondary pointer for the bounds, fetched 2026-09-29.
- The 20-chunk example is illustrative.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose README example asks three
questions about one empty box instead of one question with two ands in it.*
