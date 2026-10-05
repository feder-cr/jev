---
title: "Intent detection with a local LLM"
description: "Detect user intents with a local LLM: one yes/no question per intent, new intents without retraining, overlapping intents, and a fallback when none fits."
parent: "Use cases"
nav_order: 9
---

# Intent detection with a local LLM

**For intent detection with a yes/no model, each intent in your catalogue is a question ("Does
the user want to change their delivery address?"), all of them go in one request, and code
picks the intents whose P(yes) clears a threshold, or hands off when none does.** Adding an
intent means adding a question, with no retraining and no example utterances to collect. Intent
questions scored 0.859 for the first jevos on our test set of 999 new yes/no questions
(per-kind numbers for jevos-v4 are not published; its overall score on the set is 78.9%), which
is good enough for routing and suggestions, and not good enough to trigger irreversible actions without a check.

The shift from a trained intent classifier is that intents stop competing. A classifier trained
on ten intents must put every message in one of them; independent questions can say that a
message has two intents, or none, and both answers are useful in a chat assistant.

This page is the catalogue as a request, adding intents, overlapping intents, the no-match
fallback, what the measured number covers, how far a catalogue scales, and where running
locally matters.

## An intent catalogue is a list of questions

```json
{
  "model": "jev-latest",
  "state": {
    "channel": "in-app chat",
    "previous_bot_message": "Your order 7731 is out for delivery today.",
    "user_message": "ah no, I won't be home, can you leave it with a neighbour or send it to my office instead?"
  },
  "questions": {
    "change_address": {"type": "noul", "instructions": "Does the user ask to deliver the order to a different address?"},
    "delivery_instructions": {"type": "noul", "instructions": "Does the user ask to leave the parcel with someone or in a specific place?"},
    "reschedule":     {"type": "noul", "instructions": "Does the user ask to deliver the order on a different day?"},
    "cancel_order":   {"type": "noul", "instructions": "Does the user ask to cancel the order?"},
    "track":          {"type": "noul", "instructions": "Does the user ask where the order is or when it will arrive?"}
  }
}
```

Two habits carry most of the accuracy. Every question starts the same way ("Does the user ask
to ..."), which keeps the probabilities comparable with each other. And the previous bot message
is in `state`, because "send it to my office instead" only has an intent in the context of what
came before. How to phrase intent questions in general, including requests versus complaints,
is on [asking about intent: what does the writer want?](yes-no-questions-about-intent.md).

## Adding an intent without retraining

Adding "return an item" is one line in the questions. What it does not remove is the need to
check that the new question does not take messages from the old ones. A cheap routine:

1. Keep a file of a few hundred real messages with the intents a person assigned.
2. Before shipping a new or reworded question, run the file through `jev decide` or the server.
3. Compare, per intent, how many messages changed their top intent.

If "return an item" starts winning messages that were "cancel order", the two questions overlap,
and the fix is in their wording ("return an item you already received" versus "cancel an order
that has not shipped"). The same routine catches a question that was reworded for one case and
broke three others; [why wording changes an LLM's answer](why-wording-changes-the-answer.md)
covers how to test paraphrases.

Sales teams apply the same catalogue idea to buying signals, such as budget, timeline and who
decides, on [lead qualification with yes/no questions](lead-qualification-with-yes-no-questions.md).

## When two intents are both yes

The example message above has two plausible intents: change the address, or leave the parcel
with a neighbour. A single-label classifier would pick one. With independent questions, code
can do the right thing for a chat assistant:

```python
def intents(p, act=0.7, ask=0.4):
    sure = [k for k, v in p.items() if v >= act]
    maybe = [k for k, v in p.items() if ask <= v < act]
    if len(sure) == 1:
        return {"do": sure[0]}
    if len(sure) > 1:
        return {"ask_user_to_choose": sorted(sure, key=p.get, reverse=True)}
    if maybe:
        return {"confirm": max(maybe, key=p.get)}
    return {"handoff": True}
```

Two confident intents become a short clarifying question to the user ("Change the address, or
leave it with a neighbour?"). One uncertain intent becomes a confirmation ("Do you want to
reschedule the delivery?"). The thresholds are placeholders to be set from your labelled
messages.

## When nothing fits

The last line of that function is the one that matters most. Below the lower threshold on every
intent, the message is outside your catalogue: small talk, a new kind of request, or a
complaint with no ask. Hand it to a person or to a general reply, and log it. Those logs are
your backlog of missing intents. A separate "other" question phrased as a negative ("Is this
about none of the above?") is the weaker design, because it gives the model nothing in the text
to find.

## What the 0.859 does and does not cover

The first jevos scored 0.859 on the 71 intent questions in our set of 999 written after
training, and 0.858 on negation, which appears in intents such as "does not want a refund".
Those are measurements on our
texts (emails, tickets, logs, reviews, forms), not on chat messages, and not on your catalogue.
They are the reason to use thresholds with a confirm step rather than acting on the top intent
alone.

The model reads stated intent better than implied intent. "Cancel my subscription" is stated.
"I guess I won't be needing this anymore" implies it. If implied intents matter to you, ask for
them explicitly ("Does the user suggest they may stop using the service?") as their own
question, and route them to a person; the retention case is worked through on
[detecting cancellation intent in customer messages](cancellation-intent-detection.md).

## How big can a catalogue get?

The 8,192-token context applies to the text plus each question, not to all the questions
together, so a few dozen intents with a chat message fit easily. Cost grows with the total tokens read: on our reference laptop a
short request took 28 ms and a long one 130 ms, and questions are tokens too. For a catalogue of hundreds of intents, ask in
two stages: a handful of coarse questions first (orders, account, billing), then only the
detailed intents under the winning area. The same idea, used for choosing between models, is on
[an LLM router with yes/no questions](llm-router-with-yes-no-questions.md).

## Where local matters for intents

Intent detection sits inside a conversation turn, so its latency is added to every reply. On
our reference laptop a short request takes about 28 ms, well inside a chat turn, while the
hosted Jev API took about 311 ms on the same short request, mostly network.
The user's messages, which often contain order numbers and addresses, also stay on your server.

Where local does not help: languages other than English, and assistants that need the model to
also write the reply. jevos only decides; the reply comes from your templates or another model.

## Short answers to the questions that lead here

**What is intent detection?** Working out what a user wants from their message, such as
cancelling an order or changing an address, so the system can act or route it.

**Can I add intents without retraining?** Yes. Each intent is a question; add one, then replay a
labelled set of messages to check it does not overlap the others.

**How do I handle messages with several intents?** Keep every intent above the threshold, and
ask the user to choose when more than one is confident.

**How accurate is it?** Intent questions scored 0.859 for the first jevos on our own test set;
jevos-v4 per-kind numbers are not published. Measure on your own
messages and catalogue.

**See also:** [semantic routing vs yes/no questions](semantic-routing-vs-yes-no-questions.md),
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md)
and [mainly about: questions for messages with several topics](mainly-about-questions-for-mixed-messages.md).

## Sources

- Intent 0.859 (71 questions), negation 0.858: our 999-question test set, first jevos.
- Latency 28 ms short and 130 ms long read from scratch, hosted Jev
  311 ms on the short request, 8,192-token context: the [jev README](https://github.com/feder-cr/jev) and our
  reference-laptop measurements.
- Thresholds in the code are placeholders.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The most useful answer an intent
detector gives is "none of these", because it is the list of intents you have not written yet.*
