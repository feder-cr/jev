---
title: "What is a decision model in AI?"
description: "A decision model reads a text and a typed question and returns a probability per allowed answer. How it differs from a chat LLM, a classifier and rules."
parent: "Guides"
nav_order: 5
---

# What is a decision model in AI?

**A decision model is a model that reads a text and a question with a fixed set of allowed
answers, and returns a probability for each allowed answer in one pass instead of writing a
reply.** The answers are typed: a yes/no question gets P(yes), a multiple-choice question gets a
probability per option, and a score question gets a probability per level of a scale. Your code
then acts on the numbers, usually by comparing them with a threshold. TypeSafe's Jev,
Microsoft-Decision-1 and jevos are three examples: the first two are hosted, jevos runs on your
own CPU.

The non-obvious part is where the decision ends up. A chat model hands back a sentence to parse
and trust; a decision model hands back a number, and the rule that turns it into an action lives
in your code, where it can be tested, logged and changed without touching the model. Microsoft's
developer post says these models make "quick, focused decisions" and "are sometimes described
as" System One models.

This page is what goes in and comes out, three models that work this way, why the output is a
probability, and how a decision model differs from a chat LLM, a classifier trained for one task
and a rules engine.

## What goes into a decision model, and what comes out?

A `state` goes in (the text to decide about, a string or any JSON), with named questions, each
with a type and its allowed answers. One answer per question comes back under the same name, and
no text is generated (jevos reports `output_tokens` 0). The multiple-choice example from the
jevos README:

```json
{"model": "jev-latest",
 "state": {"item": "wireless mouse", "customer_message": "The box arrived empty. This is the second time!"},
 "questions": {"team": {"type": "choice",
   "instructions": "Which team should handle this message?",
   "criteria": {"billing": "payments, invoices, refunds",
                "shipping": "deliveries, missing or damaged parcels",
                "tech": "a product that does not work"}}}}
```

jevos-v4 answered `shipping`, with probabilities 0.02, 0.93 and 0.05 and a `confidence` of 0.89.
The three question types, in this wire format's names:

| type | asks | gets back |
|---|---|---|
| `noul` | is this true? | P(yes), from 0 to 1 |
| `choice` | which of these options? | the most probable option, a probability per option, a confidence |
| `score` | how much, on this scale? | the expected level, a probability per level, a confidence |

The allowed answers are the point. A decision model cannot reply "it depends" or invent a fourth
team; it can only spread probability over the answers you allowed.

## Which models are decision models?

- **Jev**, by TypeSafe AI, is hosted. jevos speaks its wire format, so code written for Jev's
  SDK works unchanged against jevos for yes/no questions.
- **Microsoft-Decision-1**, announced on 2026-10-09, runs in Microsoft Foundry and through
  OpenRouter. Microsoft puts the category this way: "Unlike LLMs, which are designed to generate
  text or reason through complex problems, decision models are purpose-built to deliver
  structured outputs that software can immediately act on." Its documentation uses the same
  three question types.
- **jevos** is open source (MIT): one native binary, CPU only, about 1 GB of memory, English
  text, 8,192 tokens of context.

A shared interface does not mean equal answers: on the six tasks in our README, Jev scored higher
than jevos-v4 on all six. What a hosted option means next to a local one is on
[an open-source alternative to Microsoft-Decision-1](open-source-alternative-to-microsoft-decision-1.md).

## Why return probabilities instead of an answer?

Because the right cut-off depends on what a mistake costs, and only the application knows that.
One model can serve a cautious gate and a permissive one: for example, a refund bot can require
P(yes) above 0.9 to act alone, while a spam flag goes up at 0.5. A middle band can go to a person
([human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md)), and
[how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md) picks the numbers
from labelled examples. Microsoft's documentation agrees: "Choose a probability threshold based
on your workload, and validate it against labeled examples before you automate a gate."

