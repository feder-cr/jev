---
title: "Ask whether the text says it at all"
description: "Gate questions for missing information: ask whether the text states a fact before asking about it, so an LLM does not answer a question the text cannot."
parent: "Question design"
nav_order: 4
---

# Ask whether the text says it at all

**Before asking a yes/no question the text might not answer, ask a gate question first: "Does
the message say when the parcel was delivered?"** If the gate says no, the real question has no
answer in the text, and whatever probability the model gives it is a guess. jevos is good at
the gate: 0.847 on questions about whether a text states something, on our 999-question test
set, with an average P(yes) of 0.23 on those whose answer is no.

The reason this matters is that a yes/no model always answers. There is no "I don't know" in a
probability, and a question about a fact that is not in the text still comes back as a number
between 0 and 1. It may land near 0.5, which at least looks uncertain. Nothing forces it to, and
a confident-looking answer to an unanswerable question is the worst output a decision
system can produce, because nothing downstream will question it.

This page is why the missing case is different from the no case, how to write a gate, how to
wire it in code, and what the measurements say.

## "No" and "not stated" are different answers

Take a refund rule that depends on the delivery date and a message that never mentions it:

```json
{
  "model": "jev-latest",
  "state": "Hi, my order came but the charger inside is broken. Can you help?",
  "questions": {
    "within_window": {"type": "noul", "instructions": "Was the order delivered less than 30 days ago?"}
  }
}
```

The true answer to "within_window" is neither yes nor no: the text does not say. A low
probability would read as "outside the window, decline the refund", which is a wrong decision
built on a missing fact. A high one would approve a refund on nothing.

Your system needs three outcomes here, not two: yes, no, and ask for more information (or look
it up in the order database). A single yes/no question cannot produce the third outcome, so
you add a question that can.

## Write the gate

A gate question asks about the presence of information, not its value:

```json
"questions": {
  "states_delivery": {"type": "noul", "instructions": "Does the message say when the order was delivered?"},
  "states_order_id": {"type": "noul", "instructions": "Does the message include an order number?"},
  "states_problem":  {"type": "noul", "instructions": "Does the customer describe what is wrong with the item?"}
}
```

Three habits make gates work:

- **Ask about the text, not the world.** "Does the message say..." or "Does the customer
  mention..." points the model at the words on the page. "Was the order delivered?" asks about
  reality, and the model may answer from what usually happens.
- **Ask one fact per gate.** The rule is the same as for any question, covered on
  [one condition per question](one-condition-per-question.md).
- **Ask positively.** "Does the message include an order number?" rather than "Is the order
  number missing?", and take 1 minus P(yes) in code if you need the other side. The reason is on
  [negation in yes/no questions](negation-in-yes-no-questions.md).

## Wire it in code

The gate and the real question can go in the same request, since they share one reading of the
text. The logic that uses them is yours:

```python
p = {k: a["noul"] for k, a in answers.items()}

if p["states_problem"] < 0.5:
    action = "ask the customer what is wrong"
elif p["states_delivery"] < 0.5:
    action = "look up the delivery date"
else:
    action = "apply the refund rule"
```

In most systems the second branch is the common one, and the best design is to not ask the
model at all: the delivery date lives in your order database, and code computes the window
exactly. Gates are most useful for facts that exist only in the message, such as what is wrong,
what the customer wants, or whether they gave a reason.

## What the measurements say

On the 999 yes/no questions written after the model was finished, 98 were "not stated"
questions, and jevos `q4_k_m` was right on 0.847 of them. When the right answer was no, the
average P(yes) it gave was 0.23, low next to 0.59 on arithmetic questions and 0.53 on dates.
On a second set of 1,000 template questions, with answers computed by code from structured
texts about orders, leave requests, loans, bookings and similar records, it answered every
"not stated" question correctly.

Two caveats. The template set is regular by construction, so its perfect score says more about
easy cases than about messy customer mail; the 0.847 is the number to plan with. And the
gate does not fix the other failure, a question the text answers but that needs computing.
That lean toward yes is measured on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Where the gate goes in a decision

The gate is also a natural input to a review band. A case where the gate is uncertain, say
between 0.3 and 0.7, is a case where even the model is not sure the fact is there, and that is
a good case to send to a person. How to set those bands is on
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md), and the
general rule of putting policy text in the question, which gates protect, is on
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

Being straight about the limit: a gate reduces confident answers to unanswerable questions; it
does not make them impossible. It is one more probability, with its own error rate. For
decisions that cost money, the missing-information branch should lead to a person or a lookup,
never to an automatic no.

## Short answers to the questions that lead here

**How do I stop an LLM from answering when the text has no answer?** Ask first whether the
text states the fact. Act on the real question only when the gate says yes.

**Does a probability near 0.5 mean the information is missing?** Not reliably. A missing fact
can produce a confident answer. Ask the gate question explicitly.

**How good is jevos at spotting missing information?** 0.847 on 98 not-stated questions in our
999-question test set, and all correct on the not-stated questions of a 1,000-question template
set.

**Should the gate and the question be in the same request?** Yes. They share one reading of the
text, so the gate adds a fraction of the cost of the first question.

**What should the code do when the fact is missing?** Look it up in your own data, or ask the
customer. Do not treat missing as no.

**See also:** [how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md),
[what P(yes) means](what-p-yes-means.md) and
[hallucination detection with a local LLM](hallucination-detection-with-a-local-llm.md).

## Sources

- 0.847 on 98 not-stated questions and the mean P(yes) values on no-answer questions: our
  999-question test set, `jevos-q4_k_m`.
- All-correct result on not-stated questions: our second test of 1,000 template questions with
  answers computed by code.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model that always returns a
number, which is exactly why the question of whether there is anything to answer has to be
asked out loud.*
