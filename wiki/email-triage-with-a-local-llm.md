---
title: "Email triage with a local LLM"
description: "Sort email with a local LLM: needs a reply, urgent, newsletter, meeting request. One request per email, and the mail never leaves your machine."
parent: "Use cases"
nav_order: 5
---

# Email triage with a local LLM

**Email triage with a local LLM is one request per message with a handful of yes/no questions
(does it need a reply from me, is it urgent, is it a newsletter or notification, does it ask
for a meeting) and a few lines of code that turn the probabilities into folders, flags or a
summary list.** The questions share one reading of the email, so four of them cost little more
than one, and a trimmed email is answered in a fraction of a second on a laptop CPU. Mailboxes
are among the most private text anyone has, and with a local model none of it is sent to an
inference provider.

The quality of the result depends less on the model than on what you send it. A raw email is
mostly quoted history, signatures, legal footers and HTML. Cut it to the part the sender just
wrote and the answers get better and faster at the same time.

This page is the state you build from an email, the questions, what the code does with the
answers, the band you look at yourself, why local matters for mail, and the limits.

## Building the state from a raw email

Latency grows with the text: on our reference laptop, about 1.1 ms per prompt token, which is
54 ms for a short request and 220 ms for one of about 190 tokens. A long thread pasted whole
can be thousands of tokens and still fit in the 8,192-token context, but it costs seconds and
buries the new message. Before calling the model:

- Keep the sender, the subject and the new part of the body. Drop quoted replies below the
  first "On ... wrote:" line, signatures and footers.
- Add the facts your code already has as fields, so the model does not have to guess them:
  whether the sender is in your contacts, whether you are in To or only in Cc, whether a
  `List-Unsubscribe` header is present.
- Keep field names readable in English. The model reads them as part of the text; the guidance
  is on [sending JSON as the text: designing the state](designing-the-state-as-json.md).

## The questions

```json
{
  "model": "jev-latest",
  "state": {
    "from": "Priya (Finance)",
    "sender_in_contacts": true,
    "me_in": "To",
    "subject": "Q3 invoices",
    "body": "Hi, two supplier invoices are still missing their PO numbers. Can you send them before our call on Thursday? I can also do 30 minutes tomorrow if that's easier."
  },
  "questions": {
    "needs_reply": {"type": "noul", "instructions": "Does the sender ask the recipient to answer, send something or decide something?"},
    "urgent":      {"type": "noul", "instructions": "Does the sender say this is urgent or needed very soon?"},
    "bulk":        {"type": "noul", "instructions": "Is this a newsletter, a marketing email or an automatic notification?"},
    "meeting":     {"type": "noul", "instructions": "Does the sender propose a meeting or a call at a specific time?"}
  }
}
```

Each question asks what the text says, not what you should feel about it. "Does the sender say
this is urgent" is a reading question; "is this urgent" invites the model to guess, and real
urgency often depends on a date. A mention of Thursday is only urgent if Thursday is tomorrow,
and that comparison belongs in code, as explained on
[urgency detection in customer messages](urgency-detection-in-customer-messages.md).

## From probabilities to folders

```python
def triage(p, email):
    if p["bulk"] > 0.8 and not email["sender_in_contacts"]:
        return "later"
    if p["needs_reply"] > 0.7:
        return "reply today" if p["urgent"] > 0.7 else "reply"
    if p["meeting"] > 0.7:
        return "calendar"
    if max(p.values()) < 0.3:
        return "read"
    return "check"
```

The numbers are placeholders. The order is the point: the bulk rule runs first, but only for
senders not in your contacts, because a newsletter from a colleague is still from a colleague.
Keep the four probabilities with the message even after you file it. They let you re-sort
later with a different threshold without asking the model again.

## The band you look at yourself

"check" is the review band: messages where no question is clearly yes and not everything is
clearly no. In an inbox the person reviewing is you, and the cost of a wrong answer is modest
but real. A wrong "later" can hide a request for a week. So the rule of thumb is that the model
may move mail up (flag, "reply today") freely and may move mail down (archive, "later") only
above a high bar. That asymmetry follows from the model's own error direction: on our
999-question test set it said yes wrongly 152 times and no wrongly 91 times. The general version
of this argument is on
[thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md).

## Why a local model matters for mail

An inbox holds contracts, health appointments, salary numbers and the personal data of people
who never agreed to have it sent anywhere. A local model reads it on the machine that already
has it, with no inference provider to add to a list of processors, and nothing to rate-limit
when you triage a backlog of ten thousand messages overnight with
[batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).

Local does not make the pipeline private by itself. The script that fetches mail has your
credentials, the log of probabilities is derived from the mail, and the server should listen
only on 127.0.0.1 (the default). [A private LLM for text classification](private-llm-for-text-classification.md)
covers what local solves and what it does not.

## Where email triage with a small model falls short

- **English only.** A mailbox that mixes languages needs translation first or another model.
- **Long threads.** The model answers about the text you send. If the request is buried five
  replies down, and you sent only the latest reply, it will not see it.
- **"Needs a reply from me" is not "needs a reply".** A message to a group asking "can someone
  check this?" asks the group. Send whether you are in To or Cc, and ask about the recipient.
- **Hidden context.** The model does not know your projects, your boss or your deadlines unless
  they are in the state.
- **Not measured on email.** We have not run jevos on an email dataset. The questions above are
  intent and stated-fact questions, which scored 0.859 and 0.954 on our 999-question set, but
  your mail is your mail: label a hundred messages and check.

## Short answers to the questions that lead here

**Can a local LLM sort my email?** Yes, for decisions such as needs a reply, newsletter, or
meeting request. It returns probabilities and your code files the messages.

**How many questions per email?** As many as you need in one request. They share one reading of
the email, so the extra questions are cheap.

**Is it private?** The text is processed on your machine and not sent to a model provider. The
mail client, logs and credentials still need the usual care.

**How do I make it faster?** Send less: strip quoted history, signatures and footers before the
request.

**See also:** [many questions about one text: why the extra ones are cheap](many-questions-about-one-text.md),
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md)
and [phishing email screening with a local LLM](phishing-email-screening-with-a-local-llm.md).

## Sources

- Latency per prompt token, 54 and 220 ms, 8,192-token context, default bind to 127.0.0.1: the
  [jev README](https://github.com/feder-cr/jev) and our reference-laptop measurements.
- Error direction and accuracy by kind of question: our 999-question test set, `jevos-q4_k_m`.
- Folder rules and thresholds in the code are illustrative.

---

*From the notes of [jev](https://github.com/feder-cr/jev). Most of the speed in email triage
comes from deleting the quoted history before the model ever sees it.*
