---
title: "Sending JSON as the text: designing the state"
description: "What to put in the JSON state of a yes/no request: field names that read as English, no noise, and computed values like days since delivery, not raw dates."
parent: "Question design"
nav_order: 6
---

# Sending JSON as the text: designing the state

**Put in the `state` only what the questions need, name every field so it reads as English,
and send computed values ("delivered": "5 days ago") instead of raw data the model would have
to calculate from.** The state can be a plain string or any JSON object or array, and all of
it is read the first time the model sees it: every field costs time, and every field the model has to
interpret is a place it can go wrong. A state designed for reading is short, plain and already
reduced to facts.

The non-obvious point is that the state is where most computation should disappear. The
question "Was it delivered within 30 days?" is only as hard as the state makes it. Two ISO
timestamps turn it into a date subtraction, which is the model's weakest skill; "delivered: 5
days ago" turns it into reading.

This page is what to include and leave out, how to name fields, which values to compute before
sending, and what size costs.

## What should go in the state?

Everything a question depends on, and nothing it does not. The README's refund example is a
good pattern:

```json
{
  "model": "jev-latest",
  "state": {
    "item": "wireless mouse",
    "delivered": "5 days ago",
    "customer_message": "The box arrived empty. This is the second time!"
  },
  "questions": {
    "refund": {"type": "noul", "instructions": "Our policy refunds items reported missing within 30 days of delivery. Should this customer get a refund?"},
    "upset": {"type": "noul", "instructions": "Is the customer upset?"}
  }
}
```

Three fields: what was bought, a duration the rule needs, and the customer's own words. The
README reports 95 input tokens for this state with three questions. What is not there matters
as much: no order ID, no warehouse code, no internal status flags, no customer email address.
None of them helps answer any question, all of them cost tokens, and a field such as
`"status": "REFUND_PENDING"` can nudge the model toward an answer it should have reached from
the message.

If the record carries personal data the questions do not need, leaving it out is also the
simpler privacy position, even on a model that runs on your own machine.

Log lines and alerts are the other common JSON state; which of their fields to keep is shown on
[log and alert triage with a local LLM](log-and-alert-triage-with-a-local-llm.md).

## Field names that read as English

Assume the model reads the keys as well as the values. Name fields the way you would describe them to
a new colleague:

| Instead of | Use |
|---|---|
| `cust_msg` | `customer_message` |
| `dlv_ts` | `delivered` |
| `amt` | `order_total` |
| `flg_rpt` | `reported_before` |
| `s` | `subject_line` |

Units belong in the value, in words: `"order_total": "34 dollars"`, not `"order_total": 34`.
And the field names should match the words in your questions. If the question says "the
customer", the state should say `customer_message`, not `body`, so the model does not have to
work out who wrote what. That habit of naming the subject is the fourth rule on
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## Compute before you send

Anything your code can compute exactly, it should compute before the request:

- **Durations, not dates.** `"delivered": "5 days ago"` rather than `"ordered_at"` and
  `"delivered_at"` timestamps. On our 999-question test set, questions about dates and
  durations scored 0.598; questions about facts stated in the text scored 0.954.
- **Results, not ingredients.** `"items_missing": "1 of 3"` rather than two lists to compare.
- **Flags that are facts.** If your system knows the customer has complained before, send
  `"previous_complaints": "2"`, or better, decide the rule part in code and skip the question.
- **Comparisons already made, when they are the whole point.** If the only thing a question
  needs is whether the total is over a limit, `"over_free_shipping_limit": "yes"` is a field
  your code fills in exactly. At that point you may not need a question at all.

The reason is measured on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md):
computing is where a small model is weak and where it leans toward yes. The state is your
chance to move that work into code, where it is exact.

## String or object?

A plain string is right when there is one text and no structure: a review, a single email, a
chat message. The README's billing example is just `"I was charged twice for the same order."`
and 27 input tokens.

An object is right when some facts come from your system and some from a person. Keeping them
in separate fields lets a question point at one ("Does the customer say...") and keeps system
data from being mistaken for something the customer wrote. An array works for a short history
of messages, one object per message with an `author` field.

Nesting deeper than that rarely helps. A flat object with clear names reads better than a
nested one with short keys.

## What size costs

Every token in the state is read before any question is answered. On the reference laptop
(Intel Core Ultra 7 255H, 16 threads), with the text read from scratch, that is 26 ms for a
request of about 30 tokens and 112 ms for one of about 190. A text asked about again is kept,
so the second question on it reads only the question: 22 ms for the same 191-token request.
Cutting a noisy 400-token record
to the 100 tokens the questions need is the single largest speed-up available to you, larger
than any server option. Why latency grows with length is on
[why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).

The hard limit is 8,192 tokens by default for the state plus each question, counted per question,
and 256 KB for the state itself. Records that approach
it are long documents, and those have their own design, on
[yes/no questions about long documents](yes-no-questions-about-long-documents.md).

## Short answers to the questions that lead here

**Can I send JSON to an LLM instead of text?** To jevos, yes: `state` accepts a string or any
JSON object or array, and questions are asked about it directly.

**Does the model read the field names?** Treat it as if it does. Names that read as English and
match the words in your questions make the state easier to answer from.

**Should I send raw timestamps?** No. Compute the duration in code and send it as words, such as
"5 days ago". Date reasoning is one of the model's weakest kinds of question.

**How much does a bigger state cost?** On the reference laptop, about 26 ms for 30 tokens and
112 ms for 191 tokens read from scratch. Removing fields no question needs is the cheapest speed-up.

**Is there a size limit?** 8,192 tokens for the state plus each question, by default, and 256 KB
for the state.

**See also:** [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md),
[checking text for personal data with yes/no questions](pii-check-with-yes-no-questions.md) and
[ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Sources

- The refund and billing examples and their token counts, the 26 ms, 112 ms and 22 ms latencies, and
  the 8,192-token context: the [jev README](https://github.com/feder-cr/jev) and our
  measurements on the reference laptop.
- 0.598 on dates and 0.954 on stated facts: our 999-question test set, `jevos-q4_k_m`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose README example already sends
"5 days ago" where a raw record would have carried a date.*
