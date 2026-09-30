---
title: "Small LLMs and arithmetic in yes/no questions"
description: "A 1B LLM answers 0.95 of reading questions right and 0.58 of questions that need a sum. Measured on two test sets, and how to design around it."
parent: "Measurements"
nav_order: 2
---

# Small LLMs and arithmetic in yes/no questions

**A small language model that answers in one pass is good at reading a text and poor at
computing from it.** On 999 yes/no questions written after training, jevos answered 0.954 of
the questions about a fact stated in the text correctly, and 0.584 of the 221 questions that
needed a sum, a difference or a product. Questions that compare a number with a threshold
(0.654) and questions about dates and durations (0.598) sit in between, closer to the bottom.

A second test, built so that every answer is computed by code, reproduces the same shape. So
this is a property of the model, not of one set of questions, and the practical conclusion is
the same either way: do not ask the model to calculate.

This page is both measurements, why a one-pass model struggles with a sum, and how to phrase
questions and split work so the weakness never reaches your results.

## Measured on 999 new questions

Each question in the set is labelled with the reasoning it needs. Grouped from easiest to
hardest:

| Kind | Example of the shape | Questions | Accuracy |
|---|---|---|---|
| stated fact | "Does the customer mention the order number?" | 108 | 0.954 |
| tone | "Is the reviewer angry?" | 32 | 0.938 |
| paraphrase | "Does the sender say the product broke?" | 84 | 0.893 |
| intent | "Does the customer want to cancel?" | 71 | 0.859 |
| negation | "Did the customer not receive a confirmation?" | 106 | 0.858 |
| not stated | "Does the text say which courier was used?" | 98 | 0.847 |
| rule | "Under a 30-day policy, is this return eligible?" | 104 | 0.721 |
| number vs threshold | "Is the order total over 100 euros?" | 78 | 0.654 |
| dates and durations | "Did it arrive within 5 working days?" | 97 | 0.598 |
| arithmetic | "Do the two items cost more than 110 euros together?" | 221 | 0.584 |

The examples in the second column are ours, written for this page to show the shape; the test
questions themselves stay unpublished so the set remains a clean test.

The line is sharp. Everything that can be answered by finding and understanding words is above
0.84. Everything that needs an operation on numbers is below 0.73, and arithmetic, the largest
group, is close to a coin toss.

It is also where the model's lean toward yes comes from: on arithmetic questions whose answer is
no, the average P(yes) is 0.59, as measured on [why a small LLM says yes](why-a-small-llm-says-yes.md).

## Measured again, with answers computed by code

A hand-written test can be wrong in its own way, so we built a second one where no person
decides the answer: 1,000 yes/no questions generated from templates over orders, leave requests,
servers, loans, courses, shipments, rentals, prescriptions and bookings, with every answer
computed by code from the numbers in the text.

| Kind | Accuracy |
|---|---|
| stated fact | 0.98 |
| not stated | 1.00 |
| number vs threshold | 0.85 |
| rule | 0.62 |
| dates and durations | 0.61 |
| arithmetic | 0.56 |
| all | 0.67 |

Arithmetic at 0.56 against 0.58 on the hand-written set, dates at 0.61 against 0.60: the two
tests agree on the weakness. They disagree on thresholds (0.85 here, 0.65 there), most likely
because a template states its numbers cleanly and a hand-written email buries them in prose. That also makes the generated set a cheap stand-in for the
expensive one, since it can be regenerated at any size without anyone writing a question.
How to build one for your own data is on [generating test questions with code](generating-test-questions-with-code.md).

## Why one pass cannot carry a sum

jevos reads the text and the question and produces one number, without writing anything out.
A person checking "do 89.90 and 25.00 come to more than 110?" does the addition first and then
compares. A model that answers in a single pass has to do both inside one computation, with no
place to hold the intermediate total.

Large models asked to reason step by step get around this by writing the steps as text and
reading them back. That is exactly the generation jevos does not do, and it is the reason it
answers in 25 to 110 ms on a CPU instead of seconds. The trade is deliberate, and it means the
arithmetic has to happen somewhere else. The same reading-versus-computing split is the thread
of [small language models explained](small-language-models-explained.md).

## How to keep arithmetic out of the model

**Compare in code, ask the model about the words.** In most applications the numbers already
exist as fields: the order total, the delivery date, the number of failed logins. Compare them
in code, where the answer is exact, and ask the model only what code cannot read:

```json
"questions": {
  "claims_missing": {"type": "noul", "instructions": "Does the customer say an item was missing?"},
  "asks_refund":    {"type": "noul", "instructions": "Does the customer ask for their money back?"}
}
```

plus `delivered_days_ago <= 30` in your own code.

**When the numbers are only in the text**, get them out with ordinary tools first: a date
parser, a currency regex, a field in a form. jevos answers yes/no questions and does not return
values, so extraction is a separate step, not a question for it.

**When you must ask a numeric question**, give the model the computed quantity, not the inputs.
"The delivery took 9 working days. Is that within the 5-day promise?" is a comparison with the
number stated, which is easier than working the number out from two dates, and still sits in the
0.65 to 0.85 range rather than at 0.95. Put a person on the middle band.

**Rephrase as reading where the meaning allows.** "Does the customer say the delivery was
late?" asks what the text claims, not what the calendar says, and it is a question the model
answers well. Whether the two are the same question depends on your use.

## Short answers to the questions that lead here

**Can a small LLM do arithmetic?** Not reliably in one pass. jevos is right on 0.584 of our
arithmetic yes/no questions against 0.954 on stated facts.

**Why is an LLM bad at maths?** A model that answers without writing intermediate steps has
nowhere to hold a partial result. Larger models asked to reason step by step compensate by
generating text, which is slow.

**Are dates also a problem?** Yes, 0.598 on our set: a date question is usually a subtraction in
disguise.

**How do I test this on my own model?** Generate questions from templates with the answer
computed by code, and compare accuracy by kind. Our generated set reproduced the hand-written
arithmetic and date results within two points.

**What should I do instead?** Compare numbers in code and ask the model only about what the text
says.

**See also:** [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md),
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md)
and [zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).

## Sources

- Our 999-question test set, written after training and never used for tuning, run on
  `jevos-q4_k_m`; per-kind accuracies recomputed from the per-question results for this page.
- Our generated 1,000-question set with answers computed by code, run on the released jevos.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The second test exists because we did not trust the first one enough, which is the
habit we would recommend.*