Choice and score answers add a `confidence`. In the jevos README's score example, "How angry is
the customer?" on four levels (calm, annoyed, angry, furious) gets a score of 1.25 and a
confidence of 0.0: the model cannot place the message, and the README says to route such answers
to a person. A confidence is worth something only if it tracks being right: with jevos-v2, at
confidence 0.75 or more, 95% of choice answers were right, on 46% of the questions; below 0.25,
47%. More on [AI decision making with probabilities and thresholds](ai-decision-making-with-probabilities.md).

## How is it different from a chat LLM?

A chat LLM writes; a decision model scores. Generating means producing tokens one after another,
then parsing what came out, which may be a label, a hedge or a paragraph. A decision model reads
the text and the questions and returns numbers, so the time goes into reading the input
([why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md)) and
there is nothing to parse. Asking a chat model for a JSON label fixes the shape but still gives a
word instead of a probability ([structured output vs a probability](structured-output-vs-a-probability.md)).

Being straight about the limit: a decision model does not explain itself, summarize or write.
Microsoft's documentation says to use a generative model "when the application needs to create,
summarize, rewrite, or explain content". The two combine: the decision model routes or gates,
the generative one writes.

## How is it different from a classifier trained for one task?

A classic text classifier learns a fixed set of labels from labelled examples of one task; new
labels mean new examples and a new model. A decision model takes the question and options at
request time, so a new label is a new line in `criteria`, the approach on
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).
The trade reverses when a task has thousands of labelled examples and never changes: a classifier
trained on exactly that data can be the better tool, as argued on
[a yes/no LLM vs a fine-tuned BERT classifier](yes-no-llm-vs-fine-tuned-bert.md).

## How is it different from a rules engine?

A rules engine executes logic you wrote: if the amount is over 500 and the account is new, hold
the payment. It is exact, cheap and auditable, and it cannot read "The box arrived empty. This is
the second time!" and tell you the customer is upset. A decision model reads language and is
never exact. They work best together: code computes what can be computed, the model is asked
only what needs reading. The jevos README is explicit: on points that add up (a fraud score from
six rules, measured with jevos-v2) the model was right 34% of the time, barely above the most
common level, and confidently wrong, so compute sums in code and ask the parts as yes/no
questions. [A yes/no LLM vs a business rules engine](yes-no-llm-vs-business-rules-engine.md) and
[decision engine vs decision model](decision-engine-vs-decision-model.md) go further.

## Short answers to the questions that lead here

**What is a decision model?** A model that returns a probability for each allowed answer to a
typed question about a text, in one pass, without generating text. Your code applies the
threshold and takes the action.

**What is the difference between a decision model and an LLM?** A chat LLM generates text that
has to be parsed; a decision model scores a fixed set of answers. Use the first to write, the
second to gate, route and grade.

**What are examples of decision models?** TypeSafe's Jev and Microsoft-Decision-1, both hosted,
and jevos, which is open source and runs on a CPU.

**Can a decision model run locally?** jevos does: one binary on a CPU, about 1 GB of memory,
listening on 127.0.0.1:8017. The hosted ones are reached over the network.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[what P(yes) means, and what it does not](what-p-yes-means.md) and
[an LLM router with yes/no questions](llm-router-with-yes-no-questions.md).

## Sources

- jevos facts, examples and figures, including the jevos-v2 ones and the six-task comparison
  with Jev: the [jev README](https://github.com/feder-cr/jev), our own measurements.
- Microsoft's definition of decision models and the announcement date:
  [Introducing Microsoft-Decision-1](https://commandline.microsoft.com/microsoft-decision-1-model-foundry/),
  Command Line blog, dated 2026-10-09, fetched 2026-10-12.
- Question types and the advice quoted:
  [Deploy and use Microsoft-Decision-1 in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision),
  Microsoft Learn, fetched 2026-10-12.
- "Quick, focused decisions" and "System One":
  [Not Every Decision Needs an LLM](https://techcommunity.microsoft.com/blog/educatordeveloperblog/not-every-decision-needs-an-llm-getting-started-with-microsoft-decision-1/4563468),
  Microsoft Tech Community, fetched 2026-10-12.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a decision model that answers with
probabilities and leaves the deciding to your code.*
