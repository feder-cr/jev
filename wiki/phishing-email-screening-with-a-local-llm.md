---
title: "Phishing email screening with a local LLM"
description: "Screen emails for phishing signs with yes/no questions on a local LLM: urgency, credential requests, odd links. A first filter next to header checks."
parent: "Use cases"
nav_order: 12
---

# Phishing email screening with a local LLM

**A small local LLM can flag emails that read like phishing by answering a few yes/no
questions about the body: does it create urgency, does it ask for a password or payment
details, does it tell the reader to click a link to fix a problem.** Those answers are a first
filter that decides which messages get a warning banner or a closer look. They are not a
security control: authentication results, link checks and your mail gateway do the real work,
and an attacker can write a message that answers every question the way they want.

What the model adds is reading. Header checks tell you whether a message really came from the
domain it claims; they say nothing about a message from a real but compromised account asking
the finance team to change bank details today. That request is plain language, and plain
language is what a yes/no model reads.

This page is the signals written as questions, what code checks better than any model, a
request, a sketch of the combination, and the limits, stated plainly.

## Which phishing signs are questions about the text?

CISA's public guidance lists the signs most people are taught: "urgent or emotionally
appealing language, especially messages that claim dire consequences for not responding
immediately", "requests to send personal and financial information", and untrusted or
misspelled links. It also notes that poor grammar is no longer a reliable sign, since
generated phishing can be written well.

The first two are about meaning, and they make good questions:

| Signal | Question |
|---|---|
| urgency | Does the email say something bad will happen if the reader does not act quickly? |
| credentials | Does the email ask the reader to enter or send a password, code or login details? |
| payment | Does the email ask the reader to pay, or to change where a payment is sent? |
| link as the fix | Does the email tell the reader to click a link to solve a problem with their account? |
| secrecy | Does the email ask the reader not to tell anyone or not to verify the request? |
| authority | Does the sender claim to be a manager, a bank, or a government office? |

Keep each question to one condition, so a hit tells you which sign fired. The reasoning is on
[one condition per question](one-condition-per-question.md).

## What should code check instead?

Some phishing signals are exact facts about the message, and a model is the wrong tool for them:

- **Sender authentication.** SPF, DKIM and DMARC results. DMARC, per RFC 7489, lets a domain
  owner publish a policy (`none`, `quarantine` or `reject`) and checks that the From domain
  aligns with a domain authenticated by SPF or DKIM. Your mail server already computes this;
  read the result from the headers.
- **Link mismatch.** Whether the domain a link points to differs from the text shown, or from the
  sender's domain. That is string comparison after parsing the HTML.
- **Lookalike domains.** Edit distance against your own and your partners' domains.
- **Reputation.** Whether a sender, domain or URL is on a list you trust.

Regex and parsers are exact where exactness is possible; the model reads what they cannot. The
wider comparison is on [LLM decisions vs keyword rules and regex](llm-decisions-vs-keyword-rules.md).

## A request for one email

Send the subject and the body text, stripped of HTML, as the state. Add the few header facts that
help the model read the body in context, such as whether the sender is external:

```json
{
  "model": "jev-latest",
  "state": {
    "sender_is_external": true,
    "subject": "Action required: mailbox storage full",
    "body": "Your mailbox will be suspended in 2 hours. Sign in here to keep your messages."
  },
  "questions": {
    "urgency":     {"type": "noul", "instructions": "Does the email say something bad will happen if the reader does not act quickly?"},
    "credentials": {"type": "noul", "instructions": "Does the email ask the reader to sign in or send login details?"},
    "link_fix":    {"type": "noul", "instructions": "Does the email tell the reader to click a link to solve a problem with their account?"}
  }
}
```

All questions in one request share the text, which is read once. On our reference laptop three
questions on one short text took about 66 ms against 49 ms for one alone, so a handful of
signals per email stays well under a second on a CPU.

## A sketch of the combination

This is an untested sketch of the shape, not a finished filter. Header facts come from your
mail server; `p` holds the probabilities from the request above.

```python
text_signs = sum(p[name] > 0.7 for name in ("urgency", "credentials", "link_fix"))

if headers["dmarc"] == "fail" or link_domain_mismatch:
    action = "quarantine"          # exact checks decide on their own
elif text_signs >= 2 and sender_is_external:
    action = "warning_banner"      # the model only adds a warning
else:
    action = "deliver"
```

The model never releases a message the exact checks stopped, and never quarantines a message on
its own in this sketch. It raises a warning. Where you set the 0.7 and the count of two depends
on how many false alarms your users will tolerate; the trade is on
[precision and recall at a threshold](precision-and-recall-at-a-threshold.md).

## Being straight about the limit

A small model is a first screen, not a security control. Four reasons:

1. **The attacker writes the input.** A phishing email that avoids urgent words and never says
   "password" will answer no to every question. Filters based on how text reads can be written
   around.
2. **The input can talk to the model.** OWASP's cheat sheet on prompt injection says a guardrail
   model "is itself an LLM and is itself susceptible to prompt injection" and should be treated
   "as one layer in a defense-in-depth design". The same applies to a screen that reads email.
3. **It is not measured on phishing.** We have not measured jevos on a phishing set. What we
   measured is a spread by kind of question: on 999 questions written after training, intent was
   right 0.859 of the time and stated facts 0.954. Build your own set from reported messages
   before you rely on any threshold.
4. **English only.** jevos reads English. Phishing in other languages needs another tool.

What it is good for: warning banners, prioritising the reports your security team reads, and
sorting user-reported messages, all locally, without sending mailbox content to a third party.
For the non-security side of the inbox, see [email triage with a local LLM](email-triage-with-a-local-llm.md).

## Short answers to the questions that lead here

**Can an LLM detect phishing emails?** It can flag the language of phishing, such as urgency and
requests for credentials. It cannot verify a sender or a link, and a careful attacker can write
around it.

**Is a local model safe to use as my phishing filter?** Not as the filter. Use it next to
SPF, DKIM and DMARC results, link checks and your gateway, to add warnings.

**Why ask several questions instead of one "is this phishing?"** Separate signs tell you which
one fired, and a message with two or three is more suspicious than one with a single sign.

**Does grammar still matter?** Less than it did. CISA notes that generated phishing may have
perfect grammar.

**Can it run on every incoming email?** A few questions per short email take a fraction of a
second on a laptop CPU, which fits a mail pipeline of modest volume.

**See also:** [spam detection with yes/no questions](spam-detection-with-yes-no-questions.md),
[prompt injection screening with a small model](prompt-injection-screening-with-a-small-model.md)
and [combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## Sources

- Our measurements: three questions about 66 ms vs 49 ms for one, from the
  [jev README](https://github.com/feder-cr/jev); accuracy by kind of question from our
  999-question test set on `jevos-q4_k_m`. No phishing measurement exists; none is claimed.
- CISA, [recognize and report phishing](https://www.cisa.gov/secure-our-world/recognize-and-report-phishing),
  fetched 2026-09-29.
- RFC 7489, [Domain-based Message Authentication, Reporting, and Conformance (DMARC)](https://www.rfc-editor.org/rfc/rfc7489),
  fetched 2026-09-29.
- OWASP, [LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. We have not measured it on phishing mail, so this page gives you questions and a
design, not a detection rate.*
