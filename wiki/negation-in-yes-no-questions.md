---
title: "Negation in yes/no questions for an LLM"
description: "How a small LLM handles negation in yes/no questions: negated facts vs negated questions, what we measured, and why to ask positively and flip in code."
parent: "Question design"
nav_order: 2
---

# Negation in yes/no questions for an LLM

**Keep the negation in the text and out of the question: ask "Did the customer ask for a
refund?" and compute "did not" as 1 minus P(yes) in your code.** the first jevos handled negation that
appears in the text well, 0.858 on the negation questions of our 999-question test set (per-kind numbers for jevos-v4 are not published), but a
question that is itself negated adds a step between the words and the answer, and every such
step is a place for a small model to slip. A positive question with the flip done in code
costs nothing and removes the step.

The non-obvious part is that there are two different things called negation. "The customer
did not ask for a refund" is a negated fact, and reading it is part of understanding the text.
"Did the customer not ask for a refund?" is a negated question, and it asks the model to
answer the opposite of what it found. The first is the model's job; the second is yours.

This page is the difference between the two, what the measurement says and does not say,
the double negatives to avoid, and the small piece of code that replaces them.

## Negated facts versus negated questions

A negated fact is in the `state`:

```json
{
  "model": "jev-latest",
  "state": "Thanks for the quick reply. I don't need a refund, just a working charger.",
  "questions": {
    "wants_refund": {"type": "noul", "instructions": "Does the customer ask for a refund?"}
  }
}
```

The word "refund" is in the text, and a model that matched words would say yes. The correct
answer is no, because of "don't need". This is the case a yes/no model must get right, and it
is what the measurement below is mostly about.

A negated question looks like this:

```json
"questions": {
  "no_refund": {"type": "noul", "instructions": "Is it true that the customer does not want a refund?"}
}
```

It asks for the same information with the sign reversed. There is nothing to gain from the
reversal: the model has to find the fact and then invert it, and you get back a probability you
could have computed yourself as 1 minus the first one.

## What we measured

On the 999 yes/no questions written after the model was finished (10 scenarios, 10 texts each,
exactly half of the answers yes), 106 questions were labelled as negation questions. The first jevos
answered 0.858 of them correctly (jevos-v4 scores 78.9% overall on the set; per-kind numbers are not published). More telling is the average P(yes) the model gave
when the right answer was no: 0.17, one of the two lowest of any kind of question, next to tone
at 0.16. On questions about stated facts the same number is 0.29. So on negation the model is
not leaning toward yes, which is the failure a small model shows elsewhere and is measured on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

Being straight about the limit: we did not run the same questions twice, once positive and
once negated, so we have no number for how much a negated question costs on jevos-v4. The advice
on this page is a design habit, not a measured delta. It is cheap to follow and cheap to test
on your own cases.

Outside our measurements, the question has been studied on other models. Jang, Ye and Seo
(2022) tested models from 125M to 175B parameters on negated versions of task prompts and
found that all of them did worse on the negated prompts, and that larger models did not do
better, which is the opposite of the usual scaling pattern. Their setting is not ours (negated
task instructions, not yes/no questions about a text), but it is a reason not to assume
negation in the question is free.

## Ask positively, flip in code

```python
p_refund = answers["wants_refund"]["noul"]
p_no_refund = 1 - p_refund
```

That is the whole technique. It has three side benefits beyond accuracy:

- **One question serves two rules.** If one part of your system routes on "wants a refund" and
  another on "does not want a refund", both read the same probability.
- **Thresholds stay readable.** "Act when P(refund) is below 0.2" is clearer to review than
  "act when P(no refund) is above 0.8", and it is the same decision.
- **It composes.** Combining "not A" with "B" in code is a line of arithmetic, covered in
  [combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## Phrasings to avoid

| Instead of | Ask | Then |
|---|---|---|
| Did the customer not reply? | Did the customer reply? | 1 minus p |
| Is it false that the item arrived? | Does the customer say the item arrived? | 1 minus p |
| Is the customer not unhappy? | Is the customer happy with the outcome? | use p |
| Does the message lack an order number? | Does the message contain an order number? | 1 minus p |

The third row is the worst case, a double negative. "Not unhappy" is not the same as "happy"
in everyday English either, so rewriting it forces you to decide what you actually want to
know. "Lack", "fail to", "without", "absent" are negations in disguise and deserve the same
treatment.

## When a negation belongs in the question

Sometimes the condition is only natural in the negative: "Does the customer say this has not
happened before?" asks about a specific claim, the claim that it is the first time, and there
is no positive phrasing that means the same thing. The test is whether the negation is part of
what the writer said or part of how you want to use the answer. If the writer said it, keep
it, because you are asking about a negated fact. If it is only how your rule is worded, move it
to code.

Related: "not" is also how people write questions about missing information ("Does the text
not mention a date?"). That case has a better form, a gate question that asks whether the text
states the fact at all, explained on [ask whether the text says it](ask-whether-the-text-says-it.md).
The broader set of rules this page belongs to is on
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## Short answers to the questions that lead here

**Do LLMs understand negation?** A 2022 study of models up to 175B parameters found all of them
did worse on negated prompts. On our test set jevos handled negation inside the text well: 0.858 on 106 questions,
with a low average P(yes) of 0.17 when the answer was no.

**Should I write "not" in a yes/no question?** Only when the writer's claim is itself negative.
Otherwise ask the positive question and take 1 minus P(yes).

**Is 1 minus P(yes) the same as asking the negated question?** For a well calibrated model it
should be close. Computing it yourself removes a reasoning step and keeps both uses on one
number.

**Why does the model say yes when the text says "don't"?** It may be matching the word rather
than reading the sentence. Check your question names the subject and the action, and test it
on cases with and without the negation.

**See also:** [why wording changes the answer](why-wording-changes-the-answer.md),
[one condition per question](one-condition-per-question.md) and
[what P(yes) means](what-p-yes-means.md).

## Sources

- 0.858 accuracy on 106 negation questions and the mean P(yes) of 0.17, 0.16 and 0.29 on
  no-answer questions: our 999-question test set, measured on the first jevos.
- Joel Jang, Seonghyeon Ye, Minjoon Seo, "Can Large Language Models Truly Understand Prompts? A
  Case Study with Negated Prompts", 2022, [arXiv:2209.12711](https://arxiv.org/abs/2209.12711),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The one-line flip in this page is
the cheapest fix in the whole Question design section.*
