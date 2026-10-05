---
title: "Scores as yes/no thresholds: is it at least high?"
description: "Turn a 1-to-5 score or a low/medium/high level into n-1 yes/no boundary questions, read the level from the answers, and repair boundaries that disagree."
parent: "Question design"
nav_order: 5
---

# Scores as yes/no thresholds: is it at least high?

**To get a level or a score out of a yes/no model, ask one question per boundary ("Is the
urgency at least medium?", "at least high?", "critical?") and take the level as the highest
boundary answered yes.** A scale with n levels needs n minus 1 questions. Each boundary has one
clear answer, where "Is the urgency medium?" can be wrong in two directions, and the answers
come back as probabilities you can threshold, compare and log.

jevos-v4 also answers a `score` question directly (levels in `criteria`, lowest first; early),
and you can build the same kind of score yourself from yes/no questions when you want control of
the boundaries. Boundary questions are not a workaround, though. They are the same idea statisticians
use for ordered outcomes, and they often make a better score than asking for a number.

This page is the idea behind boundary questions, the request, how to read a level and an
expected score from the answers, what to do when the boundaries disagree, and where the
approach is weak.

## Why boundaries and not levels?

Ordered levels are not independent labels. "High" is more than "medium" and less than
"critical", and a question per level throws that order away: "Is it medium?" and "Is it high?"
can both come back high, and nothing tells you which to believe.

A boundary question keeps the order. "At least high" is yes for high and for critical, no for
low and for medium. Ordinal regression, the standard statistical model for ordered outcomes,
is built the same way: it models the cumulative probability of being at or below each
threshold, and the probability of one level is the difference between two neighbouring
cumulative probabilities. Asking a model n minus 1 boundary questions gives you those
cumulative probabilities directly.

## A request with one question per boundary

```json
{
  "model": "jev-latest",
  "state": "Our checkout has been down for twenty minutes and customers are calling. Please look at it now.",
  "questions": {
    "at_least_medium":  {"type": "noul", "instructions": "Is the urgency of this message at least medium?"},
    "at_least_high":    {"type": "noul", "instructions": "Is the urgency of this message at least high?"},
    "critical":         {"type": "noul", "instructions": "Is the urgency of this message critical?"}
  }
}
```

The questions are parallel: same subject, same property, only the level changes. That matters
because you will compare their probabilities with each other. The general rule is on
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

If the levels have meanings in your organisation, say so in the question: "Is the urgency at
least high, meaning a customer-facing service is affected?" The model knows nothing about your
scale except what the question says.

## Reading the level

Two ways, depending on what you need:

```python
bounds = ["at_least_medium", "at_least_high", "critical"]
levels = ["low", "medium", "high", "critical"]
p = [answers[b]["noul"] for b in bounds]

# 1. a level: count the boundaries passed
level = levels[sum(x > 0.5 for x in p)]

# 2. an expected score from 0 to 3: the sum of the boundary probabilities
expected = sum(p)
```

The expected score works because for an ordered scale, the expected level equals the sum of
the probabilities of being at least each boundary. It is a continuous number you can sort a
queue by, which a hard level cannot do.

## When boundaries disagree

A well behaved set of answers decreases: P(at least medium) is at least P(at least high), which
is at least P(critical). Nothing in three independent questions enforces that, and on unclear
texts they can come back out of order, for example 0.4 for medium and 0.6 for high.

Three ways to handle it, from cheapest to most careful:

- **Enforce the order.** Replace each probability with the minimum of itself and every one
  before it. The result is monotone and never claims more than a lower boundary allows.
- **Count it as a signal.** An inversion means the model found the text ambiguous about the
  scale. Log it; if it happens often on one boundary, that boundary question is badly worded.
- **Send it to a person.** For decisions with a cost, an inverted pair is a good reason to put
  the case in a [review band](human-in-the-loop-ai-with-a-review-band.md).

```python
fixed = []
for x in p:
    fixed.append(min(x, fixed[-1]) if fixed else x)
```

## Where this is weak

**Scores that are sums.** A score made by adding points ("2 points for a missing item, 3 for a
repeat, refund above 4") is arithmetic, not judgment. On the fraud points task (a score from six rules), jevos-v4 scored 0.50 and the hosted Jev 0.69, and
the model was confidently wrong, so the gap was largest on exactly these additive point
scores. Ask the model for each signal as its own question and add the points in code, as
described on [one condition per question](one-condition-per-question.md).

**Numbers in the text.** "Is the order value at least high?" when the text says "EUR 480" is a
number against a threshold, and on our 999-question test set the first jevos scored 0.654 on those questions,
against 0.954 for facts stated in the text (per-kind numbers for jevos-v4 are not published). If the number is in your data, compare it in code;
the details are on [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).

**Fine scales.** A 1-to-10 scale is nine boundaries, and the difference between "at least 6"
and "at least 7" is rarely something the text says. Few, well named levels work better than
many numbered ones.

Boundary questions are at their best on judgments a reader makes: urgency, severity, how
clearly a complaint is stated, how far an answer follows a rubric. A related use is in
evaluation, covered on [rubric design for an LLM judge](rubric-design-for-an-llm-judge.md).

## Short answers to the questions that lead here

**Can a yes/no model give a score?** Yes, as boundary questions. A scale of n levels takes n
minus 1 questions, and the level is the highest boundary answered yes.

**Why not ask "Is the priority medium?"** Because it can be wrong in two directions and gives
you no order. "At least medium" has one clear answer and keeps the scale.

**How do I get a number out of it?** Sum the boundary probabilities. On an ordered scale that is
the expected level, and it sorts a queue well.

**What if P(at least high) is larger than P(at least medium)?** Enforce the order with a running
minimum, log the inversion, and consider a review band for those cases.

**Does jevos support the `score` question type?** Yes, early: on 2,350 held-out score questions
the most probable level is right 58.5% of the time and within one level 86%; on 329 everyday
ratings 63% and 97% within one level; on rubrics (jevos-v2) 69%; on points to add up (jevos-v2)
34%, barely above the most common level.

**See also:** [zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md),
[urgency detection in customer messages](urgency-detection-in-customer-messages.md) and
[how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).

## Sources

- The `score` question type and its accuracy on 2,350 held-out questions: the
  [jev README](https://github.com/feder-cr/jev).
- The six-task comparison (fraud points 0.50 against 0.69 for Jev): the jev README.
- 0.654 and 0.954 by kind of question: our 999-question test set, first jevos.
- Cumulative thresholds in ordinal models:
  [Ordinal regression on Wikipedia](https://en.wikipedia.org/wiki/Ordinal_regression), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which answers yes/no, multiple-choice
and score questions, and lets you build scores from yes/no ones.*
