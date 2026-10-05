---
title: "jevos vs bart-large-mnli for zero-shot classification"
description: "NLI zero-shot classification with a hypothesis per label next to a yes/no question per label: how each works, context length, speed class, languages."
parent: "Comparisons"
nav_order: 5
---

# jevos vs bart-large-mnli for zero-shot classification

**bart-large-mnli classifies by asking, for each label, whether the text entails a hypothesis
such as "This text is about politics."; jevos classifies by asking, for each label, a yes/no
question you write, such as "Is this message mainly about a refund?".** Both are zero-shot and
both score labels independently when you want them to. The NLI model is smaller (0.4B parameters
per its card), with a 1,024-position input; jevos has an 8,192-token context and
questions that can carry a rule, not only a topic. For short texts and topic labels the NLI model
is the lighter tool. For longer texts, or labels that need a condition spelled out, a question is
the more expressive unit.

Conflict of interest, in one line: we build jevos; the facts about bart-large-mnli come from its
Hugging Face model card and config, fetched 2026-09-29.

The two methods are closer than they look. A hypothesis is a statement the model checks against
the text; a yes/no question is the same check phrased as a question. The difference is in what
each model was built to check and how much you can say in the check.

This page is how NLI zero-shot works, what changes with a question per label, context length,
the speed class of each, languages and licence, and a way to choose.

## How NLI zero-shot classification works

The model card describes the method in two steps. The text to classify is posed as the premise,
and a hypothesis is built from each candidate label: for the label "politics", the card's
example is `This text is about politics.` The model scores entailment, neutral and contradiction
for the pair (the three classes in its config), and the probabilities for entailment and
contradiction are converted to a label probability.

By default the labels compete with each other. With `multi_label=True`, the card says, each class
is calculated independently, which is the right mode when a text can belong to several labels.

The card's usage is one line of the Transformers pipeline:

```python
from transformers import pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
```

## What changes with a question per label

A jevos request for the same job asks one question per label about the same text:

```json
{
  "model": "jev-latest",
  "state": "Hi, my card was charged but the order page still says payment pending.",
  "questions": {
    "billing":  {"type": "noul", "instructions": "Is this message mainly about a payment, a charge or a refund?"},
    "shipping": {"type": "noul", "instructions": "Is this message mainly about delivery or tracking of a parcel?"}
  }
}
```

Each comes back as its own `noul`, which is the `multi_label=True` behaviour by construction: the
probabilities do not sum to 1, and you pick the label, or several, in code.

Three practical differences follow.

- **What a label can say.** A hypothesis template is usually one pattern filled with a label
  name. A question can hold a definition and a rule: "Our policy refunds items reported missing
  within 30 days of delivery. Should this customer get a refund?" is a README example. That is a
  decision, not a topic.
- **Shared reading.** jevos reads the text once for every question in a request; three questions
  took about 66 ms against 49 ms for one. An NLI model scores each premise and hypothesis pair.
- **Structured input.** jevos takes a JSON object as `state` as well as a string, so fields such as
  `delivered: "5 days ago"` can be sent as they are.

The full recipe, with the thresholds that handle "no label fits", is on
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).

## Context length

bart-large-mnli's config sets `max_position_embeddings` to 1,024, the most tokens it can take for
premise and hypothesis together. Longer texts are cut or have to be split. jevos has an 8,192-token
context for the text and all questions of a request. For support tickets and reviews neither
limit matters; for contracts, reports or long email threads, the difference decides whether
you chunk. Chunking strategy is on
[yes/no questions about long documents](yes-no-questions-about-long-documents.md).

## Speed class

We have not benchmarked bart-large-mnli, so there is no head-to-head number here. What can be
said is the class of each. The NLI method scores one premise and hypothesis pair per label, so
its cost grows with the number of labels times the length of the text. jevos runs on a CPU, one shared reading of the text plus a
small cost per question: 28 ms for a short request and 130 ms for a long one on an
Intel Core Ultra 7 255H with 16 threads (measured with jevos-v3, the same size and speed as jevos-v4).

For a third-party reference point, the SetFit documentation reports bart-large-mnli at about 31
ms per sentence in its own zero-shot example, measured on its setup. That number is theirs, not
ours, and says nothing about jevos on the same hardware.

## Languages and licence

The card describes a checkpoint of bart-large trained on the MultiNLI dataset and does not list
other languages; check before using it on non-English text. jevos reads English only. For other
languages, neither is the right default, and a multilingual model is the honest answer, as
[using an English-only LLM with other languages](using-an-english-only-model-with-other-languages.md)
explains.

Both are MIT: the card lists MIT for the model, and jevos' code is MIT.

## Which one to pick

| If your situation is... | Lean toward |
|---|---|
| short English texts, topic labels, Transformers already in the stack | bart-large-mnli |
| labels that need a definition or a policy in them | jevos |
| texts over about a thousand tokens | jevos |
| a CPU-only service, one native binary to deploy | jevos |
| many labels on very short texts, cost per label matters most | measure both |

Whichever you pick, measure on a hundred of your own labelled cases. Zero-shot accuracy depends
heavily on how the labels are worded, for both methods.

## Short answers to the questions that lead here

**What is bart-large-mnli?** A 0.4B-parameter checkpoint of bart-large trained on MultiNLI, used
for zero-shot classification by turning each label into an entailment hypothesis.

**Is a yes/no question the same as an NLI hypothesis?** Close. Both check one statement against
the text; a question can also carry a definition or a rule.

**Which handles longer texts?** jevos, with 8,192 tokens of context against bart-large-mnli's 1,024
positions.

**Can both assign several labels?** Yes: bart-large-mnli with `multi_label=True`, jevos because
every question is answered independently.

**Which is more accurate?** We have not compared them on the same set. Test both on your labels.

**See also:** [jevos vs SetFit](jevos-vs-setfit.md),
[a yes/no LLM vs a fine-tuned BERT classifier](yes-no-llm-vs-fine-tuned-bert.md) and
[mainly about: questions for messages with several topics](mainly-about-questions-for-mixed-messages.md).

## Sources

- bart-large-mnli method, `multi_label=True`, MultiNLI, 0.4B parameters, MIT licence and pipeline
  example: the [model card](https://huggingface.co/facebook/bart-large-mnli), fetched 2026-09-29.
- `max_position_embeddings` of 1,024 and the three NLI classes: the model's
  [config.json](https://huggingface.co/facebook/bart-large-mnli/blob/main/config.json), fetched
  2026-09-29.
- The 31 ms per sentence figure: SetFit's
  [zero-shot how-to](https://huggingface.co/docs/setfit/how_to/zero_shot), their measurement,
  fetched 2026-09-29.
- jevos latency, the three-question timing and the 8,192-token context: our own measurements and
  the [jev README](https://github.com/feder-cr/jev).

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model on a laptop CPU;
a question per label is a hypothesis per label with room for a rule.*
