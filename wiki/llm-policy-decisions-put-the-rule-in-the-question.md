---
title: "LLM policy decisions: put the rule in the question"
description: "Using a local LLM to apply refund, access or warranty rules: write the rule into the yes/no question, split compound rules, and keep arithmetic in code."
parent: "Guides"
nav_order: 3
---

# LLM policy decisions: put the rule in the question

**To have a language model apply a business rule, write the rule into the question, ask one
condition per question, and do the arithmetic in your own code.** The model knows nothing about
your refund window or your access policy except what the request tells it, and a question that
contains the rule ("Our policy refunds items reported missing within 30 days of delivery.
Should this customer get a refund?") is one it can answer from the text. A question that only
names the rule ("Is this eligible under policy R-12?") is one it can only guess.

Rules are also where a small model is weakest. On 2,000 yes/no questions about three business
policies jevos never saw, with the exact answer computed by code from the rule and the facts,
it was right 0.811 of the time, against 0.927 for TypeSafe's hosted Jev. That is useful as a
first pass and it decides how to design around it.

This page is how to write the question, how to split a rule the model gets wrong into parts it
gets right, what the measurements say about each kind of condition, and where to draw the line
between the model and code.

## The rule goes in `instructions`

```json
{
  "model": "jev-latest",
  "state": {
    "item": "wireless mouse",
    "delivered": "5 days ago",
    "customer_message": "The box arrived empty. This is the second time!"
  },
  "questions": {
    "refund": {
      "type": "noul",
      "instructions": "Our policy refunds items reported missing within 30 days of delivery. Should this customer get a refund?"
    }
  }
}
```

The README's run of this request answers 0.78. The model has to find three things in the text,
that the item is missing, that it was reported, and that the delivery was five days ago, and
check the last against 30 days.

Jev's API has an optional `criteria` field for describing what yes and no mean. This server
accepts it for compatibility and does not read it, so anything the decision depends on belongs
in `instructions`.

## Measured: which conditions the model gets right

On a separate set of 999 questions written after training, each labelled with the kind of
reasoning it needs, the spread is wide:

| What the question needs | Accuracy |
|---|---|
| a fact stated in the text | 0.954 |
| a negation ("did the customer not ask for...") | 0.858 |
| noticing the text does not say | 0.847 |
| applying a stated rule | 0.721 |
| comparing a number with a threshold | 0.654 |
| reasoning about dates and durations | 0.598 |
| a sum or other arithmetic | 0.584 |

Reading is strong. Computing is weak. And a business rule is usually both: a reading part (is
the item missing?) and a computing part (is five days within thirty?). On the 2,000 policy
questions the gap to Jev was largest on additive point scores, where several signals are summed
and compared with a cut-off, which is arithmetic wearing a policy's clothes.

## Split the rule into what the model reads and what code computes

The design that follows from that table: let the model answer the reading questions, extract
the numbers, and let code apply the thresholds.

A rule like "refund if the item was reported missing within 30 days of delivery and the order
was over 20 dollars" becomes:

```json
"questions": {
  "missing":    {"type": "noul", "instructions": "Does the customer say an item was missing from the delivery?"},
  "first_time": {"type": "noul", "instructions": "Does the customer say this has not happened before?"}
}
```

plus the delivery date and the order total, which your system already has as fields and which
code compares exactly. The model does the part only a reader can do, turning a message into
facts, and nothing it does can be off by one day.

When the numbers exist only in the text, you can still split: ask the model the comparison
directly only if a mistake is cheap, and otherwise send it to a person when the probability is
in the middle.

## Ask whether the text says it at all

A rule applied to facts the text does not contain produces a confident answer to a question
that has none. Before "Was it reported within 30 days?", it can pay to ask "Does the message
say when the parcel was delivered?". The model is at 0.847 on noticing that a text does not
state something, which makes that question a reliable gate in front of the rule.

## Thresholds for decisions with a cost

A refund is not a classification: a wrong yes pays money. Use the probability as a band, not a
bit:

- above 0.9: act automatically,
- 0.1 to 0.9: send to a person, with the model's answers attached,
- below 0.1: decline, or ask for more information.

Where you put the bands depends on what a mistake costs you, and the model's lean toward yes on
questions it cannot compute, measured on [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md),
is a reason to set the upper band higher than the lower one is low.

## What this is not

The model is not a rules engine and should not be the only check on a decision with legal or
financial weight. On rules it has never seen it is wrong about one time in five. It is a fast,
local way to turn free text into the facts a rule needs, and to handle the easy majority of
cases, so that people spend their time on the rest. How the model and a rules engine divide that
work is on [a yes/no LLM vs a business rules engine](yes-no-llm-vs-business-rules-engine.md), and the
whole refund flow end to end is on [refund request triage](refund-request-triage-with-a-local-llm.md).

## Short answers to the questions that lead here

**Can an LLM apply a business policy?** It can apply a rule written into the question. jevos
answered 0.811 of 2,000 questions on policies it had never seen correctly; a large hosted model
answered 0.927.

**Where do I put the policy?** In the question's `instructions`. The `criteria` field is
accepted but not read by this server.

**Why does it get dates and totals wrong?** Computation is its weakest skill, 0.58 to 0.65 on our
test set against 0.95 for stated facts. Extract the numbers and compare them in code.

**Should I trust it for refunds?** As a first pass with a band for human review, yes; as the
final decision on every case, no.

**How do I handle missing information?** Ask first whether the text states the fact, then ask
the rule.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md) and
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- The refund request and its 0.78 answer, and the 2,000-question comparison with Jev and Laya:
  the [jev README](https://github.com/feder-cr/jev).
- Accuracy by kind of question: our 999-question test set, written after training, run on
  `jevos-q4_k_m`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The split between what the model reads and what code computes is the design we
would recommend for any model this size.*
