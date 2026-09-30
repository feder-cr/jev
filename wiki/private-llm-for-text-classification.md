---
title: "A private LLM for text classification"
description: "Classify customer text with an LLM that never sends it off the machine: what that protects, what it leaves open (access, logs), and how to send less."
parent: "Local and private AI"
nav_order: 2
---

# A private LLM for text classification

**A private LLM for text classification is one that reads the text on a machine you control,
so the text is never sent to a model provider.** With jevos the server runs on `127.0.0.1`, the
customer message goes in as `state`, each label is a yes/no question, and what comes back is one
probability per label. No copy of the message is sent anywhere for the model to read it. That
removes one party from your data flow; it does not make the rest of your system private.

The distinction matters because "local" is easy to over-read. Customer text can end up in many
places around a model call: application logs, debugging dumps, a proxy, a backup, a shared
machine. A local model changes none of those.

This page is what "the data never leaves the machine" covers precisely, what it leaves open,
how to send less text in the first place, and when a private small model is not the right
classifier.

## What exactly stays on the machine?

The model call. When your application posts a ticket to `POST /v1/systemone`, the text travels
over the loopback interface to a process on the same host, is read by the model, and the answer
goes back the same way. There is no network hop to a third party, no provider-side log of your
prompt, and no question of which region the provider processes it in.

It also makes the data flow easy to describe. For a hosted classifier you would list the
provider, what it receives, how long it keeps it and under what contract. For a local one the
entry for this step is: "classified on our server by a model file we host". If your server is
a rented machine, the hosting company is still part of that description.

## What local processing does not solve

| Risk | Does a local model help? | What does |
|---|---|---|
| Text sent to a model provider | Yes, it is not sent | nothing more needed |
| Who can call the classifier | No | bind to `127.0.0.1`, or set `JEV_API_KEY` |
| Text in application logs | No | log hashes and probabilities, not bodies |
| Text in a reverse proxy or APM tool | No | disable body capture for this route |
| Retention of the messages themselves | No | your retention policy |
| A wrong classification about a person | No | thresholds, review, logging |

Three of those deserve a sentence each.

**Access.** The server listens on `127.0.0.1` by default, so only processes on the same host
can reach it. If you bind it to a network interface without `JEV_API_KEY`, anyone who can reach
the port can send text and read answers. With the key set, every call except `/health` needs a
Bearer token; see [securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md).

**Logs.** The probabilities are not personal text, but they are information about a person
("P(yes) 0.91 that this customer is threatening to cancel"). A decision log that stores the
state hash, the question names and the probabilities lets you reconstruct what happened without
keeping the message twice. What to keep is on [logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

**Decisions.** Where a label triggers something that affects the person, the legal questions
are the same as with any model. The reading of GDPR Article 22 on
[GDPR and automated decision-making with an LLM](gdpr-and-automated-decision-making.md)
applies to a local model exactly as to a hosted one.

## Send less text in the first place

The most private field is the one you never send. `state` accepts a JSON object, which makes it
easy to pass only what the questions need:

```json
{
  "model": "jev-latest",
  "state": {
    "channel": "email",
    "customer_message": "I was charged twice for the same order and nobody answers my emails."
  },
  "questions": {
    "billing":  {"type": "noul", "instructions": "Is this a billing problem?"},
    "cancel":   {"type": "noul", "instructions": "Does the customer say they want to cancel?"},
    "repeated": {"type": "noul", "instructions": "Does the customer say they already contacted support?"}
  }
}
```

No name, no email address, no order number, no account ID. None of the three questions needs
them, and the answers come back keyed by question name, so your code joins them to the customer
record it already has. Dropping fields also saves time: latency grows with the length of the
input: on the reference laptop a 30-token request read from scratch took 26 ms and a 191-token
one 112 ms. The general method is on
[sending JSON as the text: designing the state](designing-the-state-as-json.md).

If messages routinely contain identifiers you would rather not pass at all, strip the exact
patterns (emails, phone numbers, card numbers) with a deterministic tool before the model sees
the text. That is the split described on
[checking text for personal data with yes/no questions](pii-check-with-yes-no-questions.md):
exact patterns in code, meaning in the model.

## How good is the classification?

Privacy is worth little if the labels are wrong. The measurements that matter for
classification come from 999 yes/no questions written after training, on texts such as emails,
tickets, logs, reviews and forms: 0.954 on facts stated in the text, 0.938 on tone, 0.859 on
the writer's intent, 0.858 on negation. The weak spots are questions that need a computation,
0.584 on arithmetic and 0.598 on dates, which a classifier mostly should not be asking anyway.

The label design is on
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md):
one question per label, several labels in one request, the text read once. On the README's
example, three questions take about 66 ms together against 49 ms for one alone.

## When a private small model is the wrong tool

- **Other languages.** jevos reads English only. Translating first means sending the text to a
  translator, which may undo the point of running locally.
- **Stable labels with lots of history.** If you have thousands of labelled tickets for a label
  set that does not change, a classifier trained on those examples will usually be more accurate; see
  [a yes/no LLM vs a fine-tuned BERT classifier](yes-no-llm-vs-fine-tuned-bert.md). It can be
  just as private.
- **Hard rules.** On 2,000 questions about unseen business policies, jevos was right 0.810 of
  the time against 0.927 for the hosted Jev. If the label is really a policy decision, compute
  the policy in code.

## Short answers to the questions that lead here

**Does a local LLM send data anywhere?** The jevos server reads the text in its own process on
your machine and sends it nowhere. Downloading the binary and the model needs the network once.

**Is a local model private by default?** The model call is. Your logs, proxies, backups and who
can reach the port are separate decisions.

**Can I classify customer emails without a cloud API?** Yes, in English, with one yes/no
question per label and a threshold on each probability.

**Should I remove personal data before classifying?** Send only the fields the questions need,
and strip exact identifiers in code when the questions do not depend on them.

**Is the output personal data?** Treat it as such when it is about an identifiable person: a
probability that a customer is angry is information about that customer.

**See also:** [self-hosted AI for decisions](self-hosted-ai-for-decisions.md),
[offline AI for decisions](offline-ai-for-decisions.md) and
[email triage with a local LLM](email-triage-with-a-local-llm.md).

## Sources

- Server binding, `JEV_API_KEY`, the request format and the three-question timing: the
  [jev README](https://github.com/feder-cr/jev).
- Accuracy by kind of question: our 999-question test set on `jevos-q4_k_m`; policy accuracy:
  our 2,000-question comparison. Latency by text length: our measurement on an Intel Core Ultra 7
  255H.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose server listens on `127.0.0.1`
unless you tell it otherwise.*
