---
title: "LLM decisions vs keyword rules and regex"
description: "Regex and keyword lists are exact, fast and brittle to phrasing and negation; a yes/no LLM reads meaning. When to use each, and how to combine them."
parent: "Comparisons"
nav_order: 13
---

# LLM decisions vs keyword rules and regex

**Use regex and keyword rules for things with a fixed shape, such as an order number, an email
address, a URL or an exact phrase, and a yes/no model for things defined by meaning, such as "is
the customer asking for a refund?".** A regex is exact, practically free and fully predictable,
and it breaks the moment someone phrases the same idea differently or negates it. A model handles
paraphrase and negation, costs tens to hundreds of milliseconds per text on a CPU, and returns a
probability instead of a certainty. The best systems use both: regex to extract, the model to
judge.

Conflict of interest, in one line: we build jevos, a yes/no model, and this page still tells you
to keep your regexes for everything they do well.

The failure of keyword rules is not that they are wrong, it is that they are wrong silently. A
list that catches "refund" and "money back" misses "I want what I paid returned to my card", and
nothing tells you it missed. A model's failures show up as uncertain probabilities you can route
to review.

This page is what regex does best, where keywords break, what a model adds, a hybrid design, the
costs, and a note on regex that can hurt you.

## What regex does best

Anything with a syntax. Order IDs, dates in a known format, currency amounts, email addresses,
URLs, SKUs, error codes in logs. Here a pattern is the right tool on every axis: exact, auditable,
testable with a few examples, and orders of magnitude cheaper than any model. Even OpenAI's
latency guide has a section titled "Don't default to an LLM", pointing out that language models
"are therefore sometimes used in cases where a faster classical method would be more
appropriate."

If the question is "does this message contain an order number?", write the regex.

## Where keywords break

Keywords approximate meaning with strings, and meaning escapes in three common ways.

**Paraphrase.** "Cancel my subscription", "I don't want to be billed next month", "how do I stop
this". One intent, no shared keyword. Each new phrasing means a new rule, and the list is never
finished.

**Negation.** "I am not asking for a refund, just an explanation" contains the keyword and means
the opposite. Keyword lists that try to handle "not" within a few words of the keyword become the
most fragile part of the system.

**Context.** "This is sick" in a gaming chat and in a medical form. "Kill the process" in a server
log and in a threat. A string match has no idea which one it is looking at.

## What a yes/no model adds

A question states the meaning directly and lets the model find it in the text:

```json
{
  "model": "jev-latest",
  "state": "I'm not asking for a refund, I just want to know why I was charged twice.",
  "questions": {
    "wants_refund":   {"type": "noul", "instructions": "Is the customer asking for their money back?"},
    "billing_issue":  {"type": "noul", "instructions": "Is this a billing problem?"}
  }
}
```

Each question comes back as its own `noul`, the probability of yes. On our 999 questions written
after training, jevos was right 0.893 of the time on paraphrase questions, 0.858 on negation
questions and 0.954 on facts stated in the text, the three cases where keyword rules are weakest.

What it does not add is exactness. A probability of 0.8 is a strong yes, not a proof; the model
reads English only; and on arithmetic, 0.584 in the same test, it is worse than a line of code.
Calculations belong in code, as [small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md)
shows.

## A hybrid design: regex extracts, the model judges

The two work best in sequence, each doing its own part:

1. **Regex extracts the structured parts.** Order IDs, amounts, dates, links. These become
   fields.
2. **Code computes what depends on them.** Days since the order, whether the amount is over a
   limit, whether a link's domain is on your list.
3. **The model answers questions of meaning** about the text, with the computed fields in `state`
   when they help: "Is the customer asking for their money back?", "Is the tone threatening?".
4. **Code combines the answers** with thresholds and rules, and sends the uncertain middle to a
   person.

A cheap regex can also act as a pre-filter where a pattern is decisive, such as skipping the model
for auto-generated notifications. And an old keyword list is valuable as a test set: every text it
matched, reviewed by hand, is a labelled case for checking the model. The pattern for phishing,
where header checks and link parsing are exact and "does this ask for credentials?" is a meaning
question, is on [phishing email screening with a local LLM](phishing-email-screening-with-a-local-llm.md).

## What each one costs

| | regex / keywords | yes/no model (jevos) |
|---|---|---|
| Cost per text | negligible | 26 ms (about 30 tokens) to 112 ms (about 190) on our laptop CPU |
| Memory | negligible | about 1 GB with the model loaded |
| Handles paraphrase | only what you listed | yes, 0.893 in our test |
| Handles negation | badly, by special cases | 0.858 in our test |
| Exact on syntax | yes | no, and not needed |
| Output | match or no match | P(yes) per question |
| Changing a rule | edit a pattern | edit a question |

Several questions on the same text cost much less than separate calls, because the text is read
once: three questions took about 66 ms against 49 ms for one. So the model is affordable for
most message streams on a CPU, but not free, and nothing beats a regex on price.

## A note on regex that can hurt you

Regex has its own failure mode that models do not: catastrophic backtracking. OWASP describes
ReDoS as an attack that exploits the fact that most regex implementations "may reach extreme
situations that cause them to work very slowly (exponentially related to input size)." Its example
is `^(a+)+$`, where each extra "a" in a failing input doubles the number of paths the engine tries.
If your patterns run on user text, review them for nested quantifiers, or use an engine that does
not backtrack.

## Short answers to the questions that lead here

**Is an LLM better than regex for text classification?** For meaning, such as intent, tone and
paraphrase, usually yes. For fixed formats like IDs and emails, regex is better and far cheaper.

**Why do keyword filters miss things?** People phrase the same idea many ways, negate keywords and
use words in more than one sense. A list cannot enumerate meaning.

**Can I combine regex and an LLM?** Yes: regex to extract structured fields, code to compute, the
model to answer meaning questions, code to combine.

**How does a yes/no model handle negation?** Better than keyword rules: 0.858 on negation questions
in our test. Positive phrasing of the question still helps.

**Is a model fast enough to replace keyword rules?** For most message streams on a CPU, yes: 26 to
112 ms per request in our measurement. It will never be as cheap as a regex.

**See also:** [negation in yes/no questions](negation-in-yes-no-questions.md),
[checking text for personal data with yes/no questions](pii-check-with-yes-no-questions.md) and
[a yes/no LLM vs a business rules engine](yes-no-llm-vs-business-rules-engine.md).

## Sources

- Accuracy by kind (paraphrase 0.893, negation 0.858, fact 0.954, arithmetic 0.584): our 999-question
  test set on `jevos-q4_k_m`.
- Latency, memory and the three-question timing: our own measurements, in the
  [jev README](https://github.com/feder-cr/jev).
- "Don't default to an LLM": OpenAI, [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization),
  fetched 2026-09-29.
- ReDoS definition and the `^(a+)+$` example: OWASP,
  [Regular expression Denial of Service](https://community.owasp.org/attacks/Regular_expression_Denial_of_Service_-_ReDoS),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no model for the questions a
pattern cannot express, and no use at all for finding an order number.*
