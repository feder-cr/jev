---
title: "Generating test questions with answers computed by code"
description: "Build yes/no test questions from templates with answers computed by code: no labelling errors, any size, reproducible, and the biases to watch for."
parent: "Evaluation"
nav_order: 11
---

# Generating test questions with answers computed by code

**A generated test set is a small program that writes texts from templates, asks yes/no
questions about them, and computes each right answer from the same values it put in the text.**
Because code decides the answer, there are no labelling mistakes, the set can be regenerated at
any size with a fixed seed, and every question kind can have as many cases as you need. The price
is a style of its own: templated texts are cleaner than real ones, so a generated set is a
complement to a hand-labelled set of real cases, not a replacement.

It is most valuable exactly where hand labelling is weakest: questions with numbers, dates and
rules, where a tired labeller adds wrong, and where you need hundreds of cases per kind before
the per-kind accuracy means anything.

This page is what a generator is good for, a minimal generator in Python, how to control balance,
boundaries and phrasing, how to keep it reproducible, and the biases a generated set brings with
it.

## What does code-computed labelling buy you?

- **Correct answers.** "Do the three items cost more than 110 euros together?" has one answer, and
  the generator knows it because it chose the prices.
- **Size on demand.** A kind with 30 hand-written questions has a range of about plus or minus 8
  points. A generator gives you 500 of that kind in a second.
- **Control.** You decide how many cases sit near the threshold, how many are far from it, and
  how the yeses and noes are balanced.
- **Regeneration.** When a test set has been looked at too often while tuning, a new seed gives a
  fresh one of the same shape.

It suits question kinds whose answer follows from structured values: number against a threshold,
arithmetic, dates and durations, rules with explicit conditions, and "is it stated" questions
where the generator decides which fields to include. It does not suit tone, intent or anything
where a person's judgement is the definition of the right answer.

## A minimal generator

This sketch writes request files in the documented `POST /v1/systemone` body, plus an expectation
file per case in the layout used on
[LLM regression tests in CI](llm-regression-tests-in-ci.md). It is written for this page, not a
tested tool.

```python
import json, pathlib, random

rng = random.Random(7)                      # fixed seed: same set every run
TEMPLATES = [
    "Is the order total over {t} euros?",
    "Does the order cost more than {t} euros in total?",
    "Taken together, do the items come to more than {t} euros?",
]

def make_case(i):
    prices = [round(rng.uniform(5, 80), 2) for _ in range(rng.randint(2, 4))]
    total = sum(prices)
    gap = rng.choice([1, 2, 5, 15])         # near and far from the threshold
    t = int(total) - gap if i % 2 == 0 else int(total) + gap
    state = {"items": [{"name": f"item {k + 1}", "price_eur": p} for k, p in enumerate(prices)]}
    question = rng.choice(TEMPLATES).format(t=t)
    request = {"model": "jev-latest", "state": state,
               "questions": {"over": {"type": "noul", "instructions": question}}}
    return request, {"over": "yes" if total > t else "no"}

out = pathlib.Path("cases"); out.mkdir(exist_ok=True)
for i in range(500):
    request, expect = make_case(i)
    (out / f"{i:04d}.request.json").write_text(json.dumps(request))
    (out / f"{i:04d}.expect.json").write_text(json.dumps(expect))
```

Three details carry most of the value. The label is computed from `total > t`, not from which
branch was taken, so a bug in the branch logic cannot produce a wrong label. The `gap` puts some
cases within a euro of the threshold and some far away, so you can see whether errors cluster at
the boundary. And alternating the branch keeps the yes and no answers balanced.

## Balance, boundaries and distractors

- **Balance by construction.** Decide the answer first, then build the text that produces it, and
  check it with the computed label. A generator that picks values at random and lets the answer
  fall where it may will produce whatever ratio the ranges imply.
- **Boundaries on purpose.** Include cases exactly at the threshold ("over 100" with a total of
  100.00) and decide in the question whether "over" includes it. These are the cases where
  question wording and label logic most often disagree.
- **Distractors.** Add values that should be ignored: a shipping fee the question does not
  mention, a date that is not the delivery date, a second customer's order. Without them, the
  only number in the text is always the relevant one, and the test is easier than real life.
- **Missing information.** Leave the relevant field out of some texts and ask whether the text
  says it. These "not stated" cases are cheap to generate and catch confident answers to
  unanswerable questions; the question pattern is on
  [ask whether the text says it at all](ask-whether-the-text-says-it.md).

## Several phrasings per question

A single template tests one phrasing, and models can be sensitive to wording. Write three or more
templates per question, tag each case with its template, and report accuracy per template as well
as per kind. A large gap between templates is a finding about wording, not about the model's
ability; how to use it is on
[why wording changes an LLM's answer](why-wording-changes-the-answer.md).

## Keep it reproducible

- Fix the seed and store it with the results.
- Version the generator with your code. A changed template is a changed test.
- Record the generator version, the seed, the model file and its hash next to every reported
  score, so a number from last month can be compared with one from today.
- Keep generated and hand-labelled results in separate reports. Averaging them hides which one
  moved.

## The biases a generated set brings

Being straight about the limits:

- **Clean text.** Templates state numbers plainly; real emails bury them in prose. In our own two
  test sets, number-against-threshold questions scored 0.85 on the generated set and 0.654 on the
  hand-written one, most likely for this reason. Arithmetic (0.56 and 0.584) and dates (0.61 and
  0.598) agreed closely. The comparison is on
  [small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).
- **A style of its own.** Every text from a template shares a structure, and a system tuned
  against that structure can do better on the generated set than on real data. Use it to test,
  and if you ever tune on something, tune on anything but this.
- **Only what you thought of.** A generator covers the variations its author imagined. Real inputs
  contain the ones nobody did, which is why a hand-labelled sample of real cases stays necessary.
- **Correct labels for the question you wrote.** If the template says "within 30 days" and your
  business means "within 30 calendar days of delivery, excluding the delivery day", the code will
  faithfully compute the wrong thing. Review the label logic like any business rule.

## Short answers to the questions that lead here

**How do I create test data for an LLM without labelling?** Generate texts from templates and
compute each answer in code from the values you inserted.

**Are generated test questions as good as real ones?** They are more reliable in their labels and
less realistic in their text. Use both: generated for size and exact answers, real for coverage.

**Which kinds of question can be generated?** Anything whose answer follows from structured
values: thresholds, sums, dates, explicit rules, and whether a field is present.

**How do I avoid an easy generated test?** Add distractor values, missing fields, cases at the
exact threshold, and several phrasings per question.

**Did generated and hand-written tests agree in your measurement?** On arithmetic and dates, within
about two points. On thresholds, no: 0.85 generated against 0.654 hand-written.

**See also:** [building a yes/no test set for your own data](building-a-yes-no-test-set.md),
[accuracy by kind of question](accuracy-by-kind-of-question.md) and
[benchmark contamination and truly held-out tests](benchmark-contamination-and-held-out-tests.md).

## Sources

- Per-kind accuracy on our generated 1,000-question test set (answers computed by code, over
  orders, leave, servers, loans, courses, shipments, rentals, prescriptions and bookings) and on
  our 999-question hand-written set: our measurements of the released jevos.
- The generator is an illustrative sketch written for this page.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where the generated test and the
hand-written one agreed on arithmetic and disagreed on thresholds, and both results were kept.*
