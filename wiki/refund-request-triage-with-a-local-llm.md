---
title: "Refund request triage with a local LLM"
description: "An end-to-end refund triage workflow with a local LLM: build the state, read facts from the message, apply the policy in code, and route by band."
parent: "Use cases"
nav_order: 19
---

# Refund request triage with a local LLM

**A refund triage workflow with a small local LLM has five steps: build a state from the order
record and the customer's message, ask the model yes/no questions about what the message says,
apply your refund policy in code, route each request by band (approve, review, decline or ask
for more), and log everything.** The model does one job in that chain, turning the customer's
words into facts. The order system supplies the dates and amounts, code applies the rule, and a
person handles the middle band.

The page on [putting the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md)
explains how to phrase a policy for the model. This page is the pipeline around it: where the
data comes from, which decisions the model never makes, and how the workflow improves after it
goes live.

It walks through the steps in order, then the failure modes, then how to measure the workflow
on your own history.

## Step 1: what goes into the state?

Two sources, kept apart in the JSON: facts your systems already know, and the message only the
customer could write. This is the README's example:

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
    "upset": {"type": "noul", "instructions": "Is the customer upset?"},
    "wrong_item": {"type": "noul", "instructions": "Does the customer say they received the wrong item?"}
  }
}
```

The README's run of it answers `refund` 0.78, `upset` 0.73 and `wrong_item` 0.1, with 95 input
tokens. Note `delivered` is already "5 days ago", computed from the order record, not a raw
date the model would have to subtract. Every field that is a fact in your database should arrive
as that fact, ready to read. More on the design of this object in
[sending JSON as the text: designing the state](designing-the-state-as-json.md).

## Step 2: which questions does the model answer?

The README example asks the policy question directly, which is fine for a demo. In production,
ask the facts the policy needs, and keep the verdict for code:

- Does the customer say an item was missing from the delivery?
- Does the customer say they received the wrong item?
- Does the customer say the item arrived damaged?
- Does the customer ask for their money back, as opposed to a replacement?
- Is the customer upset?
- Does the message say when the problem was noticed?

These are reading questions. On 999 yes/no questions written after training, stated facts were
answered right 0.954 of the time, intent 0.859 and tone 0.938, while applying a rule was 0.721
and arithmetic 0.584. That spread is the reason for the split. All the questions go in one
request: the text is read once, and on our reference laptop three questions on this example took
about 165 ms against 103 ms for one.

## Step 3: where does the policy live?

In code, where it is exact and versioned:

```python
def refund_route(p, order):
    claims_problem = max(p["missing"], p["wrong_item"], p["damaged"])
    in_window = order["days_since_delivery"] <= 30          # exact, from the order system
    small = order["amount"] <= 50
    repeat = order["refunds_last_90_days"] >= 2

    if not in_window:
        return "decline_with_explanation"
    if claims_problem > 0.9 and small and not repeat:
        return "approve"
    if claims_problem < 0.1:
        return "ask_for_details"
    return "review"
```

This is an untested sketch; the thresholds and field names are yours to choose. What matters is
the shape: the window, the amount and the history are compared in code, and the model's
probabilities decide only which band a request falls into. When the policy changes, you change
a function and its tests, not a prompt.

## Step 4: who handles each band?

| Band | What happens |
|---|---|
| approve | refund issued automatically, customer notified |
| review | a person sees the message, the order and the model's answers, and decides |
| ask for details | the customer is asked what went wrong, with no refusal |
| decline with explanation | outside the window or not eligible under an exact rule, with a route to appeal |

The review band is not a failure of automation. It is where the hard cases go, and the model's
answers make those cases faster for a person to read. Sizing the band is the subject of
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

The `upset` answer does not decide eligibility. It decides tone and priority: an upset customer
in the review band can move up the queue, and a customer who also says "this is the second time"
may be worth routing to someone who can do more than refund. If the message threatens to leave,
that is a different question, covered on
[detecting cancellation intent in customer messages](cancellation-intent-detection.md).

## Step 5: what gets logged?

For every request: a hash of the state, the questions, each probability, the thresholds in force,
the route taken, the model file hash reported by `/health`, and the timing from the
`Server-Timing` header. When a customer disputes a decline or an auditor asks why refunds were
approved, that record answers without re-running anything. Details on
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## What goes wrong, and how the workflow absorbs it

- **The model says yes when the answer is no.** On the 999 set it made 152 wrong yeses against
  91 wrong noes. A wrong yes on "missing" costs a refund, so the automatic approval threshold is
  high, the amount is capped, and repeat claims go to review. The reasoning is on
  [thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md).
- **The message does not say.** "Refund please" states no problem. The "ask for details" band
  exists for this, and a question such as "Does the message say what went wrong?" is a reliable
  gate.
- **The message is not in English.** jevos reads English only. Route other languages to people or
  to a translation step.
- **Someone games the text.** A customer who learns the wording that gets approval can write it.
  The amount cap and the repeat rule are in code for that reason.

## Measuring the workflow on your history

Before switching on automatic approval, run the pipeline in shadow mode on a few hundred past
requests where you know what a person decided. Compare the route the workflow would have taken
with the decision that was made, band by band. The number that matters most is how many
requests the workflow would have approved that a person declined; set the approval threshold so
that number is one you can live with. Then keep sampling approved requests for review after
launch, since the mix of messages changes. We have not measured jevos on a refund dataset, so
this shadow run is your accuracy figure.

## Short answers to the questions that lead here

**Can an LLM approve refunds?** It can read what the customer says. Let code apply the policy, and
approve automatically only when the facts are clear, the amount is small and the history is clean.

**Why not just ask the model the policy question?** You can, as the README example does. Splitting
into facts and code is more accurate on rules and easier to change when the policy does.

**What does the model see?** The order facts you choose to send and the customer's message, on
your own machine.

**How fast is it?** On a laptop CPU, three questions on the README example took about 165 ms.

**How do I know it works?** Run it in shadow mode on past requests and compare with what people
decided.

**See also:** [support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md),
[gating AI agent tool calls with yes/no checks](gating-ai-agent-tool-calls.md) and
[fraud case triage with a local LLM](fraud-case-triage-with-a-local-llm.md).

## Sources

- The request and its answers (0.78, 0.73, 0.1; 95 input tokens), the 165 ms and 103 ms timings,
  and the `/health` and `Server-Timing` behaviour: the [jev README](https://github.com/feder-cr/jev).
- Accuracy by kind of question and the 152 to 91 error split: our 999-question test set on
  `jevos-q4_k_m`. No refund dataset was measured.
- No external facts are stated on this page.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The README asks the policy question in one line; this page is what we would build
around it before any money moved.*
