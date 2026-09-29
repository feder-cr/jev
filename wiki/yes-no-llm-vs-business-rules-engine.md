---
title: "A yes/no LLM vs a business rules engine"
description: "Rules engines evaluate structured facts exactly; a yes/no LLM turns free text into those facts. Why the model should read and the engine should decide."
parent: "Comparisons"
nav_order: 12
---

# A yes/no LLM vs a business rules engine

**A business rules engine evaluates structured facts exactly and the same way every time; a yes/no
LLM reads free text and tells you, with a probability, whether a fact is there.** They are not
alternatives. The engine cannot read "the box arrived empty, this is the second time!", and the
model should not be the one comparing 5 days with a 30-day limit. The design that works is a
split: the model turns text into facts, and the engine, or plain code, applies the rules to them.

Conflict of interest, in one line: we build jevos, a yes/no model, and our own measurements are
the reason this page tells you not to let it apply your rules alone.

It is tempting to hand the whole policy to the model, because a question can contain a rule and
the model will answer it. That works often enough to be dangerous. On rule questions and on
arithmetic, a small model is measurably weaker than on reading, and a rules engine is not weak at
either.

This page is what each is good at, the split with a worked example, the numbers behind it, how to
turn probabilities into facts an engine can use, and what the split does for audits.

## What a rules engine is good at

A rules engine takes facts, evaluates conditions and fires outcomes. json-rules-engine, an
open-source JavaScript example, describes itself as "a rules engine expressed in JSON", with "full
support for `ALL` and `ANY` boolean operators, including recursive nesting", and facts and events
as its building blocks. Engines like it are exact: the same facts give the same outcome, every
rule can be read by a person, and a change in policy is a change in one rule, reviewed like code.

What an engine needs is structured input: `days_since_delivery = 5`, `item_missing = true`. It has
no way to get from a customer's sentence to `item_missing = true`. Someone, or something, has to
read.

## What a yes/no model is good at

Reading. On our 999 questions written after training, jevos was right 0.954 of the time on facts
stated in the text, 0.938 on tone, 0.859 on intent and 0.858 on negation. "Does the customer say
the item was missing?" is exactly that kind of question, and it works on text that no keyword
list would cover.

It is weaker exactly where the engine is strong. On the same set: 0.721 on applying a rule, 0.654
on comparing a number with a threshold, 0.598 on dates and 0.584 on arithmetic. On 2,000 questions
about three business policies, jevos reached 0.811 against 0.927 for TypeSafe's hosted Jev,
and the gap was widest on additive point scores, where several signals are summed and compared
with a cut-off. That is a rules engine's home ground.

## The split, with the README's refund case

The README asks the model a single question with the policy inside it: "Our policy refunds items
reported missing within 30 days of delivery. Should this customer get a refund?" about a wireless
mouse delivered 5 days ago, whose customer wrote "The box arrived empty. This is the second
time!" The answer was 0.78. That is a reasonable answer, and it mixes two jobs: reading the
complaint and checking the date.

Split, the model gets only the reading:

```json
{
  "model": "jev-latest",
  "state": {"customer_message": "The box arrived empty. This is the second time!"},
  "questions": {
    "missing": {"type": "noul", "instructions": "Does the customer say the item was missing from the package?"},
    "repeat":  {"type": "noul", "instructions": "Does the customer say this has happened before?"}
  }
}
```

The engine, or code, gets the rest. A sketch, not a library API:

```python
facts = {
    "item_missing": answers["missing"]["noul"] > 0.8,
    "missing_unsure": 0.3 <= answers["missing"]["noul"] <= 0.8,
    "days_since_delivery": (today - delivered_on).days,   # computed, not asked
}
if facts["missing_unsure"]:
    decision = "review"
elif facts["item_missing"] and facts["days_since_delivery"] <= 30:
    decision = "refund"
else:
    decision = "no_refund"
```

The date comparison is now exact, the policy is a line anyone can read, and the model answers a
question in its strongest category. The thresholds are illustrative; choose yours from labelled
cases, as on [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).

## Turning probabilities into engine facts

An engine wants booleans; the model gives probabilities. Three habits bridge them:

- **Two thresholds, not one.** Above the upper one the fact is true, below the lower one false,
  and in between it is "unknown", which the rules route to a person. The band is the subject of
  [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).
- **Stricter bars for expensive yeses.** On our 999-question set the model's errors leaned toward
  yes, 152 wrong yeses against 91 wrong noes, so a fact that triggers a payment deserves a higher
  bar than one that triggers a reply.
- **Positive facts.** Ask "does the customer say the item was missing?", not "is the item not
  present?"; negation is better handled by the engine's NOT than by the question.

## What the split does for audits

With everything in one question, the audit trail is "the model said 0.78". With the split, it is
the text, each question and its probability, the thresholds, the computed fields and the rule that
fired. A policy change is visible as a changed rule rather than a changed prompt, and a disputed
decision can be traced to the fact that was misread or the rule that applied. What to log is on
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## Short answers to the questions that lead here

**Can an LLM replace a rules engine?** No. The engine is exact on structured facts; a small model
was right 0.721 of the time on rule questions in our test and 0.584 on arithmetic.

**Can a rules engine read text?** Not by itself. It needs structured facts, and extracting them
from free text is what a yes/no model is good at.

**Where do the thresholds go?** In the engine's rules or your code, with a band in between that
routes to a person.

**Should I put the policy in the question at all?** For a quick decision it works, and the README
does it. For anything audited or involving numbers and dates, move the policy into rules.

**Is this slower?** The reading is one request with several questions, which share one reading of
the text. The rules themselves are cheap.

**See also:** [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md),
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md) and
[LLM decisions vs keyword rules and regex](llm-decisions-vs-keyword-rules.md).

## Sources

- The refund example and its 0.78: the [jev README](https://github.com/feder-cr/jev).
- Accuracy by kind (fact, tone, intent, negation, rule, number, dates, arithmetic) and the 152 to 91
  error split: our 999-question test set on `jevos-q4_k_m`.
- 0.811 against 0.927 on 2,000 policy questions, and the additive point score gap: our own
  measurement, published in the README.
- json-rules-engine description and features: its
  [GitHub repository](https://github.com/CacheControl/json-rules-engine), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model that reads the customer's
sentence and leaves the 30-day arithmetic to code.*
