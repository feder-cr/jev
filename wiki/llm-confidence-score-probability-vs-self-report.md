---
title: "LLM confidence scores: probabilities vs self-reports"
description: "Asking a chat model how confident it is vs reading a probability: what research found about self-reported confidence, and how to test either one."
parent: "Probability and thresholds"
nav_order: 14
---

# LLM confidence scores: probabilities vs self-reports

**A self-reported confidence ("I am 90 percent sure") is text the model generates, and in
published evaluations it has tended to be overconfident, clustering between 80 and 100 percent
whatever the model's real accuracy; a probability read from the model is a number that can be
checked, thresholded and recalibrated against labelled cases.** Neither is trustworthy by
default. The research is not one-sided either: for some chat models, verbalised confidence has
been better calibrated than their token probabilities. What decides is measurement on your own
questions.

A note on interest: we build jevos, which returns a probability and no text, so we have a stake
in this comparison. The findings below are from other people's papers, and the test at the end
works the same whichever kind of score you use.

This page is the two kinds of confidence score, what the research found about each, why
post-training complicates both, what a probability gives you that a sentence does not, and how
to test any confidence score on your data.

## Two things called a confidence score

- **Self-reported (verbalised) confidence.** You ask a chat model to answer and to say how
  confident it is, and it writes "Confidence: 85%". The number is generated like any other
  token, has to be parsed, and reflects whatever the model learned about how people talk about
  confidence.
- **A probability read from the model.** The probability the model assigns to an answer, for
  example to "yes" or to one of four options, or a P(yes) returned directly by a decision model.
  There is nothing to parse, and every input gets one.

Both can be calibrated or not. The difference is where the number comes from, and therefore how
it tends to fail.

## What research found about self-reported confidence

Xiong and colleagues (ICLR 2024) benchmarked confidence elicitation across five datasets and
five models, including GPT-4 and LLaMA 2 Chat. Their first finding: "LLMs, when verbalizing
their confidence, tend to be overconfident, potentially imitating human patterns of expressing
confidence." The values predominantly fell between 80 and 100 percent and were typically
multiples of 5. Prompting strategies reduced the gap between stated confidence and accuracy,
but the models' ability to tell their right answers from their wrong ones stayed limited, in
some settings close to random.

Two results pull the other way, and belong on the same page:

- Lin, Hilton and Evans (2022) showed that GPT-3 can be taught to express uncertainty in words,
  such as "90% confidence", that maps to well-calibrated probabilities, including under some
  distribution shift.
- Tian and colleagues (2023) found that for models fine-tuned with human feedback, verbalised
  confidences emitted as output tokens were typically better calibrated than the models'
  conditional probabilities, often with a relative reduction in expected calibration error of
  about 50 percent on the benchmarks they used.

So "never trust a self-report" is too strong. "Do not trust one you have not measured" is right.

## Why post-training complicates both

The GPT-4 technical report shows the effect in one figure. On a subset of MMLU, the pre-trained
model's probabilities had an expected calibration error of 0.007; after post-training, 0.074,
with the caption "The post-training hurts calibration significantly." Kadavath and colleagues
(2022) found that larger models are well calibrated on multiple choice and true/false questions
when those are presented in the right format.

Read together: the raw probability of a pre-trained model can be well calibrated on a clean
format; the training that makes a model a good assistant can degrade that; and the self-report
of the same assistant may or may not recover it. None of this transfers automatically to your
questions, which is why the section below matters more than any of these numbers.

## What a probability gives you that a sentence does not

For decisions in software, a probability has practical advantages whatever its calibration:

- **No parsing, no format errors.** jevos returns `noul`, P(yes), with `output_tokens` always 0;
  there is no "Confidence: high" to interpret. The general argument is on
  [structured output vs a probability](structured-output-vs-a-probability.md).
- **A value for every case, on a continuous scale.** Self-reports that cluster on 80, 90 and 95
  leave little room for a threshold to separate cases.
- **It can be recalibrated.** A temperature or a [Platt fit](platt-scaling-for-a-yes-no-model.md)
  on your labelled cases adjusts a probability; there is no equivalent knob on a generated
  sentence short of changing the prompt.

What it does not give you is calibration for free. On natural yes/no questions like our held-out
split, jevos's calibration error was 0.009; on 999 new questions it leaned toward yes, with 152
wrong yeses against 91 wrong noes, mostly on arithmetic and dates. A probability can be
confidently wrong in one direction too, as
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md) documents.

## How to test any confidence score on your data

The test is the same for a self-report, a token probability or a P(yes):

1. **Label a few hundred real cases** for the questions you care about.
2. **Collect the score for each**, parsed to a number between 0 and 1.
3. **Check calibration**: draw a [reliability diagram](reading-a-reliability-diagram.md) and
   compute [expected calibration error](expected-calibration-error-explained.md), with the count
   in each bin.
4. **Check discrimination**: do right answers get higher confidence than wrong ones? Xiong and
   colleagues call this failure prediction; a score that cannot separate the two is useless for
   a threshold even if its average is honest.
5. **Split by kind of question**, since both kinds of score can be good on some kinds and poor on
   others.

If a self-report passes on your data, use it. If a probability fails, recalibrate or change the
question. The score that survives this test is the one to trust.

## Short answers to the questions that lead here

**Can I ask an LLM how confident it is?** You can, and the answer is text. Published
evaluations found such self-reports tend to be overconfident, often between 80 and 100 percent.

**Are token probabilities better than self-reported confidence?** Sometimes. For some models
fine-tuned with human feedback, the verbalised confidence was better calibrated. Measure on your
cases.

**Why does post-training hurt calibration?** The GPT-4 report shows it happening on MMLU; the
report does not reduce it to one cause, and neither should we.

**Does jevos report a confidence?** It reports P(yes) per question and generates no text.

**How do I check any confidence score?** Label a few hundred cases, draw a reliability diagram,
and check whether right answers get higher scores than wrong ones.

**See also:** [what P(yes) means](what-p-yes-means.md),
[LLM calibration explained](llm-calibration-explained.md) and
[jevos vs the OpenAI API for yes/no classification](jevos-vs-openai-api-for-classification.md).

## Sources

- Our measurements: ECE 0.009 on 6,397 natural yes/no held-out questions (`jevos-q8_0`); 152 vs
  91 errors on the 999-question set (`jevos-q4_k_m`). `output_tokens` 0 is from the
  [jev README](https://github.com/feder-cr/jev).
- Xiong et al. (2024, ICLR),
  [Can LLMs Express Their Uncertainty?](https://arxiv.org/abs/2306.13063), fetched 2026-09-29.
- Lin, Hilton, Evans (2022),
  [Teaching Models to Express Their Uncertainty in Words](https://arxiv.org/abs/2205.14334),
  fetched 2026-09-29.
- Tian et al. (2023), [Just Ask for Calibration](https://arxiv.org/abs/2305.14975), fetched
  2026-09-29.
- OpenAI (2023), [GPT-4 Technical Report](https://arxiv.org/abs/2303.08774), Figure 8, fetched
  2026-09-29.
- Kadavath et al. (2022),
  [Language Models (Mostly) Know What They Know](https://arxiv.org/abs/2207.05221), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev). We return a probability because it
can be checked, and this page tells you to check ours too.*
