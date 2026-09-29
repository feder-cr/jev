---
title: "Using an English-only LLM with other languages"
description: "jevos reads English only. Three options for text in other languages: translate first, route by language, or use a multilingual model."
parent: "Question design"
nav_order: 12
---

# Using an English-only LLM with other languages

**jevos reads English only, so for text in another language you have three options: translate
the text to English before asking, route non-English text to a multilingual model, or keep
jevos out of those decisions.** Sending the original text with English questions is not one of
the options. The server will still return a probability, because it always does, but we have
not measured what that probability is worth on any other language, and a number whose meaning
is unknown should not drive a decision.

This is an honest limit rather than a detail. A system that starts in English can receive its
first German or Spanish ticket on any day, and a yes/no model gives no error when it does. The protection has to be in your code, and it has to be there before the first such
message arrives.

This page is why the limit matters more than it looks, the three options with what each costs,
how to detect the language, and what to watch for when translation sits in front of the model.

## Why not just send the text?

Because nothing will tell you it went wrong. A chat model given a French message might answer
in French, or say it did not understand; the failure is visible. A yes/no model returns a
number between 0 and 1 for any input, and a plausible-looking 0.3 on a French complaint looks
exactly like a correct 0.3 on an English one.

We have measured jevos on English text: 0.954 on stated facts and 0.938 on tone, among other
kinds, on our 999-question test set, and 0.811 on 2,000 policy questions. None of those texts
was in another language. We have no result for any other language, good or bad, and this page
does not guess one.

## Option 1: translate first

Put a machine translation step in front of the request, then ask English questions of the
English text.

```json
{
  "model": "jev-latest",
  "state": {
    "original_language": "German",
    "customer_message_english": "The package arrived damaged. I would like a replacement, please.",
    "order_total": "34 euros"
  },
  "questions": {
    "asks_replacement": {"type": "noul", "instructions": "Does the customer ask for a replacement?"},
    "polite":           {"type": "noul", "instructions": "Is the customer's message polite?"}
  }
}
```

What it costs:

- **Latency and money.** The translation step can easily be slower than the yes/no question
  itself. On the reference laptop, a request of about 190 tokens takes about 220 ms; a
  translation step can easily cost more than that, locally or over a network.
- **Privacy.** If the translation is a hosted service, the text leaves your machine, which may
  be the thing you chose a local model to avoid. The trade-off is laid out on
  [local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md).
- **Meaning.** Translation is a second model with its own errors, and the errors land on
  exactly the questions that depend on nuance: tone, politeness, sarcasm and implied intent.
  A formal "Sie" and an informal "du" may both become "you". If your questions are about how
  something was said, test them on translated examples specifically; the tone caveats are on
  [yes/no questions about tone and emotion](yes-no-questions-about-tone.md).

What translation does well is carry facts across: an order number, a missing item, a request
for a refund. Reading questions survive translation better than judgment questions.

Keep the original text with the decision, in your logs. A reviewer who reads German will want
the German, not the translation the model saw.

## Option 2: route by language

Detect the language in code, send English to jevos, and send everything else to a model that
reads it.

```python
if language == "en":
    answer = ask_jevos(text, questions)
else:
    answer = ask_multilingual_model(text, questions)
```

This is a small cascade, and the same pattern as sending doubtful cases to a larger model,
covered on [a model cascade: small model first, large model on doubt](model-cascade-small-model-first.md).
It keeps each model on text it was built for, and it keeps English traffic fast and local. The
cost is a second model to run, pay for, and test, and two sets of thresholds, because two
models do not produce comparable probabilities.

Detect the language with a dedicated language identification library, not with a yes/no
question to jevos: we have not measured jevos on that task either, and asking an English-only
model whether a text is English is the case where you least want to rely on it.

## Option 3: keep the questions, change the model

If most of your text is not in English, the honest answer is that jevos is the wrong tool for
your traffic. Use a multilingual model for yes/no questions instead, a larger local one or a
hosted API. The design advice on this wiki still applies, because it is about questions, not
languages: one condition per question, the rule written in, computation in code, as collected
on [how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).
Whether a small English model is enough for your case at all is the subject of
[when a small model is enough, and when it is not](when-a-small-model-is-enough.md).

## Questions in English, text in English

Whichever option you choose, keep the questions in English and make the state English too.
Field names in another language ("kundennachricht") are text the model has to read, and they
fall under the same limit. The state design that makes this easy is on
[sending JSON as the text: designing the state](designing-the-state-as-json.md).

Mixed-language text, an English message with a quoted Spanish reply for example, is a case to
handle deliberately: translate the quoted part, or put it in its own field and ask your
questions about the English one.

## Short answers to the questions that lead here

**Does jevos work in languages other than English?** It is documented as English only, and we
have not measured it on any other language. Do not rely on it for other languages.

**Can I translate text to English and then ask jevos?** Yes. Facts usually survive translation
well; tone and politeness are at more risk. Test on translated examples of your own data.

**What happens if I send French text?** You get a probability, as for any input, with no error.
We do not know what it is worth, so do not act on it.

**Should the questions be in English?** Yes, and the field names in the state as well.

**What should I use for multilingual text?** A model that reads those languages, either for all
traffic or for the non-English part behind a language check.

**See also:** [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md),
[email triage with a local LLM](email-triage-with-a-local-llm.md) and
[small language models explained](small-language-models-explained.md).

## Sources

- English only: our own statement of the model's scope.
- The 220 ms latency for about 190 tokens and the 0.811 on 2,000 policy questions: the
  [jev README](https://github.com/feder-cr/jev) and our measurements on the reference laptop.
- 0.954 on stated facts and 0.938 on tone: our 999-question test set, `jevos-q4_k_m`.
- No measurement on other languages exists, and none is claimed on this page.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model that always returns a number,
which is why its English-only limit has to be enforced in your code rather than discovered in
its answers.*
