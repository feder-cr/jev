---
title: "Multi-class text classification with a choice question"
description: "Put the labels in one choice question and get back one label, a probability per label and a confidence. How to write options, cost, accuracy, limits."
parent: "Question design"
nav_order: 13
---

# Multi-class text classification with a choice question

**For multi-class classification, where each text gets exactly one label, ask one `choice`
question with the labels as options in `criteria`; jevos-v4 returns the most probable option, a
probability for every option and a `confidence`.** In the README example, a message about an
empty box goes to `shipping` with 0.93 (billing 0.02, tech 0.05) and a confidence of 0.89. Each
option can carry a short description, which is where the classifier is really written. When
`confidence` is 0 the model cannot place the text, and the case belongs to a person.

The non-obvious part is that a choice and a set of yes/no questions answer different questions.
A choice asks "which one of these?" and always returns one of your options. Yes/no questions ask
"does this label apply?" once per label, and can come back with none or several. Picking the
wrong form causes more errors than the wording of any single label.

This page is the request and the answer, how to write options, choice against yes/no questions,
what a choice costs in time, how accurate it is, and where it is the wrong tool.

## What does a choice question send and return?

The options go in `criteria` as a dictionary: the key is the label your code switches on, the
value an optional description. The README's example:

```json
{
  "model": "jev-latest",
  "state": {"item": "wireless mouse", "customer_message": "The box arrived empty. This is the second time!"},
  "questions": {
    "team": {
      "type": "choice",
      "instructions": "Which team should handle this message?",
      "criteria": {
        "billing": "payments, invoices, refunds",
        "shipping": "deliveries, missing or damaged parcels",
        "tech": "a product that does not work"
      }
    }
  }
}
```

```json
{
  "model": "jevos-v4",
  "answers": {
    "team": {"type": "choice", "choice": "shipping",
             "probabilities": {"billing": 0.02, "shipping": 0.93, "tech": 0.05}, "confidence": 0.89}
  },
  "usage": {"input_tokens": 233, "output_tokens": 0}
}
```

`choice` is the label to act on. `probabilities` has one number per option; here they add up to
1.00, so they are not independent yes/no answers. `confidence` says how sure the pick is, down to
0 when the model cannot place the text. Nothing is generated, so there is no label to parse.

## How should I write the options?

Treat each option as a small definition, because the description is what the model holds against
the text.

- **Name the feature that separates neighbours.** A customer whose box arrived empty may want
  money back, so "billing" is not absurd; "missing or damaged parcels" is what says shipping owns
  it. When two options keep getting confused, rewrite their descriptions first.
- **Make the options exclusive.** If "refund request" and "shipping problem" can both be true of
  one message, make them yes/no questions, or two choices about different things.
- **Keep the keys stable.** Keys come back in `choice` and `probabilities`, so they are part of
  your code. Edit descriptions freely.
