---
title: "Decision engine vs decision model"
description: "A decision engine executes rules you wrote; a decision model reads free text and returns probabilities. Where each fits and how to combine the two."
parent: "Comparisons"
nav_order: 15
---

# Decision engine vs decision model

**A decision engine executes logic you wrote, as rules, decision tables or scoring formulas, over
structured inputs; a decision model reads unstructured text and returns a probability for each
allowed answer.** They do different halves of one job. The engine cannot tell whether "The box
arrived empty. This is the second time!" reports a missing item; the model should not be the one
comparing 5 days with a 30-day limit or adding up risk points. Combined, the model answers the
fuzzy questions about the text and the engine applies the rule to those answers.

Conflict of interest, in one line: we build jevos, a decision model.

The names make this harder than it should be. In the OMG standard DMN, "Decision Model and
Notation", a decision model is the logic itself, which an analyst can read and an engine can
execute. On this wiki, a decision model is a model such as jevos, TypeSafe's Jev or
Microsoft-Decision-1 that reads text and returns probabilities. Same two words, opposite sides of
the split.

This page is what each one is, where each fits, a decision table fed by a model, how an engine
should take choice and score answers, and when you need neither. The measured case for the split,
by kind of question, is on
[a yes/no LLM vs a business rules engine](yes-no-llm-vs-business-rules-engine.md).

## What is a decision engine?

Software that evaluates logic someone wrote over facts it is given: rules in code, a scoring
formula or a decision table. The same facts give the same outcome, and a policy change is a
reviewed edit to one rule.

DMN, an OMG standard, covers the decision-table kind. OMG calls it "a modeling language and notation
for the precise specification of business decisions", whose expression language defines decision
logic "in sufficient detail to allow execution", and which "is designed to be usable alongside the
standard business process notation BPMN". In Camunda's documentation, a decision table "consists
of inputs, outputs and rules", and its hit policy decides what the result holds: under FIRST,
"the output of the first satisfied rule".

An engine needs fields such as `item_missing = true`, and nothing in it gets there from a
customer's sentence.

## What is a decision model?

A model that takes a text and typed questions and returns probabilities instead of generated text.
jevos answers in TypeSafe Jev's wire format: a `noul` returns P(yes), a `choice` the most probable
option with a probability per option and a `confidence`, and a `score` an expected level with a
probability per level and a `confidence`. Microsoft says of its hosted Microsoft-Decision-1 that it
"doesn't generate a free-form response or written rationale" and "returns a typed, numerical
decision". The category is defined on [what is a decision model in AI?](what-is-a-decision-model.md).

It is strong at tone, intent and what the text says, in words nobody listed in advance, and weak
at everything exact: on an earlier test with jevos-v2, a fraud score from six rules was right 34%
of the time, barely above the most common level, and confidently wrong.

## Where does each one fit?

| | Decision engine | Decision model |
|---|---|---|
| Input | structured fields | free text, or JSON with text in it |
| Output | an outcome | a probability per allowed answer |
| Strong at | dates, sums, limits | tone, intent, what the text says |
| A policy change is | an edited rule | a reworded question, to re-test |
| Explains itself by | the rule that fired | the question and its probability |
| Fails by | a case no rule covers | a misreading that can look confident |

Use the engine alone when every input is already a field, the model alone for light, reversible
routing ("Is this a billing problem?"), and both whenever a written policy depends on what a
person wrote.

## How do the two work together?

The model turns text into facts; the engine applies the policy to those facts and to the fields
your systems already hold. One request asks both questions about the message:

```json
{
  "model": "jev-latest",
  "state": {"customer_message": "The box arrived empty. This is the second time!"},
  "questions": {
    "missing": {"type": "noul", "instructions": "Does the customer say the item was missing from the package?"},
    "team": {"type": "choice", "instructions": "Which team should handle this message?",
             "criteria": {"billing": "payments, invoices, refunds",
                          "shipping": "deliveries, missing or damaged parcels",
                          "tech": "a product that does not work"}}
  }
}
```

