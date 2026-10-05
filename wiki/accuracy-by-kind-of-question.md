---
title: "Accuracy by kind of question: why one number hides failures"
description: "Why an overall accuracy hides where a yes/no model fails, and how to tag your own questions by kind so the weak spots show up before production."
parent: "Evaluation"
nav_order: 10
---

# Accuracy by kind of question: why one number hides failures

**One accuracy number is an average over whatever mix of questions the test happened to contain,
so it describes your application only if your questions come in the same mix.** On our
999 hand-written yes/no questions the first jevos scored 0.757 overall, but 0.954 on questions
about a fact stated in the text and 0.584 on questions that need arithmetic (jevos-v4 scores
78.9% overall on the same set; per-kind numbers for jevos-v4 are not published). Tag each test question with the kind of
reasoning it needs, report accuracy per tag, and the failures that the average hid become a list
of what to route to the model and what to keep in code.

The point is not only that some kinds are harder. It is that the overall number can move up or
down by changing the mix, with no change in the model. Two teams using the same model on
different questions will see very different accuracy, and both will be right.

This page is a worked example of how the mix moves the number, a set of kinds you can reuse with a
test for each, how to tag questions that need two kinds of reasoning, how many questions a kind
needs, and what to do with the result.

## How much can the mix move the number?

The per-kind accuracies below were measured on the first jevos on our set; the application mixes are hypothetical, and
the resulting numbers are arithmetic, not measurements.

| Hypothetical application | Mix of questions | Expected accuracy |
|---|---|---|
| support triage that asks what customers say | 90% stated fact, 10% arithmetic | 0.9 times 0.954 + 0.1 times 0.584 = 0.917 |
| our test set as written | ten kinds, 32 to 221 questions each | 0.757 (measured, first jevos) |
| order checks that ask the model to compute | 50% arithmetic, 50% dates | 0.5 times 0.584 + 0.5 times 0.598 = 0.591 |

The same model, the same weights, and a spread from about 0.59 to about 0.92, purely from which
questions are asked. So "the model is 76% accurate" (the first jevos's overall figure) is not a property of the model. The per-kind
numbers are closer to one, and the full table of all ten kinds, with example shapes, is on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

## A set of kinds you can reuse

Tags are useful only if two people assign them the same way. Each kind below comes with a one-line
test to decide it.

| Kind | Tagging test |
|---|---|
| stated fact | could you answer by pointing at words in the text? |
| paraphrase | is the answer in the text, but in different words than the question? |
| tone | is it about how the text is written, not what it says? |
| intent | is it about what the writer wants to happen? |
| negation | does the answer turn on a "not", "never" or "no"? |
| not stated | is the right answer "the text does not say"? |
| rule | does it apply a policy or condition written in the question? |
| number against a threshold | does it compare one number with another? |
| dates and durations | does it need a difference between times? |
| arithmetic | does it need a sum, a difference or a product first? |

These ten fit business text: emails, tickets, logs, reviews, forms. Your domain may need its own.
Contract review might need "clause present" and "clause modified"; moderation might need "quotes
someone else" versus "says it themselves". Add a kind when you suspect it behaves differently, and
keep it if the numbers say so.

## Questions that need two kinds of reasoning

Many real questions combine steps. "Was the parcel late under our 5-day promise?" reads a date,
computes a duration and compares it with a threshold. Tag it with the hardest step it needs, here
dates and durations, because that step decides whether the model can answer. If you want more
detail, add secondary tags, but report on the primary one, or the kinds stop adding up to your
total.

This tagging habit also shows which questions to rewrite. A question tagged "arithmetic" can often
become a question tagged "stated fact" by computing the number in code and putting it in the state:
"The delivery took 9 working days" plus "Is that within the 5-day promise?" is a comparison, not a
subtraction. Structuring the state that way is covered on
[sending JSON as the text: designing the state](designing-the-state-as-json.md).

## How many questions does a kind need?

Enough that its range is narrower than the decision you will make with it. A kind with 30 questions
gives a rough range of plus or minus 8 points or more, which can tell "reliable" from "coin toss"
but not 0.86 from 0.90. In our set, tone had 32 questions and arithmetic 221, so the tone figure is
the less certain of the two, and we read it as "high", not as 0.938 to the third decimal.

Grow the kinds near your decision boundary first. If a kind sits clearly above 0.9 or clearly below
0.65, more questions will not change what you do with it.

## What to do with per-kind accuracy

- **Route by kind.** Reading kinds go to the model. Computing kinds go to code, with the model
  asked only about the words. On the first jevos every reading kind was above 0.84 and every computing kind
  below 0.73.
- **Set thresholds by kind.** A kind where the model is often wrong toward yes needs a higher bar
  to act on yes; the first jevos's per-kind mean P(yes) on no-answer questions ranged from 0.16 to 0.59, detailed
  on [why a small LLM says yes](why-a-small-llm-says-yes.md).
- **Decide model size by kind.** If the questions you cannot move to code are mostly in weak kinds,
  a small model is the wrong tool for them. The checklist is on
  [when a small model is enough](when-a-small-model-is-enough.md).
- **Re-measure when the mix changes.** A new product line, a new language of complaint, a new
  policy: any of them shifts the mix and the overall number with it.

## Short answers to the questions that lead here

**Why is my model's accuracy different from the benchmark?** Partly because your questions come in a
different mix of kinds. With our per-kind figures, a mix heavy on stated facts gives about 0.92 and
a mix of sums and dates about 0.59.

**What kinds of question do small LLMs get wrong?** In our measurement on the first jevos, the ones that need computing:
arithmetic 0.584, dates 0.598, numbers against a threshold 0.654. Reading kinds were all above 0.84.

**How do I tag my own questions?** Use a short list of kinds with a one-line test each, and tag by the
hardest reasoning step the question needs.

**How many questions per kind do I need?** At least 30 to tell strong from weak; more for kinds near
your threshold.

**Can I improve accuracy without changing the model?** Often, yes: move computing kinds to code and
rewrite those questions as reading questions.

**See also:** [building a yes/no test set for your own data](building-a-yes-no-test-set.md),
[evaluation metrics for yes/no classifiers](evaluation-metrics-for-yes-no-classifiers.md) and
[yes/no questions about tone and emotion](yes-no-questions-about-tone.md).

## Sources

- Per-kind accuracy, question counts per kind, and mean P(yes) on no-answer questions: our
  999 hand-written yes/no questions, measured on the first jevos (released 2026-09-27).
  Per-kind numbers for jevos-v4 are not published; its overall figure on the set is 78.9%.
- The expected accuracies for hypothetical mixes are weighted averages of those figures, not
  measurements on such mixes.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which reports ten accuracies for its
999-question test set next to the one overall figure, and plans with the ten.*
