---
title: "A yes/no LLM vs a fine-tuned BERT classifier"
description: "Zero-shot yes/no questions or a classifier trained on your labels? When labels change or data is missing, and why fine-tuning usually wins on fixed tasks."
parent: "Comparisons"
nav_order: 6
---

# A yes/no LLM vs a fine-tuned BERT classifier

**If you have thousands of labelled examples and a label set that will not change, a fine-tuned
BERT-style classifier will usually beat a zero-shot yes/no LLM on accuracy, speed and cost per
prediction.** If you have no labels yet, labels that change every month, or decisions that depend
on a written rule, asking a yes/no question is the faster way to something that works, and
changing it is editing a sentence. Most teams that end up with a trained classifier would have
been well served by starting with questions.

Conflict of interest, in one line: we build jevos, a yes/no model, and this page still says the
trained classifier wins on its home ground.

The real comparison is not model against model. It is two ways of spending effort: labelling
data up front, or writing questions and checking them. Each has a point where it stops paying.

This page is what each approach needs before its first prediction, where each one wins, the cost
of changing your mind, a path that uses both, and how to decide with your own numbers.

## What each approach needs before the first prediction

A fine-tuned classifier needs a labelled dataset and a training run. The BERT paper's abstract
describes the idea that made this standard: the pre-trained model "can be fine-tuned with just
one additional output layer to create state-of-the-art models for a wide range of tasks." In the
Hugging Face text classification guide, the recipe is concrete: load a labelled dataset (their
example is IMDb movie reviews, positive or negative), tokenize it, define `id2label` and
`label2id`, load the model with the number of labels, train, evaluate.

A yes/no model needs a question. For jevos, that is a request:

```json
{
  "model": "jev-latest",
  "state": "I was charged twice for the same order.",
  "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}}
}
```

The README's answer to that request is `"noul": 0.9`. No dataset, no training, no GPU: the model
runs on a CPU with about 1.2 GB of memory. What it does need is a question worded well, which is
its own skill; see [how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## Where the trained classifier wins

Be straight about it: on a fixed task with plenty of data, training is the stronger option.

- **Accuracy on your distribution.** A classifier trained on your own labels learns your
  categories as your team applies them, including the unwritten conventions no question
  captures.
- **Cost per prediction.** A small encoder with one output layer is cheap to run, and at high
  volume that matters more than anything on this page.
- **No wording sensitivity.** There is no prompt, so no rephrasing of a question can move the
  answer; the behaviour is fixed by the labels it was trained with.
- **Language.** You can train on any language you have labels for. jevos reads English only.

If all four describe your situation, train the classifier.

## Where questions win

- **No labels yet.** A question works on day one. A classifier needs a dataset first, and building
  one is usually the slowest part of the project.
- **Labels that change.** Adding "is this about the new subscription plan?" is one line. Adding a
  class to a trained model means new labelled examples for it and a new training run.
- **Rare classes.** A category that appears a few times a month may never collect enough examples
  to train. A question does not need any.
- **Rules in the label.** "Should this customer get a refund, given that our policy refunds items
  reported missing within 30 days?" is a policy applied to a text, and the policy can change
  tomorrow. A classifier would learn last quarter's policy from last quarter's labels.
- **Probabilities per condition.** Each question returns its own P(yes), so a failure tells you
  which condition failed, and a review band on uncertain answers is a threshold, not a new model.

Questions also have a measured weak spot: computation. On our 999-question set, jevos was right
0.954 of the time on facts stated in the text and 0.584 on arithmetic, so a label that depends on
a sum or a date should be computed in code whichever approach you use.

## The cost of changing your mind

| Change | Trained classifier | Yes/no questions |
|---|---|---|
| add a label | label examples, retrain, redeploy | add a question |
| redefine a label | relabel affected examples, retrain | edit the question |
| change a policy threshold | relabel, retrain | edit the rule in the question |
| move to a new language | new labels in that language | not supported by jevos |
| handle ten times the volume | cheap | more CPU time per text |

The table is the argument in short. Training front-loads the cost and makes every later change
expensive; questions keep changes cheap and pay more per prediction.

## A path that uses both

A common sequence is to start with questions, route the uncertain middle to people, and keep
what they decide:

1. Ask yes/no questions and act on confident answers.
2. Send the band between the thresholds to a person, as on
   [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).
3. Store every human decision with the text. Over months, that is a labelled dataset built from
   your real traffic.
4. When one task has stabilised and has enough labels, train a classifier for that task and keep
   questions for everything that still changes.

The human decisions are the labels here, not the model's answers, which keeps the dataset honest.

## How to decide with your own numbers

Build a test set before choosing: a hundred or so real cases, labelled by hand, split by the kind
of question, never used to tune anything. [Building a yes/no test set](building-a-yes-no-test-set.md)
covers how. Run the questions on it. If they reach the accuracy you need, you are done without
training anything. If they fall short on a stable, high-volume task and you can get labels, that
gap is the case for training.

## Short answers to the questions that lead here

**Is a zero-shot LLM better than fine-tuning BERT?** Not on a fixed task with thousands of labels,
where the trained classifier usually wins. It is better when labels are missing or change.

**How many labels do I need to fine-tune?** It depends on the task; the Hugging Face guide uses a
full public dataset. If you have only a handful per class, look at
[few-shot methods such as SetFit](jevos-vs-setfit.md).

**Can I add a label without retraining?** With yes/no questions, yes: add a question.

**Is a yes/no model slower?** Usually per prediction, yes. jevos took 54 to 220 ms per request on
a laptop CPU; a small encoder is typically cheaper.

**Can I use both?** Yes. Start with questions, collect human decisions from the review band, and
train once a task is stable.

**See also:** [zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md),
[jevos vs bart-large-mnli](jevos-vs-bart-large-mnli.md) and
[when a small model is enough](when-a-small-model-is-enough.md).

## Sources

- The fine-tuning idea: Devlin et al., [BERT abstract on arXiv](https://arxiv.org/abs/1810.04805),
  fetched 2026-09-29.
- The fine-tuning recipe (IMDb, `id2label`, number of labels): Hugging Face,
  [text classification guide](https://huggingface.co/docs/transformers/tasks/sequence_classification),
  fetched 2026-09-29.
- The billing example and its 0.9, memory and latency: the [jev README](https://github.com/feder-cr/jev).
- Accuracy by kind (0.954 facts, 0.584 arithmetic): our 999-question test set on `jevos-q4_k_m`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model for the stage
before a labelled dataset exists.*
