---
title: "Structured output vs a probability"
description: "JSON mode and schemas make a model's answer parse; a probability also gives a threshold and has no format to break. When each fits, and how to use both."
parent: "Agents and routing"
nav_order: 10
---

# Structured output vs a probability

**Structured output makes a generated answer fit a format: JSON mode returns valid JSON, and
schema-constrained output returns JSON that matches the schema you supplied. A probability
answers a different need: it is a number between 0 and 1 per yes/no question, with no format to
break, and it tells you how sure the model is, so code can set a threshold.** For extracting
fields or generating content, structured output is the right tool. For a decision, a probability
carries more information than a `true` in a JSON object.

A conflict of interest: we build jevos, which returns probabilities. The two are not rivals so
much as answers to different questions: "what does the text contain?" is extraction, and "should
I act?" is a decision. Much of the friction in LLM apps comes from using the first to do the
second.

This page is what structured output fixes, what it leaves open, what a probability adds, a side
by side, when structured output is the right choice, and how to use both in one pipeline.

## What does structured output fix?

It fixes parsing. A model asked for JSON in the prompt alone may add a sentence before the
brace, skip a key, or invent a value. OpenAI's documentation separates two levels: JSON mode
produces valid JSON, and Structured Outputs goes further and makes the response adhere to the
JSON Schema you supply, so required keys are not omitted and enum values stay in the list. Its
documentation also describes explicit refusals, reported in a separate `refusal` field that code
can detect.

That is real progress. A decision encoded as `{"is_billing": true}` with a schema will parse,
and a label constrained to an enum will be one of your labels.

## What it leaves open

A schema constrains what the value may look like, not how it was chosen.

- **No confidence.** `true` from a model that was nearly split and `true` from one that was sure
  look the same. There is nothing to put a threshold on.
- **One value per field.** An enum field returns one label. If the text fits two, the second is
  gone, and you cannot see how close it came.
- **Asking for a confidence field does not fix it.** A `"confidence": 0.8` field is another
  generated value, a number the model wrote, not a probability computed from its own answer. Why
  that differs is on
  [LLM confidence scores: probabilities vs self-reported confidence](llm-confidence-score-probability-vs-self-report.md).
- **Output tokens are still generated,** and generation takes time per token and is billed per
  token on hosted APIs.

## What a probability adds

A yes/no model such as jevos reads the text and the question and returns P(yes). No token is
generated: every response reports `output_tokens: 0`.

- **A threshold in code.** Act at 0.5, or at 0.9 where a wrong yes is expensive, or send the
  middle to a person. The method is on
  [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).
- **Ranking.** Sort a queue by P(yes) and review from the top.
- **Several labels at once.** One question per label, each with its own probability.
- **Calibration you can check.** On the natural yes/no questions of our held-out split,
  calibration error was 0.009: across many answers near 0.8, about 80% were right. On new kinds
  of questions this does not carry over automatically, and our measurements show a lean toward
  yes on arithmetic and dates; see
  [LLM calibration explained](llm-calibration-explained.md).
- **Nothing to parse.** The answer is a number in a fixed place in the response.

## Side by side

| | Structured output | A probability per question |
|---|---|---|
| Output | generated JSON that fits a schema | one number from 0 to 1 per question |
| Parses | yes, schema adherence per the docs | yes, there is no text |
| Confidence | not part of the answer | the answer is the confidence |
| Threshold | not possible on a boolean | yes, set in code |
| Several labels | one per field unless you design for it | one probability each |
| Extracting values (names, dates, amounts) | yes | no |
| Output tokens | yes | none |
| Refusals | detectable in a `refusal` field (OpenAI) | not applicable, no text |

## When structured output is the right choice

- **Extraction.** Pulling the order number, the date and the amount out of an email is not a
  yes/no question. jevos cannot return values; a schema-constrained model can.
- **Generation with shape.** A reply plus a category plus a list of follow-ups, in one object.
- **Many fields at once from a large model you already call.** If you are paying for the call
  anyway, a schema keeps the result usable.
- **Languages other than English.** jevos reads English only.

## Using both in one pipeline

The two combine naturally, and the split mirrors the one between code and model elsewhere in this
wiki: extract with a schema, compute in code, decide with a probability.

1. **Extract** the facts with structured output: `delivered_on`, `item`, `reported_issue`.
2. **Compute** in code what depends on numbers or dates, such as days since delivery. Small models
   are weak at this; the measurement is on
   [small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).
3. **Decide** with yes/no questions over the resulting state, the rule written into each question.

The README's refund example is step 3: a state with the item, "delivered: 5 days ago" and the
customer's message, and three questions. It returns 0.93 for refund, 0.83 for upset and 0.04 for
wrong item, three probabilities a single boolean field could not have given.

Where the decision is the only thing the call does, step 1 is not needed at all: the text goes in
as `state` and the question is asked directly. That rewrite is covered on
[replacing chat LLM calls with yes/no questions](replacing-llm-calls-with-yes-no-questions.md).

## Short answers to the questions that lead here

**What is structured output?** A model response constrained to a format, from valid JSON up to
JSON that matches a schema you supply.

**Is JSON mode the same as a schema?** No. In OpenAI's terms, JSON mode makes the output valid
JSON; Structured Outputs also makes it adhere to your schema.

**Can I get a confidence score from structured output?** You can ask for a confidence field, but
it is a generated number, not a probability computed from the answer.

**When is a probability better than a boolean?** When you need a threshold, a review band, a
ranking, or more than one label per text.

**Can jevos return JSON fields?** No. It returns one probability per yes/no question. Use a
schema-constrained model for extraction.

**See also:** [why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md),
[what P(yes) means, and what it does not](what-p-yes-means.md) and
[jevos vs the OpenAI API for yes/no classification](jevos-vs-openai-api-for-classification.md).

## Sources

- OpenAI, [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs),
  for JSON mode versus schema adherence and the `refusal` field, fetched 2026-09-29.
- Our measurements: the 0.009 calibration error on 6,397 natural yes/no held-out questions
  (`jevos-q8_0`); the refund example and `output_tokens: 0` from the
  [jev README](https://github.com/feder-cr/jev).

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. There is no JSON for it to get wrong because it writes none.*
