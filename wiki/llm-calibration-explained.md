---
title: "LLM calibration explained with yes/no answers"
description: "What calibration means for an LLM that returns P(yes), how it differs from accuracy, and why a model calibrated on familiar data can lean on new questions."
parent: "Probability and thresholds"
nav_order: 2
---

# LLM calibration explained with yes/no answers

**An LLM is calibrated when its probabilities match how often it is right: of the questions it
answers with a P(yes) of about 0.8, about 80 percent really are yes.** Calibration is a separate
property from accuracy. A model can be accurate and overconfident, or mediocre and honest about
it, and you need calibration, not accuracy, to put a meaningful threshold on the number. It is
also a property of a model on a kind of data: good calibration on familiar questions does not
carry over to new kinds of question.

The practical reason to care is that every threshold, review band and expected-cost rule on
these pages assumes the probability means what it says. If it does not, the rule still runs; it
just makes different mistakes than the ones you planned for.

This page is the difference between calibration and accuracy, why thresholds depend on it, what
published work found for large models, what we measured on jevos, and how to check it on your
own questions.

## Calibration and accuracy answer different questions

Accuracy asks: after thresholding, how often is the answer right? Calibration asks: when the
model says 0.8, is it right 80 percent of the time? Two illustrative extremes show that they are
independent:

- A model that answers 0.5 to every question on a set that is half yes is perfectly calibrated
  and useless. Its 0.5s are right half the time, exactly as claimed.
- A model that is right 95 percent of the time but always says 0.999 is accurate and badly
  calibrated. It claims one error in a thousand and delivers fifty.

Both are made-up illustrations, not measurements. What you want is a model that separates yes
from no well (discrimination, which accuracy and precision/recall measure) and whose numbers
mean what they say (calibration). The two are checked with different tools: a threshold sweep
for the first, a [reliability diagram](reading-a-reliability-diagram.md) and
[expected calibration error](expected-calibration-error-explained.md) for the second.

## Why a threshold needs calibrated numbers

If you only ever threshold one question at one cut-off chosen on labelled data, calibration
matters less: any number that ranks cases well can be cut at the point your data says. It
starts to matter as soon as you use the number as a probability:

- **Expected cost.** The rule "act on yes when P(yes) is above C_fp / (C_fp + C_fn)" is only
  correct when P(yes) is a real frequency; see
  [thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).
- **One threshold across many questions.** Using 0.7 for every question assumes 0.7 means the
  same thing everywhere.
- **Averages and combinations.** The mean of P(yes) over a batch estimates the number of yeses
  only if the numbers are calibrated; so do products for AND.
- **Review bands.** A band from 0.3 to 0.8 is sized in probability; if the numbers drift, the
  band sends the wrong cases to people.

## What published work found for large models

Calibration of neural networks is not automatic. Guo and colleagues (2017) found that modern
neural networks, unlike those from a decade earlier, are poorly calibrated, and that a simple
post-processing step, temperature scaling, fixed much of it on most datasets; the method is on
[temperature scaling for LLM probabilities](temperature-scaling-for-llm-probabilities.md).

For language models the picture depends on format and on training stage. Kadavath and
colleagues (2022) report that larger models are well calibrated on diverse multiple choice and
true/false questions when they are provided in the right format. The GPT-4 technical report
(2023) shows a calibration plot on a subset of MMLU where the pre-trained model has an ECE of
0.007 and the post-trained model 0.074, with the caption "The post-training hurts calibration
significantly." A yes/no format helps; the training stage can undo it.

## What we measured on jevos, and where it breaks

These measurements were taken on the first jevos; calibration has not been re-measured on
jevos-v4. On the natural yes/no questions of its held-out split (6,397 questions), the
calibration error was 0.009; on the development split, 0.018. On questions of the kind the
model knows, its probabilities were close to the frequencies it achieved.

On 999 hand-written questions, the picture changes. The first jevos's errors leaned one way: 152
answers said yes when the answer was no, against 91 the other way (jevos-v4 scores 78.9% on the
same 999 questions, but per-kind numbers for it are not published). And
the lean is concentrated. The mean P(yes) on questions whose answer is no is 0.59 for
arithmetic and 0.53 for dates and times, but 0.17 for negation and 0.16 for tone. A calibrated
model would keep all of these low. On the question kinds it can read, it does; on the kinds it
cannot compute, it is confidently wrong in one direction.

This is the general lesson in one example. Calibration measured on a held-out split that
resembles the training data describes that data. It does not describe a new kind of question,
and no single number can. The full analysis is on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## How to check calibration on your own questions

1. Collect a few hundred real cases for the questions you will use, labelled by hand, with the
   kind of reasoning each question needs. [Building a yes/no test set](building-a-yes-no-test-set.md)
   covers how.
2. Run them and keep every P(yes).
3. Bin the probabilities, compare each bin's mean P(yes) with its fraction of yes, and draw the
   reliability diagram. Compute ECE if you want one number.
4. Do it again per kind of question. A pooled diagram can look fine while one kind leans.
5. If the error is a uniform over- or under-confidence, a temperature or a
   [Platt fit](platt-scaling-for-a-yes-no-model.md) on separate labelled data can fix it. If it
   is a lean on one kind of question, change the question instead: compute in code, and ask the
   model only what it reads.

## Short answers to the questions that lead here

**What is LLM calibration?** How well the model's stated probabilities match how often it is
right. A calibrated 0.8 is right about 80 percent of the time.

**Is a more accurate model better calibrated?** Not necessarily. The two are measured
separately, and a model can be strong on one and weak on the other.

**Are LLMs well calibrated?** It depends on format and training stage. Published results show
good calibration for pre-trained models on multiple choice and true/false formats, and worse
calibration after post-training in at least one report.

**Is jevos calibrated?** The first jevos had ECE 0.009 on natural yes/no questions like its
held-out split, and on new kinds of question, especially arithmetic and dates, it leaned toward
yes. Neither has been re-measured on jevos-v4.

**Can calibration be fixed after the fact?** A uniform miscalibration, often yes. A directional
error on some kinds of question, not with one global correction.

**See also:** [what P(yes) means](what-p-yes-means.md),
[how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md) and
[our held-out benchmark said 0.855](held-out-benchmark-too-optimistic.md).

## Sources

- Our measurements, all on the first jevos: ECE 0.009 (held-out, 6,397 natural yes/no
  questions) and 0.018 (dev split); the 999-question set for error counts and mean P(yes) by
  kind.
- Guo, Pleiss, Sun, Weinberger (2017),
  [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), fetched
  2026-09-29.
- Kadavath et al. (2022),
  [Language Models (Mostly) Know What They Know](https://arxiv.org/abs/2207.05221), fetched
  2026-09-29.
- OpenAI (2023), [GPT-4 Technical Report](https://arxiv.org/abs/2303.08774), Figure 8, fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The 0.009 and the 0.59 describe the
same model on two kinds of data, and we keep both on the page on purpose.*
