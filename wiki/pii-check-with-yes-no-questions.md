---
title: "Checking text for personal data with yes/no questions"
description: "Use exact detectors for emails, phones and card numbers, and yes/no questions for context such as health details. A first screen, not a compliance control."
parent: "Use cases"
nav_order: 14
---

# Checking text for personal data with yes/no questions

**Use pattern tools for personal data that has a shape, and yes/no questions for personal data
that only has a meaning.** An email address, a phone number or a card number is found exactly
by regex, checksums and dedicated detectors such as Microsoft Presidio. "My son was diagnosed
last month", "the tenant in flat 4 who uses a wheelchair" or "the only woman on the night
shift" contain no pattern at all, and a small local model asked "Does the text mention a health
condition of a person?" can read them. Neither approach finds everything, so treat the result
as a first screen that decides what gets masked or reviewed, not as a security or compliance
control.

The split matters because the two kinds of personal data fail in opposite ways. Pattern tools
are precise on shapes and blind to context. A language model reads context and is unreliable
on exact shapes: it cannot promise that a string is a valid card number, and it should not be
asked to.

This page is the two kinds of personal data, the questions for the contextual kind, what the
law counts as personal data, how to layer the checks, and the limits.

## Shape or meaning: which kind of personal data is it?

| Kind | Examples | Best tool |
|---|---|---|
| has a fixed shape | email, phone, IBAN, card number, national ID, IP address | regex, checksum, a detector like Presidio |
| is a name or place | person names, street addresses, cities | a named-entity detector, checked by a person on doubt |
| only has a meaning | health, religion, a family situation, a description that singles someone out | yes/no questions to a model |

Presidio, per its own repository, combines named-entity recognition, regular expressions,
checksum validation and context words, and covers types such as credit card numbers, names,
locations and phone numbers. Its documentation is also direct about the limit: because it uses
automated detection, it says it cannot promise to find all sensitive information, and it
recommends additional systems and protections.

The right-hand column is where a yes/no model fits: questions a regex cannot express. The
general comparison of the two approaches is on
[LLM decisions vs keyword rules and regex](llm-decisions-vs-keyword-rules.md).

## What counts as personal data?

The UK regulator's guidance defines personal data as "any information relating to an identified
or identifiable natural person", where the person can be identified directly (a name, an ID
number, an online identifier) or indirectly, through factors specific to their "physical,
physiological, genetic, mental, economic, cultural or social identity". It lists special
category data that needs extra protection, including health data, religious beliefs, political
opinions, sexual orientation and biometric data.

The indirect part is why pattern tools are not enough. A support ticket that says "the manager
of our Leeds branch, who is on sick leave" names nobody and still identifies someone, and it
contains a health detail. This page is not legal advice, and whether a given text is personal
data in your context is a question for your data protection lead.

## Questions for the contextual part

One question per category, each about what the text says:

```json
{
  "model": "jev-latest",
  "state": "Customer asked us to delay the delivery because her husband is in hospital after a stroke. Please call her on the number in the order.",
  "questions": {
    "health":      {"type": "noul", "instructions": "Does the text mention a health condition or medical treatment of a person?"},
    "family":      {"type": "noul", "instructions": "Does the text describe a person's family situation?"},
    "singles_out": {"type": "noul", "instructions": "Does the text describe a specific person in a way that would let someone identify them?"},
    "belief":      {"type": "noul", "instructions": "Does the text mention a person's religion or political views?"}
  }
}
```

Each question returns its own `noul`. The phone number is not asked about: the order system has
it, and a regex would find it in the text.

Reading questions like these are the strong side of a small model. On 999 yes/no questions
written after training, stated facts were answered right 0.954 of the time and questions about
whether the text states something at all 0.847. We have not measured jevos on a personal-data
set, so those numbers describe the kind of question, not this task.

## Layering the checks

A workable order for a pipeline that stores or forwards free text:

1. **Exact detectors first.** Regex and checksums for your known formats, a detector such as
   Presidio for names and common identifiers. Mask what they find.
2. **Questions on what is left.** Ask the contextual questions about the masked text. A health
   detail survives masking because there was nothing to mask.
3. **A band for people.** Above a high threshold, apply your handling rule automatically (for
   example, restrict access to the ticket). Between the thresholds, send it to a person. The
   pattern is on [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).
4. **Log the decision, not the text.** Record which questions fired and their probabilities, not
   a second copy of the sensitive sentence.

For a missed health detail the costly mistake is the wrong no, so the threshold for "send to a
person" should be low, not 0.5.

## Long documents

jevos reads up to 8,192 tokens per request, and latency grows with length: about 1.1 ms per
prompt token on our reference laptop. A long document should be split into passages, each
passage asked the same questions, and the answers combined with OR, since one passage with
health data makes the document contain health data. The method is on
[yes/no questions about long documents](yes-no-questions-about-long-documents.md).

## What a yes/no check cannot promise about personal data

- **It is a first screen, not a control.** A model that reads text can miss a detail phrased in a
  way it does not expect, and a determined writer can hide personal data from any automated
  check. Access control, retention rules and people are what protect the data.
- **It does not find shapes reliably.** Do not ask "Does the text contain a valid card number?".
  Use a checksum.
- **English only.** jevos reads English. Personal data in other languages needs another tool.
- **Local helps, it does not solve.** Running on your own CPU means the text is not sent to a
  third party to be checked, which is often why a PII screen exists in the first place. It does
  not by itself make your storage, logs or access rules compliant. More on that on
  [a private LLM for text classification](private-llm-for-text-classification.md).

## Short answers to the questions that lead here

**Can an LLM detect personal data?** It can read contextual personal data such as a health detail
or a description that identifies someone. For emails, phone numbers and card numbers, use regex,
checksums or a detector.

**Should I replace Presidio with a model?** No. Use both: the detector for shapes and entities,
yes/no questions for meaning. Neither claims to find everything.

**Is a PII check with a model enough for GDPR?** No automated check is. It is one screen inside
a process with access control, retention and review.

**Why run the check locally?** Because the text you are checking is the text you do not want to
send anywhere.

**What threshold should I use?** Low for sending text to review, since a missed detail costs more
than an extra look. Choose it on labelled examples from your own data.

**See also:** [review moderation with a local LLM](review-moderation-with-a-local-llm.md),
[ask whether the text says it at all](ask-whether-the-text-says-it.md) and
[GDPR and automated decision-making](gdpr-and-automated-decision-making.md).

## Sources

- Our measurements: accuracy by kind of question from our 999-question test set on
  `jevos-q4_k_m`; context and latency from the [jev README](https://github.com/feder-cr/jev). No
  personal-data measurement exists; none is claimed.
- Microsoft, [Presidio repository](https://github.com/microsoft/presidio), detection methods,
  entity types and its stated limitation, fetched 2026-09-29.
- ICO, [what is personal data](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/personal-information-what-is-it/what-is-personal-data/what-is-personal-data/),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The example ticket contains no number, no name and no pattern, and it is still
full of personal data.*
