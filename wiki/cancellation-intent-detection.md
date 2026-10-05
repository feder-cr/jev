---
title: "Detecting cancellation intent in customer messages"
description: "Tell a cancellation request from a threat to cancel and from venting, with separate yes/no questions for intent and tone, and route each one differently."
parent: "Use cases"
nav_order: 20
---

# Detecting cancellation intent in customer messages

**Cancellation intent is three different things that sound alike: a customer asking to cancel
now, a customer threatening to cancel if something is not fixed, and a customer venting with
no plan to leave.** Ask a small local model a separate yes/no question for each, plus a tone
question, and route them differently: process the request, send the threat to someone who can
fix the problem, and answer the venting as ordinary support. A single "does this customer want
to cancel?" question blurs the three, and the cost of the blur runs in both directions.

The direction that is easy to miss is the first one. Treating a clear cancellation request as a
retention opportunity, and making the customer ask again, costs trust that no retention offer wins back. A
detector that is good at spotting clear requests is as much about processing them promptly as
about saving accounts.

This page is how the three kinds differ, the questions that separate them, why intent and tone
are separate questions, the routing table, stated and implied intent, and how to check it on
your own messages.

## Request, threat or venting?

| Kind | Example | What the writer wants |
|---|---|---|
| request | "Please cancel my subscription at the end of this month." | the cancellation |
| conditional threat | "If this isn't fixed by Friday I'm cancelling." | the problem fixed |
| venting | "Honestly, this is the worst app I have ever paid for." | to be heard, maybe a fix |
| question about cancelling | "What happens to my data if I cancel?" | information |

The last row matters more than it looks. A customer who asks how cancellation works may be
about to leave, or may be checking before renewing. It is a question to answer clearly, not a
signal to push back on.

## Which questions separate them?

One question per kind, each about what the writer says or asks for:

```json
{
  "model": "jev-latest",
  "state": {
    "plan": "annual",
    "message": "Third outage this month. If support can't tell me what happened, I'm moving to another provider."
  },
  "questions": {
    "asks_to_cancel":  {"type": "noul", "instructions": "Does the customer ask for their account or subscription to be cancelled?"},
    "conditional":     {"type": "noul", "instructions": "Does the customer say they will leave only if something is not fixed or explained?"},
    "asks_about_exit": {"type": "noul", "instructions": "Does the customer ask how cancelling or leaving works?"},
    "upset":           {"type": "noul", "instructions": "Is the customer upset?"},
    "states_problem":  {"type": "noul", "instructions": "Does the customer describe a specific problem with the service?"}
  }
}
```

Each question comes back as its own `noul`, all from one read of the message. "Asks for their
account to be cancelled" is a request; "will leave only if something is not fixed" is the
condition that makes a threat. Asking both, rather than one broad cancellation question, is
what lets the routing tell them apart. The wording of intent questions in general is on
[asking about intent: what does the writer want?](yes-no-questions-about-intent.md).

## Why are intent and tone separate questions?

Because they vary independently. A polite "please cancel my account, thanks for everything" is
a clear request with no anger. A furious message about an outage may contain no intent to leave
at all. If one question mixes them, an angry venting message scores like a request and a calm
request scores like nothing.

The two kinds of question also behave differently on our measurements. On 999 hand-written yes/no
questions, the first jevos answered tone questions right 0.938 of the time and intent
questions 0.859 (per-kind numbers for jevos-v4 are not published). On questions whose right answer was no, the mean P(yes) was 0.16 for tone and
0.28 for intent: the model is steadier on how a message feels than on what the writer wants.
That is a reason to set a firmer threshold on the intent questions, and to let tone adjust
priority rather than route. More on the tone side on
[yes/no questions about tone and emotion](yes-no-questions-about-tone.md), including the
caveats about sarcasm.

## How should each kind be routed?

| Answers | Route |
|---|---|
| `asks_to_cancel` high | cancellation processing, confirm promptly; offer alternatives once, if at all |
| `conditional` high | retention or a senior agent, with the stated problem attached |
| `asks_about_exit` high, others low | answer the question, with a link to the cancellation page |
| `upset` high, no intent | ordinary support queue, higher priority |
| everything in the middle | a person reads it |

Two notes on the table. First, a request that is also angry is still a request: process it, and
let tone decide how the reply is written, not whether the customer gets what they asked for.
Second, the conditional threat is the message where a team can change the outcome, because the
customer has said what would keep them. That is where the stated problem, from `states_problem`
and the message itself, is worth putting in front of someone who can act. Routing mechanics,
queues and fallbacks are on
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md).

## Stated or implied intent?

"I'm cancelling" is stated. "I've started looking at other providers" implies an intent without
saying it, and "I just want to know what my options are" may imply one or may not. We have not
measured the two separately, but the reason to expect a gap is simple: a stated intent is close
to a stated fact, the strongest kind of question on our test set at 0.954 for the first jevos, while an implied one
has to be inferred.

So write the routing questions about what the customer says ("Does the customer ask...", "Does
the customer say they will..."), and treat implied intent as a softer signal: something to flag
for an account manager to look at, not something to act on automatically. The difference between
a message's several topics and its main one is on
[mainly about: questions for messages with several topics](mainly-about-questions-for-mixed-messages.md).

## Checking it on your own messages

Pull a few hundred past messages that people have already handled, and label each with the four
kinds in the first table (several labels are allowed). Run the questions and look at two
confusions in particular: requests routed as threats, which delay a customer who has already
decided, and threats routed as venting, which lose the chance to fix the problem. Adjust wording
first and thresholds second. We have not measured jevos on a cancellation dataset, so this
check is the only accuracy figure that applies to your messages. jevos reads English only.

## Short answers to the questions that lead here

**How do I detect churn intent in customer messages?** Ask separate yes/no questions for a
cancellation request, a conditional threat and a question about leaving, plus a tone question,
and route on the combination.

**What is the difference between a threat to cancel and a request?** A request asks for the
cancellation. A threat names a condition, something that must be fixed, and is the one where
retention work can help.

**Should a retention team see every cancellation request?** Not as a hurdle. Process clear
requests promptly; send conditional threats to the people who can fix the stated problem.

**Is an angry message a churn signal?** Not by itself. Tone and intent are separate questions,
and on our test set the first jevos answered tone more reliably (0.938) than intent (0.859).

**Can this run on every incoming message?** A handful of questions on one short message takes a
fraction of a second on a laptop CPU, and the text stays on your machine.

**See also:** [intent detection with a local LLM](intent-detection-with-a-local-llm.md),
[sentiment analysis with yes/no questions](sentiment-analysis-with-yes-no-questions.md) and
[refund request triage with a local LLM](refund-request-triage-with-a-local-llm.md).

## Sources

- Accuracy by kind of question (tone 0.938, intent 0.859, fact 0.954) and the mean P(yes) on
  no-answer questions (tone 0.16, intent 0.28): our 999 hand-written questions, measured on the first jevos. No
  cancellation dataset was measured.
- Request format and the one-read-per-request behaviour: the
  [jev README](https://github.com/feder-cr/jev).
- No external facts are stated on this page.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The example message is a conditional threat on purpose: it contains the words of a
cancellation and is not a request, which is the whole reason to ask more than one question.*
