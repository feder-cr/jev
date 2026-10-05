---
title: "jevos vs SetFit: zero-shot vs few-shot classification"
description: "SetFit trains a classifier from a few labelled examples per class; jevos needs no examples, only a well-written question. When each is the better start."
parent: "Comparisons"
nav_order: 7
---

# jevos vs SetFit: zero-shot vs few-shot classification

**SetFit trains a small classifier from a handful of labelled examples per class; jevos needs no
examples at all, only a yes/no question per label.** If you can label eight or so examples per
class and your classes are stable, SetFit gives you a fast, cheap, multilingual classifier that
you own. If you cannot label anything yet, or your "classes" are really conditions and rules that
change, a question is the quicker start. Neither is a large model, so the choice is mostly about what
you have: examples or definitions.

Conflict of interest, in one line: we build jevos; the SetFit facts below come from its
documentation and repository, fetched 2026-09-29.

The two tools sit at neighbouring points on one scale. Zero examples, a few examples, thousands of
examples: each step up buys accuracy and costs labelling. SetFit's own documentation even covers
the zero-example case, which makes the comparison sharper.

This page is what each one asks of you, how each handles a new label, SetFit's zero-shot mode,
speed and size, languages, and a way to choose.

## What each one asks of you

SetFit describes itself as "an efficient and prompt-free framework for few-shot fine-tuning of
Sentence Transformers." You give it labelled examples; it trains a Sentence Transformer body and
a classification head (scikit-learn or a PyTorch alternative), and generates "rich embeddings
directly from text examples" instead of using handcrafted prompts. The headline claim on its
docs: "with only 8 labeled examples per class on the Customer Reviews sentiment dataset, SetFit is
competitive with fine-tuning RoBERTa Large on the full training set of 3k examples."

jevos asks for the opposite input. No examples, no training step: a text and a question.

```json
{
  "model": "jev-latest",
  "state": "The box arrived empty. This is the second time!",
  "questions": {
    "missing": {"type": "noul", "instructions": "Does the customer say the item was missing from the package?"},
    "upset":   {"type": "noul", "instructions": "Is the customer upset?"}
  }
}
```

Each question comes back as its own `noul`, a probability of yes. Where SetFit learns what a class
means from examples, jevos is told what it means in words. That puts the burden on the wording,
which is why [why wording changes an LLM's answer](why-wording-changes-the-answer.md) belongs in
any evaluation of a zero-shot setup.

## How each handles a new label

With SetFit, a new class needs its own examples and a new training run. Training is fast by the
project's account, "typically an order of magnitude (or more) faster to train and run inference
with" than approaches built on large models, so the labelling, not the training, is the real cost.

With jevos, a new label is a new question in the request, live on the next call. The same goes for
changing what a label means, or putting a rule inside it: "Our policy refunds items reported
missing within 30 days of delivery. Should this customer get a refund?" is a README example that
no set of eight examples would pin down, because the rule, not the wording, decides it.

## SetFit's own zero-shot mode

SetFit can start without labels too. Its zero-shot how-to generates a synthetic dataset from the
class names with a template, `This sentence is {}` by default, through `get_templated_dataset()`,
and trains on that as usual. In its example the docs report 59.1% accuracy for zero-shot SetFit
with `BAAI/bge-small-en-v1.5`, against 37.65% for the Transformers zero-shot pipeline with
`facebook/bart-large-mnli`, and 67 times the speed. Those are SetFit's numbers on SetFit's example;
we have not reproduced them, and we have not run jevos on that dataset.

The difference in approach is what matters here. Templated zero-shot learns from label names; a
yes/no question can say much more than a label name, such as a definition, an exclusion, or a
condition. When the class name is enough, the templated route is cheap. When it is not, a question
carries the missing information.

## Speed and size

A Sentence Transformer with a classification head is a light model. SetFit's zero-shot page
reports about 0.46 ms per sentence for its example model, on its own setup. jevos is a language
model with 8-bit weights on the CPU: 28 ms for a short request and 130 ms for a long one, on an
Intel Core Ultra 7 255H with 16 threads.
The hardware differs, so do not divide one by the other, but the class is clear: per text, an
embedding classifier costs far less compute.

jevos narrows the gap when there are many labels on one text, because the text is read once for
every question: three questions took about 66 ms against 49 ms for one.

## Languages

SetFit "can be used with any Sentence Transformer on the Hub", so multilingual classification is a
matter of starting from a multilingual checkpoint. jevos reads English only. For non-English text
this is the deciding row, and it favours SetFit or another multilingual option; see
[using an English-only LLM with other languages](using-an-english-only-model-with-other-languages.md).

## A way to choose

| You have... | Start with |
|---|---|
| 8 or more labelled examples per class, stable classes | SetFit |
| no examples, labels you can describe in a sentence | jevos |
| labels defined by a rule or a policy | jevos, with the rule in the question |
| non-English text | SetFit with a multilingual checkpoint |
| very high volume on short texts | SetFit |
| many conditions per text, each needing its own probability | jevos |

The two combine well over time. Start with questions, send uncertain answers to people, keep their
decisions, and once a task has a stable label set and enough examples, a few-shot classifier is a
natural next step. The broader version of that trade-off, with full fine-tuning, is on
[a yes/no LLM vs a fine-tuned BERT classifier](yes-no-llm-vs-fine-tuned-bert.md).

## Short answers to the questions that lead here

**What is SetFit?** A framework for few-shot fine-tuning of Sentence Transformers into classifiers,
without prompts, from a small number of labelled examples per class.

**Zero-shot or few-shot: which is better?** With a handful of good examples and stable classes,
few-shot usually is. With no examples, or labels defined by rules, zero-shot questions are the
practical start.

**Can SetFit work with no labels?** Yes, by training on synthetic examples made from class names
with a template, per its zero-shot guide.

**Is SetFit faster than jevos?** Per text, an embedding classifier needs far less compute than a
language model. We have not measured both on the same hardware.

**Which supports other languages?** SetFit, through multilingual checkpoints. jevos is English only.

**See also:** [jevos vs bart-large-mnli](jevos-vs-bart-large-mnli.md),
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md)
and [intent detection with a local LLM](intent-detection-with-a-local-llm.md).

## Sources

- SetFit description, the 8-examples claim, speed, prompts and multilingual support: the
  [SetFit documentation](https://huggingface.co/docs/setfit/index) and
  [repository](https://github.com/huggingface/setfit), fetched 2026-09-29.
- Zero-shot SetFit, `get_templated_dataset()`, 59.1% vs 37.65%, 0.46 ms and 67 times: SetFit's
  [zero-shot how-to](https://huggingface.co/docs/setfit/how_to/zero_shot), their measurements,
  fetched 2026-09-29.
- jevos latency, the three-question timing and the README refund rule: the
  [jev README](https://github.com/feder-cr/jev), our own measurements.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which starts where the labelled
examples have not been written yet.*
