---
title: "Our held-out benchmark said 0.855, new questions said 0.757"
description: "A test split made the same way as the training data overstated a small LLM's accuracy by ten points. The measurements, and how to build a held-out test."
parent: "Measurements"
nav_order: 3
---

# Our held-out benchmark said 0.855, new questions said 0.757

**A test split that comes out of the same process as the training data is not held out enough,
even when whole topics are kept aside.** Our held-out split for jevos excluded three business
policies and three workflows entirely, and the model scored 0.855 on it. On 999 questions
written from scratch after training, by a different process, it scored 0.757. The ten points
between the two are the part of the first number that measured familiarity with our own way of
writing questions, not the ability to answer them.

This matters beyond our model. Anyone fine-tuning a model on generated or templated data and
testing on a split of the same data is likely to be reporting the optimistic number.

This page is the four measurements from most familiar to least, why excluding topics was not
enough, and how we build tests now.

## Four numbers, from most familiar to least

| Test | What is new to the model | Accuracy |
|---|---|---|
| development split, 12,320 questions | nothing but the specific texts | 0.915 |
| held-out split, 27,274 questions | three policies and three workflows never seen | 0.855 |
| 2,000 questions on the held-out policies, answers computed by code | the policies, and a separate question set | 0.815 |
| 999 questions written after training | everything: texts, questions, phrasing, author | 0.757 |

Each step away from the training data costs accuracy, and the biggest step is the last one,
where nothing was produced by the same pipeline. The held-out split feels like a hard test,
since whole domains are missing from training, and it still sits closer to the development
number than to the independent one.

One caveat, stated so it can be weighed: the first two rows were measured on the `q8_0` build
and the last on `q4_k_m`. We have not run both builds on the same set for this page, so some part
of the gap could be quantization. The ordering of the middle rows, and the size of the last step,
do not depend on it.

## Why excluding topics was not enough

Holding out a policy removes its rules from training. It does not remove:

- **the question templates.** A question about an unseen policy can still be phrased the way
  a thousand training questions were phrased.
- **the text formats.** A ticket, an email or a JSON record produced the same way looks
  like every other ticket, email and record in training, whatever it is about.
- **the answer distribution.** The balance of yes and no, and what a hard case looks like, come
  from the same place.

A model can learn all three, and a test that shares them rewards it for doing so. The 999
questions share none of them, and on those the model's weaknesses show up that the held-out
split had hidden: arithmetic at 0.584 and a lean toward yes that the held-out calibration
(0.009 error on its natural questions) gave no hint of. Both are measured on
[why a small LLM says yes](why-a-small-llm-says-yes.md) and
[small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).

## How we build a test now

**Written after training, by a different process.** The 999 questions were written from scratch
once the model was finished: 10 scenarios, 10 texts per scenario of 40 to 150 words, 10
questions per text, exactly half of them yes. None of the text came from the pipeline that made
the training data.

**Labelled by kind.** Each question carries the reasoning it needs: stated fact, tone,
paraphrase, intent, negation, not stated, rule, number, date, arithmetic. A single accuracy hides
where a model fails; ten accuracies say what to fix and what to route around.

**Never tuned on.** The set is used to report, not to choose. The moment a threshold, a prompt or
a checkpoint is picked by looking at it, it becomes a development set and a new test is needed.
We do not publish its questions for the same reason.

**A cheap second test with exact answers.** Hand-written questions can be mislabelled, so we
also generate 1,000 questions from templates with answers computed by code. It is not
independent in the same way, since templates have a style of their own, but it has no labelling
errors, it can be regenerated at any size, and on the kinds that matter it agreed with the
hand-written set on arithmetic and dates within two points.

## What the right number is

For jevos, the number to plan with is the independent one, 0.757 overall, together with its
breakdown: above 0.84 on everything that is reading, 0.58 to 0.72 on everything that is
computing or applying a rule. The README reports the 2,000-question comparison, 0.815, because
the same questions were put to Jev and Laya and the comparison is fair; this page is the
context for reading it.

## Short answers to the questions that lead here

**Why is my model worse in production than on the test set?** If the test set was cut from the
same data as the training set, it shares templates, formats and style with it. Ours overstated
accuracy by about ten points.

**Is holding out whole topics enough?** Not in our measurement: excluding three policies and
three workflows still gave 0.855, against 0.757 on independent questions.

**How big should an independent test be?** Ours has 999 questions, enough to report accuracy per
kind of question with about 30 to 220 questions per kind.

**Should I publish my test questions?** Not if you want to keep using them: published questions
end up in someone's training data.

**What is a good cheap check?** Questions generated from templates with answers computed by
code. They have no labelling errors and reproduced our hardest cases.

**See also:** [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md),
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md) and
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- All four accuracies are our own measurements of the released jevos: development and held-out
  splits on `jevos-q8_0`, the 2,000-question comparison as reported in the
  [jev README](https://github.com/feder-cr/jev), and the 999-question set on `jevos-q4_k_m`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. We report the lower number because it is the one your application will see.*
