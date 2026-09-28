---
title: "Pairwise comparison with a yes/no judge"
description: "Compare two LLM outputs with a yes/no judge: ask whether A beats B on one criterion, swap the order to cancel position bias, and aggregate into a win rate."
parent: "Evaluation"
nav_order: 6
---

# Pairwise comparison with a yes/no judge

**To compare two outputs with a yes/no judge, ask one criterion at a time "on this criterion, is
the first answer better than the second?", then ask again with the two answers swapped, and
combine the two probabilities.** The swap is not optional. LLM judges prefer one position over
the other, and asking in both orders cancels that preference along with any constant lean toward
yes. Over a test set, the combined probabilities give a win rate per criterion for system A
against system B.

Pairwise comparison is attractive because "which of these two is better?" is often easier to
answer than "how good is this one?". It is also where judge bias is easiest to fool yourself
with, because a biased judge produces a confident winner every time.

This page is when pairwise beats scoring each output alone, the request, why and how to swap, the
arithmetic that combines the two orders, turning comparisons into a win rate, and what we have and
have not measured.

## When to compare in pairs instead of scoring each output

| | Pointwise (score each output) | Pairwise (compare two) |
|---|---|---|
| question | "Does the reply give the return deadline?" | "Does the first reply explain the return process more clearly than the second?" |
| good for | properties that are present or absent | qualities that are a matter of degree |
| position bias | none | yes, must be controlled |
| cost for N systems | N judgements per input | grows with the number of pairs |
| result | absolute pass rates | relative preference only |

If a criterion can be written as an observable property, score it pointwise and compare pass rates;
that is simpler and has no position effect. The advice on turning criteria into properties is on
[rubric design for an LLM judge](rubric-design-for-an-llm-judge.md). Keep pairwise for what is
genuinely comparative: clarity, directness, how well an answer addresses the actual question when
both address it somewhat.

## The pairwise request

Name the positions neutrally, keep the criterion narrow, and put both outputs in `state`:

```json
{
  "model": "jev-latest",
  "state": {
    "customer_question": "How do I return shoes that are too small?",
    "first_reply":  "You can return unworn shoes within 30 days. Print the label from your account page and drop the box at any post office.",
    "second_reply": "Returns are possible. Please see our returns policy for details."
  },
  "questions": {
    "clearer":  {"type": "noul", "instructions": "Does the first reply explain how to return the shoes more clearly than the second reply?"},
    "specific": {"type": "noul", "instructions": "Does the first reply give more specific steps than the second reply?"}
  }
}
```

One criterion per question, as everywhere. "Is the first reply better?" with no criterion lets the
judge weigh length, tone and content however it likes, and you learn nothing about why.

## Why the order has to be swapped

In "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", Zheng and colleagues tested position
bias by showing judges two similar answers in both orders. Consistency across the two orders was
far from complete: only GPT-4 gave consistent results in more than 60% of cases among the judges
they tested. Their conservative fix is to call the judge twice with the order swapped and declare
a win only when an answer is preferred in both orders.

A yes/no judge adds a second, related effect. A question of the form "is the first better than the
second?" has a yes and a no, and jevos leans toward yes on questions it cannot work out: on our
999-question test set it made 152 wrong yeses against 91 wrong noes. Without a swap, that lean
would read as a preference for whichever answer sits first. We have not measured jevos on
pairwise comparisons, so treat both effects as present until your own swap test says otherwise.

## Combining the two orders

Ask the same question twice: with A first (probability `p_ab`) and with B first (probability
`p_ba`, which is about B beating A). Then:

```
pref_A = (p_ab + (1 - p_ba)) / 2
```

If the judge adds a constant lean `d` toward yes in both orders, it appears as `+d` in `p_ab` and
as `-d` in `1 - p_ba`, and cancels in the mean. A constant preference for the first position cancels
the same way. What does not cancel is a lean that depends on the content, which is why you still
check the judge against labelled pairs.

The two orders also give a consistency signal for free:

- `p_ab` high and `p_ba` low: a clear preference for A.
- `p_ab` low and `p_ba` high: a clear preference for B.
- both high or both low: the judge is following the position, not the content. Record a tie.

Counting how often the third case happens is the simplest measurement of position bias for your
judge on your data. If it is most of your pairs, the criterion is not one the judge can compare.

## From pairs to a win rate

Over a test set of inputs, for each criterion:

1. Run both systems on every input.
2. Ask each pairwise question in both orders.
3. Count A as winning where `pref_A` is above an upper bar, B where it is below a lower bar, and a
   tie in between or when the two orders disagree.
4. Report wins, losses and ties per criterion, not one merged number.

Ties are information. Two prompts that tie on most inputs are close to equivalent on that
criterion, and a win rate computed only over the few decided pairs overstates the difference. The
arithmetic of combining several criteria, and when to use min, product or mean, is on
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## What pairwise judging cannot fix

- **Length.** Zheng and colleagues also report verbosity bias: judges favouring answers made
  longer by repetition. A swap does not remove it, because the longer answer is longer in both
  orders. Control it by comparing outputs of similar length, or by adding a pointwise criterion
  such as "Does the reply repeat itself?". More on this in
  [LLM judge bias and how to control it](llm-judge-bias.md).
- **Absolute quality.** A pairwise win says A is better than B, not that A is good. Two bad replies
  still produce a winner.
- **Hard reasoning.** "Is the first proof more correct?" is not a reading question. A small judge is
  the wrong tool; use a large model or a person.
- **Long pairs.** Two outputs plus the input must fit in jevos's 8,192-token context, and latency
  grows with length.

## Short answers to the questions that lead here

**What is pairwise LLM evaluation?** Asking a judge which of two outputs is better on a criterion,
instead of scoring each output alone, and aggregating the preferences into a win rate.

**What is position bias in an LLM judge?** A preference for the answer in one position regardless
of content. It is measured by swapping the order and checking whether the verdict follows the
answer or the position.

**How do I remove position bias?** Ask in both orders and average the probability for A with one
minus the probability for B. Treat disagreement between orders as a tie.

**Should I use pairwise or pointwise evaluation?** Pointwise for properties that are present or
absent, pairwise for qualities of degree. Pointwise has no position effect to control.

**Can a small local model do pairwise judging?** For comparisons you could make by reading, and in
English, it is worth testing with the swap. We have not measured it ourselves.

**See also:** [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md),
[logits, log-odds and P(yes)](logits-log-odds-and-p-yes.md) and
[building a yes/no test set for your own data](building-a-yes-no-test-set.md).

## Sources

- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena",
  [arXiv:2306.05685](https://arxiv.org/abs/2306.05685) and its
  [HTML version](https://arxiv.org/html/2306.05685v4), fetched 2026-09-29: position bias
  measurement, the swap-and-agree approach, verbosity bias.
- The yes/no error split (152 against 91): our 999-question test set, `jevos-q4_k_m`.
- The swap formula and its cancellation argument are arithmetic, not a measurement.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no model that has not yet been
measured on pairwise comparisons, which is why this page tells you how to measure it.*