Code turns `missing` into yes, no or unsure with two thresholds, and a table does the rest. This
one is illustrative, with hit policy FIRST, so row order matters:

| missing (model) | days since delivery | amount | outcome |
|---|---|---|---|
| unsure | any | any | review by a person |
| yes | 30 or less | 50 or less | refund |
| yes | 30 or less | above 50 | review by a person |
| yes | above 30 | any | a person confirms the decline |
| no | any | any | ask what went wrong |

The model fills one column; the window, the cap and the rule order stay readable, and a dispute
traces to a misread column or a rule.

The other way works too: code computes what is exact and writes it into the state as words, like
the README's "delivered": "5 days ago". Our game races go furthest: the game code
words each move's effect ("Moving up: the snake moves closer to the food. Should the snake move
up?"), the model answers, and code plays the move with the highest P(yes), as on
[Snake AI: a local model vs a cloud API](snake-ai-local-model-vs-cloud-api.md).

## How should an engine take choice and score answers?

As a category plus a confidence, never as a bare label or a raw average.

**Choice.** Pass the option and the `confidence`, with a low-confidence rule first. The README's
choice example, the same message with the item name, returns shipping at 0.93 with confidence
0.89. On jevos-v2, answers with confidence 0.75 or more were right 95% of the time, on 46% of the
questions; below 0.25, 47%. More on
[multi-class text classification with a choice question](multi-class-text-classification-with-a-choice-question.md).

**Score.** The `score` field is an expected level, an average, so a rule such as "score at least
1" can fire on a spread with no peak. The README's "How angry is the customer?" returns 1.25 with
probabilities 0.32, 0.27, 0.25 and 0.16 and confidence 0.0. Give the engine the most probable
level and the confidence, send confidence 0 to a person, or ask "is it at least angry?" as a
yes/no, as on [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).

**Sums.** Ask each signal as a yes/no question and let the engine add the points.

## When do you need neither?

- **The output must be text.** Microsoft's guidance for its model: "Use a generative LLM instead
  when the application needs to create, summarize, rewrite, or explain content." The same holds
  for jevos.
- **One fixed task, many labelled examples, high volume.** A classifier trained for that task can
  fit better, as on [a yes/no LLM vs a fine-tuned BERT classifier](yes-no-llm-vs-fine-tuned-bert.md).
- **The decision is a search**, such as a schedule: a job for a solver.

## Short answers to the questions that lead here

**What is the difference between a decision engine and a decision model?** The engine executes
rules you wrote over structured fields. The model reads text and returns probabilities.

**Is DMN an AI decision model?** No. In DMN's vocabulary a decision model is logic you write, for
an engine to execute. Its tables can take a model's answers as inputs, like any other field.

**What about decision intelligence?** We could not fetch a primary definition today, so we leave
it undefined. Whatever the product is called, ask which part runs rules you wrote and which part
reads text.

**See also:** [AI decision making with probabilities and thresholds](ai-decision-making-with-probabilities.md),
[an open-source alternative to Microsoft-Decision-1](open-source-alternative-to-microsoft-decision-1.md)
and [combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## Sources

- OMG, [DMN overview](https://www.omg.org/dmn/) and the
  [Decision Model and Notation specification page](https://www.omg.org/spec/DMN), fetched
  2026-10-12.
- Camunda docs, [decision table](https://docs.camunda.io/docs/components/modeler/dmn/decision-table/)
  and [hit policy](https://docs.camunda.io/docs/components/modeler/dmn/decision-table-hit-policy/),
  fetched 2026-10-12.
- Microsoft Learn, [Deploy and use Microsoft-Decision-1 in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision),
  fetched 2026-10-12. We have not measured jevos against Microsoft-Decision-1.
- Our measurements, in the [jev README](https://github.com/feder-cr/jev): the jevos-v2 fraud score
  and choice confidence figures. The choice and score answers are README examples; the Snake
  question is from our game races. The decision table is illustrative.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships the model half of this page
and leaves the rules to whatever engine, or plain code, you already trust.*