- **Decide what happens when nothing fits.** A choice cannot say "none of these" unless an option
  says it. Add a catch-all with a positive description ("a question about something else, such as
  opening hours or jobs"), or ask a yes/no gate question first. A bare "none of the above" gives
  the model nothing in the text to point at, the weakness the "other" label has on
  [zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).
- **Put the rule in the instructions,** and compute any number in code before asking.

## Should I use a choice or several yes/no questions?

| | one `choice` | one yes/no question per label |
|---|---|---|
| answer | exactly one label | none, one or several |
| probabilities | one per option, shared | one per label, independent |
| nothing fits | needs an option that says so | a threshold on the highest P(yes) |
| doubt | `confidence`, down to 0 | read the probabilities yourself |
| Jev SDK | Jev's shape, not promised unchanged | works unchanged (README) |

The same split exists elsewhere. The Hugging Face zero-shot classification pipeline has a
`multi_label` parameter, "Whether or not multiple candidate labels can be true", default `False`;
with `True`, "the labels are considered independent". A choice is the single-label form, yes/no
questions the multi-label one. That pipeline is compared with jevos on
[jevos vs bart-large-mnli](jevos-vs-bart-large-mnli.md).

Use a choice when labels are exclusive by construction (one queue owns a ticket), yes/no
questions when labels are tags. Both fit in one request: the README's API example asks a yes/no
question, a choice and a score about one state, read once, as explained on [many questions about one text](many-questions-about-one-text.md).

## How fast is a choice with many options?

On the README's laptop, an Intel Core Ultra 7 255H with 16 threads, a three-option choice takes
about 100 ms and a ten-option one about 170 ms, where one yes/no question takes about 20 ms.

So a two-option choice is the wrong form for billing-or-not: "Is this a billing problem?" is
cheaper. Options add up slowly: from three to ten the time rose by about 70 ms, less than double
for over three times the options (arithmetic on two figures, not a curve). We have not timed a
choice against the same labels asked as yes/no questions; if latency is tight, time both.

Keep descriptions short. A taxonomy of hundreds of classes is the wrong shape for one choice: walk
it level by level, as on
[product categorization with yes/no questions](product-categorization-with-yes-no-questions.md),
with one choice per level where the classes are exclusive.

## How accurate is it, and what is the confidence for?

On 2,676 held-out choice questions, jevos-v4's most probable option is right 79.2% of the time
(jevos-v3 78.8%). The README's two choice tasks, same questions and HTTP client for every system:

| choice task | jevos-v4 | Jev | Qwen3.5-4B | Laya |
|---|---|---|---|---|
| Rental policy | 0.76 | 0.91 | 0.60 | 0.31 |
| Authority rules (SemIf) | 0.81 | 0.98 | 0.78 | 0.64 |

Jev, the hosted model, is clearly ahead on both. Both sets helped choose the released checkpoint,
so jevos's scores there may be slightly optimistic, a problem discussed on
[benchmark contamination and truly held-out tests](benchmark-contamination-and-held-out-tests.md).

Roughly one pick in five being wrong is the honest default, so build on `confidence`, not on
`choice` alone. With jevos-v2 (not yet measured this way on jevos-v4), at confidence 0.75 or more
95% of the answers were right, on 46% of the questions; below 0.25, only 47%. That is the shape of
a review band:

```python
team = answers["team"]
if team["confidence"] >= HIGH:     # HIGH chosen on your own labelled messages
    route(team["choice"])
else:
    send_to_person(team)           # always includes confidence 0
```

Setting `HIGH` from labelled data is covered on
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

## When is a choice the wrong tool?

- **Several labels can be true.** A choice hides the second one. Ask yes/no questions, or ask what
  the text is mainly about, as on
  [mainly about: questions for messages with several topics](mainly-about-questions-for-mixed-messages.md).
- **The labels are ordered.** Low, medium, high is a scale: use a `score` (levels in `criteria`,
  lowest first; marked early) or boundary questions, as on
  [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).
- **The label is a computation.** A total over a limit belongs in code.
- **Many classes and plenty of labelled examples.** Embedding similarity or a trained classifier
  fits better; see [semantic routing vs yes/no questions](semantic-routing-vs-yes-no-questions.md).
- **Other languages.** jevos reads English, with 8,192 tokens of context.

## Short answers to the questions that lead here

**What is multi-class text classification?** Giving each text exactly one label from a fixed set
of more than two. When a text can get several labels, it is multi-label classification.

**How do I do multi-class classification with an LLM and no training data?** Write the labels as
options with short descriptions in one choice question. jevos-v4 returns the most probable
option, a probability per option and a confidence, without generating text.

**Why did it pick a label when none fits?** A choice always returns one of your options. Add a
positively described catch-all option, or ask a yes/no gate question first.

**What does confidence 0 mean?** The model cannot place the text among the options. Do not act on
`choice`: route the case to a person.

**How many options can a choice have?** The README times three and ten options. For large
taxonomies, ask level by level.

**See also:** [support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md),
[document classification with a local LLM](document-classification-with-a-local-llm.md) and
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- Our measurements, from the [jev README](https://github.com/feder-cr/jev): the choice example and
  its answer, the choice timings (Intel Core Ultra 7 255H, 16 threads), the 79.2% on 2,676
  held-out choice questions, two rows of the six-task table, and the confidence figures measured
  with jevos-v2. The 70 ms step is arithmetic on two of those timings.
- Hugging Face Transformers documentation, `ZeroShotClassificationPipeline`, `multi_label`:
  [huggingface.co/docs/transformers/main_classes/pipelines](https://huggingface.co/docs/transformers/main_classes/pipelines),
  fetched 2026-10-12.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where a choice comes back as one label
and a confidence, and the confidence is the field the routing code should read first.*
