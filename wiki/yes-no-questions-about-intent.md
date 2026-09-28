---
title: "Asking about intent: what does the writer want?"
description: "Yes/no questions about what a writer wants: requests, complaints and threats to cancel, stated versus implied intent, and what we measured."
parent: "Question design"
nav_order: 10
---

# Asking about intent: what does the writer want?

**Ask about intent with a verb of wanting and a named writer ("Does the customer ask for a
refund?", "Does the customer say they want to cancel?"), and decide up front whether you mean
what the writer states or what they only imply.** Stated intent is a reading question and one
jevos handles well: on the intent questions of our 999-question test set it was right 0.859 of
the time. Implied intent is a judgment, useful and less reliable, and it deserves its own
question and its own threshold rather than being folded into the stated one.

Intent is usually the question a support system actually needs answered. Topic says which
team; tone says how the writer feels; intent says what should happen next. A message about
billing that asks for nothing needs a different action from one that asks for a refund, and a
calm message that says "please close my account" matters more than an angry one that does not.

This page is the three intents most systems care about, how to phrase each, the line between
stated and implied, and what the measurement does and does not cover.

## Requests, complaints and threats to leave

Most customer messages carry one of a few intents, and they are worth separate questions
because they lead to separate actions:

```json
{
  "model": "jev-latest",
  "state": "This is the second time my order arrived damaged. I want a replacement sent this week, otherwise I will cancel my subscription.",
  "questions": {
    "asks_replacement": {"type": "noul", "instructions": "Does the customer ask for a replacement?"},
    "asks_refund":      {"type": "noul", "instructions": "Does the customer ask for a refund?"},
    "complains":        {"type": "noul", "instructions": "Is the customer complaining about a product or service?"},
    "cancel_threat":    {"type": "noul", "instructions": "Does the customer say they will cancel if the problem is not fixed?"}
  }
}
```

- **A request** names something the writer wants done. Phrase it with "ask for", "request" or
  "want", followed by the thing: a replacement, a refund, a callback, a change of address.
- **A complaint** reports that something went wrong, with or without a request. Many
  complaints ask for nothing, and treating them as requests creates work nobody asked for.
- **A threat to leave** is conditional: "otherwise I will cancel". It is a different question
  from "Does the customer ask to cancel?", which is an unconditional request, and the two lead
  to different teams. The detection side is on
  [detecting cancellation intent in customer messages](cancellation-intent-detection.md).

Asking "refund" and "replacement" as separate questions matters even when both go to the same
team. The customer above asked for a replacement, not money, and a reply that offers a refund
answers the wrong request.

## Stated or implied?

"I want a refund" states the intent. "I have had this for two days and it already stopped
working" implies it: a reader guesses the writer would like a refund or a replacement, but the
writer has not said so.

Both are real, and they are different questions:

| Question | Asks about | Typical use |
|---|---|---|
| Does the customer ask for a refund? | stated intent | automatic actions, templates |
| Does the customer seem to expect a refund, even if they do not ask for one? | implied intent | prioritising, suggesting a reply |

The first question has an answer in the words on the page. The second asks the model to infer,
and people disagree on inferences too. Keep them apart so that an automatic action never runs
on an inference. The same principle, asking whether the text says a thing at all, is on
[ask whether the text says it at all](ask-whether-the-text-says-it.md).

Verbs set the bar. "Mention a refund" is weaker than "ask for a refund", which is weaker than
"demand a refund". Pick the verb that matches the action you will take, and test the choice as
on [why wording changes the answer](why-wording-changes-the-answer.md).

## What we measured

On the 999 yes/no questions written after the model was finished (10 scenarios, 10 texts each,
emails, tickets, logs, reviews and forms, exactly half of the answers yes), 71 were intent
questions. jevos `q4_k_m` answered 0.859 of them correctly, and its average P(yes) on intent
questions whose correct answer was no was 0.28.

For comparison on the same set: stated facts 0.954, tone 0.938, negation 0.858. Intent sits
with the reading kinds, below the plainest of them. Two things the set does not tell you: how
the 0.859 splits between stated and implied intent, since we did not label them separately,
and how it holds on text very different from business writing.

The 0.28 is worth a second look when a wrong yes is expensive. It is about the same as on
stated facts (0.29) and far from the 0.59 on arithmetic, so intent questions do not carry a strong lean
toward yes, but for an automatic refund a threshold above 0.5 is still sensible. How to pick it
is on [thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).

## Intent with tone and topic

Intent works best as one of three questions about a message, each answering a different part
of the decision:

- **topic** picks the team ("Is this mainly about a payment?"),
- **intent** picks the action ("Does the customer ask for a refund?"),
- **tone** picks the urgency and the care ("Is the customer angry?").

They share one reading of the text, so asking all three costs little more than asking one. Tone
has its own page, [yes/no questions about tone and emotion](yes-no-questions-about-tone.md), and
the routing that ties the three together is on
[intent detection with a local LLM](intent-detection-with-a-local-llm.md).

## Short answers to the questions that lead here

**How do I detect what a customer wants?** Ask one yes/no question per intent, with a verb of
wanting and the thing wanted: "Does the customer ask for a replacement?".

**How accurate is a small LLM on intent?** On our 999-question test set jevos answered 0.859 of
71 intent questions correctly.

**Is a complaint the same as a request?** No. Many complaints ask for nothing. Ask both, and act
on the request.

**Can the model detect implied intent?** You can ask it, as a separate question. Treat the
answer as a judgment and do not run automatic actions on it.

**What is the difference between a cancellation request and a threat to cancel?** The request is
unconditional; the threat depends on something else happening. Ask them as two questions.

**See also:** [refund request triage with a local LLM](refund-request-triage-with-a-local-llm.md),
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md)
and [how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## Sources

- 0.859 on 71 intent questions, the other accuracies by kind, and the mean P(yes) values on
  no-answer questions: our 999-question test set, `jevos-q4_k_m`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where the difference between "asks
for" and "mentions" is one word in `instructions` and a different action downstream.*
