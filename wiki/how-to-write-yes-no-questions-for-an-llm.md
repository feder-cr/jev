---
title: "How to write yes/no questions an LLM answers well"
description: "Five rules for yes/no questions a small LLM answers well: one condition, the rule in the question, reading over computing, parallel wording, named subject."
parent: "Question design"
nav_order: 1
---

# How to write yes/no questions an LLM answers well

**A yes/no question works best when it asks one thing, names who or what it is about, carries
any rule it depends on, and can be answered by reading the text rather than by computing
something from it.** On 999 yes/no questions written after the model was finished, jevos was
right 0.954 of the time on facts stated in the text and 0.584 on questions that needed a sum.
Same model, same texts: the difference is what the question asked it to do. Sibling questions
should also be phrased the same way, so that their probabilities can be compared.

This matters more for a small model than for a large one. A large model can sometimes rescue a vague
question by guessing what you meant; a 1B model is far more likely to answer exactly the
question you wrote. That makes
question design the cheapest accuracy you can buy: no retraining, no bigger machine, only a
better string in `instructions`.

This page is the five rules, a request that follows them, and a map of the pages in this
section, each of which takes one rule or one kind of question further.

## What kind of question does a small model answer well?

Questions whose answer is written in the text, or can be read off it. On the 999-question set,
labelled by the kind of reasoning each question needs:

| The question needs | Accuracy |
|---|---|
| a fact stated in the text | 0.954 |
| the tone of the text | 0.938 |
| noticing the writer's intent | 0.859 |
| handling a negation | 0.858 |
| noticing the text does not say | 0.847 |
| applying a stated rule | 0.721 |
| comparing a number with a threshold | 0.654 |
| a sum or other arithmetic | 0.584 |

The top half is reading, the bottom half is computing. So the first design decision is not
wording at all: move every computation out of the question and into your code. "Is the order
total over 200 dollars?" is a question your code answers exactly from a field; "Does the
customer ask for a refund?" is one only a reader can answer. The measurement behind this, and
the lean toward yes that computing questions produce, are on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

Each kind in the top half has its own page: [questions about tone and emotion](yes-no-questions-about-tone.md),
[asking about the writer's intent](yes-no-questions-about-intent.md),
[negation in yes/no questions](negation-in-yes-no-questions.md), and
[asking whether the text says it at all](ask-whether-the-text-says-it.md), which is the gate
to put in front of any question the text might not answer.

## The five rules

1. **One condition per question.** "Is the customer upset and asking for a refund?" has two
   answers and returns one probability. Ask two questions and combine them in code, as
   explained in [one condition per question](one-condition-per-question.md) and, for the
   arithmetic of AND and OR on probabilities, in
   [combining yes/no answers](combining-yes-no-answers-and-or-not.md).
2. **The rule goes in the question.** The model knows nothing about your policy except what the
   request says. "Our policy refunds items reported missing within 30 days of delivery. Should
   this customer get a refund?" is answerable; "Is this eligible under policy R-12?" is a guess.
   On a yes/no question this server does not read Jev's optional `criteria` field, so the rule belongs in
   `instructions`. The long version is [put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).
3. **Reading, not computing.** Send "delivered: 5 days ago" rather than two dates and a
   question about their difference. How to shape the text for this is on
   [designing the state as JSON](designing-the-state-as-json.md).
4. **Name the subject.** "Is the customer upset?" beats "Is this upset?", and in a record with
   a customer and an agent, "Does the customer ask for..." beats "Is there a request for...".
   The model should never have to guess whose words the question is about.
5. **Parallel phrasing for sibling questions.** When several questions will be compared, give
   them the same shape: "Is this message mainly about X?" for every label. That is the basis of
   [questions for messages with several topics](mainly-about-questions-for-mixed-messages.md)
   and of [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).

## A request that follows them

```json
{
  "model": "jev-latest",
  "state": {
    "item": "wireless mouse",
    "delivered": "5 days ago",
    "customer_message": "The box arrived empty. This is the second time!"
  },
  "questions": {
    "refund": {"type": "noul", "instructions": "Our policy refunds items reported missing within 30 days of delivery. Should this customer get a refund?"},
    "upset": {"type": "noul", "instructions": "Is the customer upset?"},
    "wrong_item": {"type": "noul", "instructions": "Does the customer say they received the wrong item?"}
  }
}
```

This is the README's example, and it shows four of the rules at once: the rule is inside
`refund`, the delivery is already a duration, each question asks one thing, and each names the
customer. The README's run answers 0.93, 0.83 and 0.04. The state is read once for all three
questions, so asking three small questions instead of one compound one costs about 66 ms
against 49 ms for a single question on the reference laptop.

## How do I know a phrasing is good?

You test it. Two phrasings that mean the same thing to you can produce different probabilities,
and the only way to know which one is stable is to run a few candidates on cases whose answer
you know. The method, three phrasings on a small labelled set, is on
[why wording changes the answer](why-wording-changes-the-answer.md), and building that set is
covered in [building a yes/no test set for your own data](building-a-yes-no-test-set.md).

## Where question design stops helping

Some limits are not about wording:

- **Length.** The text plus each question must fit in 8,192 tokens, and cost grows with every token. For
  contracts and long threads, see [yes/no questions about long documents](yes-no-questions-about-long-documents.md).
- **Language.** jevos reads English only. The options for other languages are on
  [using an English-only LLM with other languages](using-an-english-only-model-with-other-languages.md).
- **Rules the model has never seen.** Even a well written rule question is the harder case: on
  2,000 questions from three unseen business policies, jevos was right 0.810 of the time. Put a
  review band around decisions that cost money.

## Short answers to the questions that lead here

**How do I write a good prompt for a yes/no classifier?** Ask one condition, name the subject,
put any rule in the question, and leave numbers and dates to code.

**Should I ask one big question or several small ones?** Several small ones. They share one
reading of the text, so each extra question costs a fraction of the first, and when a decision
fails you can see which part failed.

**Where do I put the policy text?** In `instructions`, in front of the question. On a yes/no
question jevos does not read the `criteria` field.

**Why does the model get dates wrong?** Dates and durations are computation. It scored 0.598
on them on our 999-question set. Compute the duration in code and send it as text.

**Do I need examples in the question?** Not as a rule. A clear condition and a named subject
do more than examples, and every example costs tokens on every request.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md)
and [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Sources

- Accuracy by kind of question: our 999-question test set, written after the model was
  finished, run on `jevos-q4_k_m`.
- The refund request, its answers, and the 66 ms against 49 ms timing: the
  [jev README](https://github.com/feder-cr/jev), reference laptop with an Intel Core Ultra 7
  255H, 16 threads.
- The 0.810 on 2,000 policy questions: the jev README.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model whose
accuracy on the same set of texts ran from 0.584 to 0.954 depending on what the question asked
it to do.*
