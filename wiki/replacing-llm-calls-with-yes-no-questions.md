---
title: "Replacing chat LLM calls with yes/no questions"
description: "Audit an app for chat prompts that are really decisions, such as answer yes or no or classify as, and rewrite each as yes/no questions to a local model."
parent: "Agents and routing"
nav_order: 9
---

# Replacing chat LLM calls with yes/no questions

**Many chat-model calls in a codebase are decisions dressed as conversations: the prompt ends
with "Answer yes or no", "Classify this as one of", or "Return true or false", and the code
parses one word out of the reply.** Each of those can be rewritten as one or more yes/no
questions to a local model that returns P(yes) directly, with no text to parse and no output
tokens. The work is in three steps: find those prompts, rewrite them, and check the new answers
against the old ones on real cases before switching.

The rewrite usually improves the decision as well as its cost. A prompt that asks a chat model
to pick one of six labels hides which label it nearly picked; six yes/no questions show all six
probabilities, and code applies the rule.

This page is how to find the candidate calls, a before and after, how to split a multi-label
prompt, what to move and what to leave, and how to switch without guessing.

## How do I find the prompts that are really decisions?

Search the codebase for the phrases that give a decision away. A first pass:

- "answer yes or no", "respond with yes or no", "only yes or no"
- "classify", "categorize", "which category", "one of the following"
- "true or false", "return true", "is_" or "has_" fields filled from a model reply
- "respond with only", "output a single word", "reply with the label"
- code that lowercases a reply and compares it with `"yes"`, or parses a label with a regex

Then look at what the code does with the reply. If the next line is an `if`, the call is a
decision. If the reply is shown to a user or stored as text, it is a generation and stays where
it is.

A useful second pass is by cost: sort the decision calls by how often they run. The one inside
a loop over every message or every retrieved passage is worth more than ten that run once a day.
The cost side is on [reducing LLM cost with local yes/no decisions](reducing-llm-cost-with-yes-no-decisions.md).

## Before and after

A typical decision prompt to a chat model:

```text
You are a support assistant. Read the customer message below and answer with
only "yes" or "no": is this a billing problem?

Message: I was charged twice for the same order.
```

The code around it strips the reply, lowercases it, and hopes it is exactly "yes" or "no" and
not "Yes." or a sentence.

The same decision as a yes/no request:

```json
{
  "model": "jev-latest",
  "state": "I was charged twice for the same order.",
  "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}}
}
```

The README's answer to this request is `"noul": 0.9`, with 27 input tokens and 0 output tokens.
Four things changed. The role line is gone, because the model is not playing a part. The format
instruction is gone, because there is no format. The message moved into `state`. And the answer
is a probability, so the threshold is a line of your code instead of a word the model chose.
The request itself is walked through on
[ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md).

## Splitting a "classify as one of" prompt

jevos answers only yes/no questions; a `choice` question is refused with a 422. A multi-label
prompt becomes one question per label, all in the same request so the text is read once:

```json
{
  "model": "jev-latest",
  "state": "Hi, the app logs me out every time I open settings, and I was billed twice this month.",
  "questions": {
    "billing":   {"type": "noul", "instructions": "Does the customer report a billing or payment problem?"},
    "bug":       {"type": "noul", "instructions": "Does the customer report something in the app not working?"},
    "account":   {"type": "noul", "instructions": "Does the customer ask to change or close their account?"},
    "cancel":    {"type": "noul", "instructions": "Does the customer ask to cancel their subscription?"}
  }
}
```

Code then takes the highest label, or every label above a threshold when a message can have
several, or "other" when none clears it. That message is both a billing problem and a bug, which
a single-label prompt would have had to hide. The full method, with the pitfalls of picking a
label from independent probabilities, is on
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).

If the old prompt carried a rule ("classify as refundable if the item was reported within 30
days"), move the rule into the question, and move the 30-day arithmetic into code. The pattern
is on [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

## What to move, and what to leave

| The old prompt asks for | Move it? |
|---|---|
| yes or no about something stated in the text | yes |
| a label from a fixed list | yes, one question per label |
| a score from 1 to 5 | as boundary questions ("is it at least 4?"), see [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md) |
| yes or no that needs a sum or a date | compute in code first, then ask what is left |
| a reason or explanation | no, that is generated text |
| fields extracted into JSON | no, use structured output; see [structured output vs a probability](structured-output-vs-a-probability.md) |
| a decision about non-English text | no, jevos reads English only |

## Switching without guessing

1. **Collect real cases.** Take a few hundred inputs the old call has seen, and label the correct
   answer by hand for at least a hundred of them. The old model's answer is not the label.
2. **Run both.** Record the old call's parsed answer and the new P(yes) on the same inputs.
3. **Compare on the labelled cases,** per question, and look at disagreements one by one. Some
   will be the new model's mistakes; some will be the old one's.
4. **Pick the threshold** on the labelled cases, not at 0.5 by habit.
5. **Shadow in production.** Call both for a while, act on the old one, log both, and switch when
   the logs agree with your test.

Be straight with yourself about the result. On our own set of 999 questions written after
training, jevos was right 0.954 of the time on stated facts and 0.584 on arithmetic. Decisions
that are reading will usually move well; decisions that were quietly doing maths will not, and
the comparison is how you find out which is which.

## Short answers to the questions that lead here

**How do I know if an LLM call can be replaced?** If the reply is parsed into a yes, a no or a
label and then used in an `if`, it is a decision and a candidate.

**Do I need to keep the system prompt?** No role or format instructions are needed. The rule, if
there is one, goes into the question.

**What about "classify as one of" prompts?** One yes/no question per label in one request, and
the choice made in code.

**What about scores?** Rewrite them as threshold questions, one per boundary.

**Will the new answers match the old ones?** Not exactly. Compare both against hand labels, not
against each other.

**See also:** [an LLM router with yes/no questions](llm-router-with-yes-no-questions.md),
[one condition per question](one-condition-per-question.md) and
[a Python client for local LLM decisions](python-client-for-local-llm-decisions.md).

## Sources

- The billing request and its answer (0.9, 27 input tokens, 0 output tokens), the 422 on
  `choice` questions and the English-only limit: the [jev README](https://github.com/feder-cr/jev).
- Accuracy by kind of question: our 999-question test set on `jevos-q4_k_m`.
- No outside sources are used on this page.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The billing request in its README is what a prompt ending in "answer yes or no"
looks like once the role, the format and the parsing are taken out.*
