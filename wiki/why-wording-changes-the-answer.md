---
title: "Why wording changes an LLM's answer, and how to test it"
description: "Two phrasings of the same yes/no question can get different probabilities. Why that happens, and a small test to pick the phrasing that stays stable."
parent: "Question design"
nav_order: 7
---

# Why wording changes an LLM's answer, and how to test it

**A language model answers the words you send, not the meaning you intended, so two phrasings
that mean the same thing to you can get different probabilities.** The practical fix is a
small test: write three phrasings of the question, run them on 30 to 50 cases whose answer you
know, and keep the phrasing that is right most often and moves least between similar cases.
It takes an afternoon and replaces a guess with a measurement.

Wording sensitivity is not a flaw of small models only. Sclar and colleagues measured
differences of up to 76 accuracy points on one 13B model from formatting changes alone, and
found the sensitivity did not go away with larger models, more examples or instruction tuning.
If formatting moves a large model that much, the choice of words in a yes/no question
deserves a test on any model.

This page is where the sensitivity comes from, which changes tend to matter, the test itself,
and how to read its results. It contains no measurement of jevos on paraphrased questions,
because we have not run one; it tells you how to run yours.

## Where does the sensitivity come from?

A question is not a query into a database. The model reads it together with the text and
produces a probability from both, and every word shifts that reading a little. Most shifts
are small. Some are not, and they tend to come from a few sources:

- **Which words overlap with the text.** "Does the customer mention a refund?" and "Does the
  customer ask for their money back?" point at different words. If the message says "I want my
  money back", the second question lines up with it more directly.
- **How strict the verb is.** "Mention", "ask for", "demand" and "suggest" set different bars.
  The model will apply whichever bar you wrote, and you may have meant another.
- **Who the subject is.** "Is this rude?" leaves open whether you mean the customer, the agent,
  or the situation.
- **Hidden extra conditions.** "Is the customer clearly upset?" adds "clearly", which is a
  second condition about strength.

None of this is special to machines. A person given these questions would also answer them
differently. The difference is that a person asks what you meant, and a model does not.

## The three-phrasing test

**1. Collect labelled cases.** 30 to 50 real texts, with the answer to your question decided by
a person who knows what the question is for. Aim for roughly as many yes as no, and include the
hard ones: short messages, sarcasm, messages about two things. How to build a set that tells you
something is on [building a yes/no test set for your own data](building-a-yes-no-test-set.md).

**2. Write three phrasings.** Vary one thing at a time where you can: the verb, the subject, the
presence of a qualifier. For example:

```json
"questions": {
  "a": {"type": "noul", "instructions": "Does the customer ask for a refund?"},
  "b": {"type": "noul", "instructions": "Does the customer ask to get their money back?"},
  "c": {"type": "noul", "instructions": "Is the customer requesting a refund for this order?"}
}
```

All three can go in one request. They share the reading of the text, so testing three
phrasings costs far less than three separate runs.

**3. Score each phrasing.** For every phrasing, record accuracy at your threshold and the
probability on each case. Keep the numbers per case, not only the average.

```python
# probs[i][name]: the noul for phrasing `name` on case i; labels[i]: True or False
for name in ["a", "b", "c"]:
    right = sum((probs[i][name] > 0.5) == labels[i] for i in range(len(labels)))
    print(name, right / len(labels))
```

## How do I read the results?

Look at three things, in this order:

1. **Accuracy.** The obvious one. With 40 cases, one case is 2.5 points, so do not pick a
   winner on a one-case difference.
2. **Agreement between phrasings.** Cases where all three agree are cases the model reads the
   same way whatever you write; they are safe. Cases where they disagree are where your wording
   decides the answer. Read those texts: they usually show which phrasing matches what you
   meant.
3. **Margin.** A phrasing whose correct answers sit at 0.9 and 0.1 is more robust than one
   whose correct answers sit at 0.6 and 0.4, even at the same accuracy. Small wording changes
   later, or new kinds of text, will flip the second one first.

If one phrasing wins on all three, use it. If they are all similar, pick the plainest one, since
it is the one colleagues will not "improve" by accident later.

## Which rewrites usually help?

Before testing, apply the rules that remove the common causes: one condition per question,
the subject named, the rule written in, and computation moved to code. They are collected on
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).
Two more are specific to wording:

- **Use the words the texts use.** If customers write "money back", a question with "money back"
  reads more directly than one with "reimbursement".
- **Drop qualifiers you would not act on.** "Clearly", "really", "strongly" raise the bar in a
  way you cannot see. If you need levels of strength, ask them as boundaries, as on
  [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).

## Keep the test

The labelled set and the three phrasings are worth keeping. When you change the question later,
or move to a new model file, rerun them. That turns the set into a regression test, which is the
subject of [LLM regression tests in CI with yes/no checks](llm-regression-tests-in-ci.md).

Being straight about the limit: a 40-case test tells you which phrasing is better on those 40
cases. It will not tell you the accuracy you will see in production to two decimals. Use it to
choose, not to report.

## Short answers to the questions that lead here

**Why does rephrasing a prompt change the answer?** Every word shifts how the model reads the
question against the text. Verbs, subjects and qualifiers change the bar the answer has to
meet.

**How sensitive are LLMs to prompt wording?** One study measured up to 76 accuracy points of
difference from formatting alone on a 13B model. We have not measured jevos on paraphrases.

**How many phrasings should I test?** Three is enough to see whether the answer depends on
wording. More rarely changes the choice.

**How many labelled cases do I need?** 30 to 50 to choose between phrasings. More if the
decision is costly or the texts vary a lot.

**Should I average the three phrasings instead of picking one?** It can smooth the answer, but
it triples the questions per request. Pick one unless the phrasings disagree often and you
cannot tell which is right.

**See also:** [accuracy by kind of question](accuracy-by-kind-of-question.md),
[negation in yes/no questions](negation-in-yes-no-questions.md) and
[LLM judge bias and how to control it](llm-judge-bias.md).

## Sources

- Melanie Sclar, Yejin Choi, Yulia Tsvetkov, Alane Suhr, "Quantifying Language Models'
  Sensitivity to Spurious Features in Prompt Design", 2023,
  [arXiv:2310.11324](https://arxiv.org/abs/2310.11324), fetched 2026-09-29.
- No jevos measurement is quoted on this page. The test described is a method, not a result.

---

*From the notes of [jev](https://github.com/feder-cr/jev). We have not measured jevos on
paraphrased questions, so this page gives you the test instead of a number.*
