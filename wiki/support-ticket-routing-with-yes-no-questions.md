---
title: "Support ticket routing with yes/no questions"
description: "Route support tickets with one yes/no question per queue, a threshold for other, an escalation check, fallbacks and a replay of your own ticket history."
parent: "Use cases"
nav_order: 6
---

# Support ticket routing with yes/no questions

**Route tickets by asking one yes/no question per queue plus one escalation question, send the
ticket to the queue with the highest P(yes) if it clears a threshold, and to a general queue
if nothing does.** That is the whole model side. The rest of a routing system is operations:
what happens when the model server is down, how escalations meet their response targets, and
how you prove the router is right before it touches live tickets. The proof comes from your own
ticket history, which already says where each ticket ended up.

The classification idea itself is on
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).
This page assumes it and is about running it: the request, the routing function with its
fallbacks, escalation, measuring on history, and rolling out without a bad week.

## The request: queues and one escalation check

```json
{
  "model": "jev-latest",
  "state": {
    "plan": "business",
    "subject": "Can't export invoices since this morning",
    "message": "Our whole finance team gets an error when exporting invoices. Month-end close is today."
  },
  "questions": {
    "billing":   {"type": "noul", "instructions": "Is the ticket mainly about a charge, an invoice amount, a refund or a payment method?"},
    "technical": {"type": "noul", "instructions": "Is the ticket mainly about an error, a bug or a feature not working?"},
    "account":   {"type": "noul", "instructions": "Is the ticket mainly about logging in, users or permissions?"},
    "escalate":  {"type": "noul", "instructions": "Does the customer say many users are blocked or that the problem stops their business today?"}
  }
}
```

Write each queue question from what that team actually handles, not from its name. An invoice
export error is technical, not billing, and the billing question says so by listing what
billing covers. The escalation question asks what the customer says, which the model can read,
rather than how severe the problem really is, which it cannot know.

The plan tier is in `state` for the reader's context, but the rule "business customers get a
faster target" is a lookup, and lives in code.

## The routing function, with fallbacks

```python
import requests

def route(ticket, questions, url="http://127.0.0.1:8017/v1/systemone"):
    body = {"model": "jev-latest", "state": ticket, "questions": questions}
    try:
        r = requests.post(url, json=body, timeout=2)
        r.raise_for_status()
        p = {k: a["noul"] for k, a in r.json()["answers"].items()}
    except requests.RequestException:
        return {"queue": "general", "escalate": False, "reason": "router unavailable"}
    queues = {k: v for k, v in p.items() if k != "escalate"}
    best = max(queues, key=queues.get)
    queue = best if queues[best] >= 0.6 else "general"
    return {"queue": queue, "escalate": p["escalate"] >= 0.5, "p": p}
```

Three operational choices are built in:

- **Fail to a human queue.** A timeout, a restart or a `422` (for instance a question sent as
  `choice`, which jevos refuses) must never drop a ticket. The general queue is staffed; the
  router is an optimisation.
- **Return the probabilities.** Store `p` on the ticket. Agents can see why it landed where it
  did, and you can replay a new threshold over old tickets without calling the model again.
- **Escalation is independent of the queue.** An urgent billing ticket is still billing. Flag it,
  do not reroute it.

## Escalation and response targets

The escalation threshold is set lower than the queue threshold on purpose. A false escalation
costs a senior agent a minute; a missed one costs the target and possibly the customer. That is
the asymmetric case described on
[precision and recall at a P(yes) threshold](precision-and-recall-at-a-threshold.md): for
escalations, recall first.

Keep the clock in code. The response target depends on plan, time of day and queue, all of
which your helpdesk knows exactly. The model's job ends at "the customer says their business is
blocked today".

## Measuring routing on your own history

Your resolved tickets are a labelled test set you already own: each has the queue that finally
handled it. Before switching anything on:

1. Take a few hundred recent resolved tickets. Drop the ones that were moved between queues
   for reasons unrelated to content (staffing, holidays).
2. Run the router over them with `jev decide` or the server, and store every probability.
3. Count, per queue, how often the router agrees with the final queue, and how many tickets fall
   below the threshold into general.
4. Read the disagreements. Many will be a vague queue question, fixed by rewording, not by the
   model.
5. Pick the threshold that sends to general only what a person would also hesitate on.

The method for building such a set properly, balanced and never tuned on, is on
[building a yes/no test set for your own data](building-a-yes-no-test-set.md). Keep a fresh
slice aside after you tune the questions, or the numbers will flatter you.

## Rolling it out

Run in shadow mode first: the router writes its suggested queue on the ticket and agents route
as before. After a week, compare. Then turn it on for the queue where it agreed most, keep
general as the fallback, and watch the share of tickets that land in general. A sudden rise
means the incoming tickets changed (a new product, an outage) before any accuracy number would
tell you.

## Limits worth stating

- **We have not measured jevos on ticket routing.** The question kinds it needs are among its
  better ones on our 999-question test set (intent 0.859, stated facts 0.954), but only your
  history tells you the routing accuracy.
- **Rules inside routing.** "Refund requests over 500 go to the finance lead" is an amount
  compared to a limit; number-against-threshold questions scored 0.654 on the same set. Extract
  the amount and compare in code.
- **English only.** Tickets in other languages need another path.
- **Many similar queues.** Twenty queues that differ by product line are twenty questions whose
  answers can be close together. When the top two are within a few points, route to general or
  to the larger of the two, and log it.

For tickets where the local answer is not confident, sending the middle band to a larger hosted
model is a reasonable second step; the pattern is on
[a model cascade: small model first, large model on doubt](model-cascade-small-model-first.md).
Locally, one question costs 54 to 220 ms on our reference laptop depending on length, each
extra question on the same ticket costs a fraction of that, and ticket text, which often contains customer data, stays on your servers.

## Short answers to the questions that lead here

**How do I route support tickets automatically?** Ask one yes/no question per queue, pick the
highest probability above a threshold, and send the rest to a general queue.

**What if the model server is down?** Route to a staffed general queue. The router must fail
safe, never drop a ticket.

**How do I know the routing is accurate?** Replay your resolved tickets and compare the
suggested queue with the queue that finally handled each one.

**Can I add a new queue without retraining?** Yes. Add one question and replay history to check
it does not steal tickets from the others.

**Should the model decide the response target?** No. It can flag that a customer reports being
blocked; the target comes from your plan rules in code.

**See also:** [intent detection with a local LLM](intent-detection-with-a-local-llm.md),
[urgency detection in customer messages](urgency-detection-in-customer-messages.md) and
[a Python client for local LLM decisions](python-client-for-local-llm-decisions.md).

## Sources

- The `422` for `choice` and `score` questions, the request format and `jev decide`: the
  [jev README](https://github.com/feder-cr/jev).
- Accuracy by kind of question: our 999-question test set, written after training, run on
  `jevos-q4_k_m`.
- Thresholds in the code are placeholders; the rollout steps are a suggested practice, not a
  measured result.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The general queue is the most
important line in a router, because it is where the router admits it does not know.*
