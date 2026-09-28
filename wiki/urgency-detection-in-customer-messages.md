---
title: "Urgency detection in customer messages"
description: "Detect urgency in customer messages with yes/no questions: stated vs real urgency, deadlines computed in code, and levels asked as threshold questions."
parent: "Use cases"
nav_order: 7
---

# Urgency detection in customer messages

**Detect urgency by splitting it into what a model can read and what code must compute: ask
whether the customer says it is urgent, whether they are blocked, and whether they mention a
deadline, then compare any deadline date with today in code.** A yes/no model reads stated
urgency and impact well. It is weak at deciding whether "by the 14th" is tomorrow or next
month, because that is date arithmetic, and on our tests date questions were among the worst.
For levels such as low, high and critical, ask one question per boundary instead of asking for
the level.

The non-obvious part is that "urgent" in a message and urgent for your business are different
things. Some customers write URGENT on every email; others mention in passing, calmly, that
their shop has been offline since yesterday. A good urgency check listens for the second more
than the first.

This page is the difference between stated and real urgency, why deadlines stay in code, the
boundary questions, how code combines them, the review band, and the limits.

## Stated urgency versus real urgency

Ask them as separate questions, because they fail separately:

- **Stated:** "Does the customer say the matter is urgent or ask for a fast answer?" This is
  tone and wording. Tone questions scored 0.938 on our 999 yes/no questions written after
  training, on a sample of 32.
- **Impact:** "Does the customer say they cannot use the service at all?" or "Does the customer
  say they are losing sales or missing a deadline because of this?" These are stated facts,
  the model's strongest kind at 0.954.

A shouting message with no impact and a calm one with a blocked business get opposite answers
on these two, which is exactly the information you need. Tone questions in general are covered
on [yes/no questions about tone and emotion](yes-no-questions-about-tone.md).

## Deadlines are dates: compute them in code

"I need the replacement before the 14th" is urgent if today is the 12th and not if it is the
1st. A question such as "Is the deadline less than three days away?" asks the model to find the
date, know today, and subtract. On our 999-question set, date and time questions were right
0.598 of the time, and on the ones whose answer was no, the mean P(yes) was 0.53: the model
leans toward yes when it cannot do the sum. The pattern is measured on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

So the model gets one reading question, "Does the customer mention a date or deadline by which
they need something?", and code does the rest: parse the date from the text with a date parser,
compare it with today, and treat a mention that code could not parse as a case for a person.
If your form already has a "needed by" field, pass the computed number of days in `state`
instead of the raw date, and still compare it in code.

## Levels as boundary questions

For a scale, ask one question per step, each with the definition written in:

```json
{
  "model": "jev-latest",
  "state": {
    "customer_message": "Checkout has been failing for all our customers since 9am. We are losing orders every minute. Please call me."
  },
  "questions": {
    "says_urgent":    {"type": "noul", "instructions": "Does the customer say the matter is urgent or ask for an immediate answer?"},
    "at_least_high":  {"type": "noul", "instructions": "Does the customer say the problem stops them from doing part of their work?"},
    "critical":       {"type": "noul", "instructions": "Does the customer say the problem stops their business or all of their users right now?"},
    "mentions_deadline": {"type": "noul", "instructions": "Does the customer mention a date or deadline by which they need something?"}
  }
}
```

A scale of n levels needs n minus 1 boundary questions, each with one clear answer. The general
form, and what to do when the boundaries disagree, is on
[scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).

## How code combines the answers

```python
from datetime import date

def urgency(p, deadline=None, today=None):
    today = today or date.today()
    level = "normal"
    if p["at_least_high"] > 0.6:
        level = "high"
    if p["critical"] > 0.6 and p["at_least_high"] > 0.6:
        level = "critical"
    if deadline is not None and (deadline - today).days <= 2:
        level = max(level, "high", key=["normal", "high", "critical"].index)
    if p["mentions_deadline"] > 0.6 and deadline is None:
        return level, "review: deadline mentioned but not parsed"
    if p["says_urgent"] > 0.7 and level == "normal":
        return level, "review: stated urgent, no impact found"
    return level, None
```

Three things to notice. The critical level requires the lower boundary too, so an inconsistent
pair (critical yes, high no) cannot produce "critical". The deadline raises the level only
through arithmetic done in Python. And a stated urgency with no impact does not raise the level
on its own; it flags the ticket for a quick human look, which is where shouting customers and
calm, genuinely stuck ones get told apart.

## The review band

The two "review" returns above are the band. They catch the cases a yes/no model is weakest on
(a date it read but code could not parse) and the ones where stated tone and stated impact
disagree. Everything else is automated. If the band grows past what agents can look at within
your response target, raise the thresholds for "review" rather than removing it; the trade-off
is on [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

## Limits, and where local helps

- **Not measured on urgency.** The accuracies quoted are by kind of question on our own test
  set, not on customer urgency. Label a few hundred of your messages by the level an experienced
  agent would give, and check.
- **Relative dates.** "By Friday" needs the date the message was sent. Send it, and compute in
  code.
- **Implied urgency.** A customer who says "our launch is tomorrow" without saying the problem
  blocks the launch is implying impact. The model answers what is said more reliably than what
  is implied.
- **English only.**

Urgency is checked on every incoming message, which makes per-call cost and latency matter. On
our reference laptop a short message takes about 54 ms, and four questions on one message share
a single reading of it, so the check fits before a ticket is even shown in a queue. Pairing it
with [support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md)
means one request answers both where the ticket goes and how fast.

## Short answers to the questions that lead here

**How do I detect urgency in customer messages?** Ask whether the customer states urgency and
whether they state impact, as separate yes/no questions, and compute deadlines in code.

**Can an LLM tell if a deadline is soon?** It can tell you a deadline is mentioned. Whether it is
soon is date arithmetic, where a small model is unreliable; do it in code.

**How do I get priority levels instead of yes or no?** Ask one question per boundary ("at least
high?", "critical?") and take the highest boundary answered yes.

**What about customers who mark everything urgent?** Ask about impact separately. Stated urgency
without stated impact goes to a quick human check, not straight to the top.

**See also:** [combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md),
[email triage with a local LLM](email-triage-with-a-local-llm.md) and
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Sources

- Accuracy by kind of question (tone 0.938, fact 0.954, dates and time 0.598) and the mean
  P(yes) of 0.53 on no-answer time questions: our 999-question test set, `jevos-q4_k_m`.
- Short-request latency: our reference-laptop measurement in the
  [jev README](https://github.com/feder-cr/jev).
- Thresholds in the code are placeholders.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where the date questions were the
second-worst kind we measured, which is why this page keeps them out of the model.*
