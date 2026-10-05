---
title: "Building a yes/no test set for your own data"
description: "How to build a yes/no test set from your own cases: real inputs, balanced answers, a tag per kind of question, careful labels, and never tuning on it."
parent: "Evaluation"
nav_order: 9
---

# Building a yes/no test set for your own data

**A useful yes/no test set is about a hundred real cases from your own application, each with a
question, a right answer decided by a person, and a tag for the kind of reasoning the question
needs, with the yeses and noes roughly balanced and the set never used to tune anything.** That
is enough to tell you, before you rely on a model, which of your questions it answers well,
which way it fails, and where to set your thresholds. It is small enough to build in an afternoon
with two people.

Published benchmarks cannot do this job. They are not your texts, not your questions, and often
not clean; the reasons are on
[benchmark contamination and truly held-out tests](benchmark-contamination-and-held-out-tests.md).
Even a split of your own data can mislead if it was produced the same way as whatever the model
or prompt was tuned on: on the first jevos, that gap was about ten points, as measured on
[our held-out benchmark said 0.855, new questions said 0.757](held-out-benchmark-too-optimistic.md).

This page is where the cases come from, the format of one case, balance, labelling, tags, the
rule that keeps the set honest, and how far a hundred cases go.

## Where should the cases come from?

From the inputs your system will actually see. Pull a random sample from logs, tickets, emails or
records, not the ones you remember, because the ones you remember are the unusual ones. Then add
a small number of deliberate hard cases on top:

- inputs where the answer turns on a negation ("I did not receive a confirmation")
- inputs that do not contain the information the question asks about
- inputs with numbers or dates that the question depends on
- inputs that mix two topics

Keep the random sample and the hard cases tagged separately. The random sample tells you what
production will look like; the hard cases tell you where it breaks.

Strip personal data before the cases go anywhere shared. The model can be local, but a test set
tends to end up in repositories and tickets.

## What does one case look like?

One record per question, with the state stored once per text:

```json
{"id": "t042-q3", "state": {"customer_message": "The box arrived empty. This is the second time!"}, "question": "Does the customer say an item was missing?", "answer": "yes", "kind": "paraphrase", "source": "random", "note": "empty box counts as missing"}
```

The `note` field matters more than it looks. When two people disagree about a label later, the
note says what the first one decided and why. Several questions about the same text are normal and
cheap to run, since a local model reads the state once for all of them.

## How many yes and how many no?

Two sets, if you can afford them:

- **A balanced set**, about half yes and half no. It measures error direction fairly: if the model
  makes many more wrong yeses than wrong noes on a balanced set, it leans toward yes. Our own
  999 hand-written questions are exactly half yes for this reason, and it is how we found the lean described
  on [why a small LLM says yes](why-a-small-llm-says-yes.md).
- **A set with your real mix.** If only 3% of your tickets are fraud, precision on the real mix
  will be far worse than on a balanced set, because the rare yeses are outnumbered by false alarms.
  The effect is explained on [base rates](base-rates-and-yes-no-predictions.md).

If you only build one, build the balanced one, and compute the real-mix precision from its per
class error rates and your known base rate.

## Who decides the right answer?

A person who knows the domain, following written rules. Before labelling, write down for each
question what counts as yes: does "I might cancel" count as intent to cancel? Does an empty box
count as a missing item? Most label disagreements are really disagreements about the question.

Then:

1. **Have two people label independently**, at least for a first batch of 30 to 50 cases.
2. **Look at every disagreement.** Either one person made a mistake, or the question is ambiguous.
   Fix the question, not only the label.
3. **Allow "cannot tell".** Cases that a careful person cannot answer from the text do not belong in
   a yes/no test. Drop them, or rewrite the question as "Does the text say...?".

Where the answer is a fact your code can compute (is the total over 100, was it more than 30
days), let code decide it. It does not make mistakes, and those questions can be generated in
bulk, as described on
[generating test questions with answers computed by code](generating-test-questions-with-code.md).

## Tag every case with its kind

A kind tag is the reasoning the question needs: stated fact, paraphrase, tone, intent, negation,
not stated, rule, number against a threshold, date, arithmetic. It costs a few seconds per case,
and it turns one accuracy figure into a map of what to trust. On our own set the kinds ranged, on the first jevos, from
0.954 to 0.584 (per-kind numbers for jevos-v4 are not published). The tags, and how to assign them when a question needs two kinds of reasoning, are
on [accuracy by kind of question](accuracy-by-kind-of-question.md).

## Keep it clean: never tune on it

The rule is simple and easy to break: the test set is for reporting, not for choosing. The moment
you pick a threshold, a prompt wording or a model by looking at its score on the set, the set has
become a development set, and its score is optimistic.

In practice:

- Split what you collect into a **development set** you are allowed to look at and a **test set**
  you run only to report.
- Choose thresholds and phrasings on the development set.
- Run the test set when a decision has been made, not to make it.
- When you have run it many times while iterating, retire it and build a fresh one. The effect of
  choosing on the test set is measurable: on our 999 questions with the first jevos, picking the best bias by looking at
  the test answers themselves reached 0.763, against 0.759 with a bias fitted properly on other
  data. The gain was small in our case, but all of it came from looking at the answers, and with
  a smaller set and more choices to make it grows.

## Is a hundred cases enough?

To start, yes. A hundred cases gives an accuracy with a rough range of plus or minus 8 points. That
is enough to see whether a model is far off, to find the kinds of question it fails on, and to
choose a first threshold. It is not enough to tell two prompts apart by 3 points, or to trust a
kind that has only 10 cases in it. Grow the set where decisions depend on it, usually on the
kinds near your threshold. The arithmetic behind the ranges is on
[evaluation metrics for yes/no classifiers](evaluation-metrics-for-yes-no-classifiers.md).

## Short answers to the questions that lead here

**How do I build a test set for an LLM?** Sample real inputs, write the questions you will ask in
production, have people label the answers under written rules, tag each question by kind, and keep
the set away from any tuning.

**How big should a test set be?** A hundred cases is enough to start and gives about plus or minus
8 points on accuracy. Grow it for the kinds of question that matter most.

**Should the test set be balanced?** For measuring which way a model fails, yes. For estimating
precision in production, also keep or compute a version with your real mix.

**Can I use my test set to choose a threshold?** No. Choose on a separate development set, or the
test score becomes optimistic.

**What if people disagree on a label?** Usually the question is ambiguous. Rewrite it, or drop cases
that a careful reader cannot answer from the text.

**See also:** [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md),
[LLM regression tests in CI with yes/no checks](llm-regression-tests-in-ci.md) and
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## Sources

- The balanced 999-question set, its accuracy range by kind, and the recalibration results
  (0.759 fitted on development data, 0.763 chosen on the test set): our measurements on
  the first jevos.
- The plus or minus 8 points for 100 cases is the normal approximation for a proportion at 0.8,
  not a measurement.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose own test questions stay
unpublished so they can go on being a test.*
