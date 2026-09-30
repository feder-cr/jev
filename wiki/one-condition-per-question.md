---
title: "One condition per question: splitting compound questions"
description: "Why a yes/no question with 'and' or 'or' in it hides which part failed, how to split it into single conditions, and how to combine the answers in code."
parent: "Question design"
nav_order: 3
---

# One condition per question: splitting compound questions

**If a yes/no question contains "and" or "or" between two conditions, split it into one
question per condition and combine the probabilities in your code.** "Is the customer upset
and asking for a refund?" returns a single number, and when that number is low you cannot tell
whether the model found no anger, no refund request, or both. Two questions return two numbers,
each of which means one thing, and the combination is a line of arithmetic you control.

Survey designers have a name for the compound form: a double-barreled question, one that
touches more than one issue but allows only one answer. The problem is the same with a model as
with a person. The answer you get back is to a question you cannot see, the one the reader
decided to answer.

This page is how to spot a compound question, how to split it, how to put the pieces back
together, and what the split costs in latency.

## How do I recognise a compound question?

The obvious sign is a conjunction between conditions. The less obvious ones:

- **A rule with several clauses.** "Refund if the item was reported missing within 30 days and
  the order was over 20 dollars" is three conditions in one sentence.
- **Two subjects.** "Were the customer and the agent both polite?" is two questions about two
  people.
- **A condition hidden in a noun.** "Is this a repeat complaint about a late delivery?" asks
  whether it is a complaint, whether it is about a delivery, whether the delivery was late, and
  whether it has happened before.
- **"Or" between labels.** "Is this about billing or shipping?" is fine as a routing question
  only if you do not care which; usually you do.

The Wikipedia examples of double-barreled questions read like support-ticket questions:
"How satisfied are you with your pay and job conditions?" and "Is this tool interesting and
useful?". Both combine two things a person could feel differently about.

## Split it

Take the refund rule above. As one question:

```json
{"refund": {"type": "noul", "instructions": "Should the customer get a refund if the item was reported missing within 30 days and the order was over 20 dollars?"}}
```

As single conditions, with the numbers left to code:

```json
{
  "model": "jev-latest",
  "state": {
    "order_total": "34 dollars",
    "delivered": "5 days ago",
    "customer_message": "The box arrived empty. This is the second time!"
  },
  "questions": {
    "missing":   {"type": "noul", "instructions": "Does the customer say an item was missing from the delivery?"},
    "repeat":    {"type": "noul", "instructions": "Does the customer say this has happened before?"},
    "upset":     {"type": "noul", "instructions": "Is the customer upset?"}
  }
}
```

The 30-day window and the 20-dollar floor are no longer questions at all. Your system has the
delivery date and the order total as fields, and code compares them exactly. That matters
because a rule question is where a small model is weaker: 0.721 on applying a stated rule on
our 999-question set, against 0.954 on reading a stated fact, and 0.584 when the question
needs arithmetic. Splitting moves each condition toward the reading end of that range. The
wider version of this argument is on
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

## Put the answers back together

Each probability is independent, so you choose how to combine them. The three usual rules:

```python
p = {k: a["noul"] for k, a in answers.items()}

strict = min(p["missing"], p["upset"])        # AND, cautious
joint  = p["missing"] * p["upset"]            # AND, if the conditions are independent
escalate = max(p["upset"], p["repeat"])       # OR, cautious
```

`min` is the safe default for AND: the combination is only as sure as its least sure part. The
product assumes the two conditions are independent, which they often are not (an upset
customer is more likely to be reporting a problem), and it drifts low when you chain several.
Which one to use, and how NOT fits in, is the subject of
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

Keep the individual probabilities in your logs next to the combined decision. When a case is
decided wrong, they show which condition caused it, which is the whole point of the split.

## What does splitting cost?

Less than you would think. Questions in the same request share the `state`, and the text is
read once. On the reference laptop (Intel Core Ultra 7 255H, 16 threads), the
README's three questions about one text take about 66 ms together, against 49 ms for one of
them alone. Three conditions for about 1.3 times the price of one is a trade worth making for
any decision you will need to explain. Why the extra questions are cheap is on
[many questions about one text](many-questions-about-one-text.md).

## When one question is fine

Not every "and" is two conditions. "Did the customer thank the agent and say goodbye?" might be
a single thing you care about, a polite close, and splitting it gains nothing if you would
never act on the parts separately. The test is simple: if the two parts could have different
answers, and you would do something different depending on which one failed, split. If not, a
single question with a clear name is fine.

The same test applies to "or". "Does the customer mention a refund or a replacement?" is one
condition if both lead to the same queue.

## Short answers to the questions that lead here

**What is a double-barreled question?** A question that touches more than one issue but allows
only one answer. With a yes/no model, it returns one probability for two conditions.

**Should I use "and" in an LLM prompt?** In a yes/no question, only when the two parts are one
thing you care about. Otherwise ask them separately.

**How do I combine two yes/no probabilities?** For AND, the minimum is the cautious choice and
the product assumes independence. For OR, the maximum. Keep the parts in your logs.

**Does asking more questions make the request slow?** Less than linearly. On the README
example, three questions take about 66 ms against 49 ms for one, because the text is read
once.

**See also:** [how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md),
[negation in yes/no questions](negation-in-yes-no-questions.md) and
[rubric design for an LLM judge](rubric-design-for-an-llm-judge.md).

## Sources

- Accuracy on rule, fact and arithmetic questions: our 999-question test set, `jevos-q4_k_m`.
- The 66 ms and 49 ms timings: the [jev README](https://github.com/feder-cr/jev).
- Definition and examples of double-barreled questions:
  [Double-barreled question on Wikipedia](https://en.wikipedia.org/wiki/Double-barreled_question),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model that returns exactly one
probability per question, which is the reason each question should mean exactly one thing.*
