---
title: "Small language models explained"
description: "What counts as a small language model, what it does well (reading) and badly (computing), measured on 999 questions, and why narrow tasks suit it."
parent: "Local and private AI"
nav_order: 8
---

# Small language models explained

**A small language model is one with few enough parameters, roughly a billion rather than tens
or hundreds of billions, to run on ordinary hardware such as a laptop CPU.** What it gives up is
breadth: it reads well and reasons poorly. On 999 yes/no questions written after it was
finished, the 1B model jevos was right 0.954 of the time on facts stated in the text and 0.938
on tone, but 0.584 on questions that needed arithmetic and 0.598 on dates. Small models suit
narrow tasks where the job is to read, and where computing can be done in code.

"Small" is not a technical category with a fixed boundary. It is a practical one: small enough
that the hardware stops being the project, and that one person can measure the model's
behaviour on their own data in an afternoon.

This page is what "small" means, what a small model is good and bad at with measured numbers,
why a narrow task changes the picture, how small compares with large on the same job, and why
small-model benchmarks deserve suspicion.

## What counts as small?

There is no official threshold. In practice people call a model small when it runs without
specialised hardware: a few hundred million to a few billion parameters, quantized to a few
bits per weight, in a file of hundreds of megabytes to a few gigabytes. jevos is at the small
end of that range: its release is named `jevos-1b`, the 4-bit file is 619 MB, and it uses about
1.2 GB of memory once loaded.

Size sets the cost of every token processed. It also sets how much the model can know and how
many steps of reasoning it can hold together, which is where the trade-off lives.

## What does a small model do well?

Reading. Questions whose answer is in the text, in some form, are where a small model is
strongest. From the 999-question set, by kind of question:

- stated fact: 0.954 (108 questions)
- tone: 0.938 (32)
- paraphrase, do two phrasings mean the same: 0.893 (84)
- the writer's intent: 0.859 (71)
- negation, the text says something is not so: 0.858 (106)
- not stated, the text does not say it at all: 0.847 (98)

These are the questions most applications actually ask: is this a billing problem, is the
customer upset, does the email ask for a meeting, does the log line mention a customer-facing
service. The texts in the set were emails, tickets, logs, reviews and forms of 40 to 150 words,
and none of the questions was used to tune anything.

## Where does it fail?

Computing. The same set, the other end:

- applying a written rule: 0.721 (104)
- a number against a threshold: 0.654 (78)
- dates and durations: 0.598 (97)
- arithmetic: 0.584 (221)

The failure has a direction. When the model cannot work out the answer it leans toward yes: 152
of its mistakes were a yes that should have been no, against 91 the other way, and on
arithmetic questions whose answer is no the mean P(yes) was 0.59. A small model is not a random
guesser on these questions; it is a biased one. The measurement is on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md), and the practical
fix, extracting the numbers and comparing them in code, is on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

## Why do narrow tasks suit small models?

Because a narrow task removes the parts of the job a small model does worst, and makes the rest
measurable.

- **No format to get wrong.** A model that returns one probability per question has no JSON to
  break, no "Yes, because..." to parse and no answer in the wrong language. `output_tokens` is
  always 0.
- **No long chain of reasoning.** A yes/no question about one condition is one step. Splitting
  a compound decision into several such questions, and combining the answers in code, keeps
  each step inside what the model reads well.
- **A task you can test completely.** With one kind of output, you can build a set of your own
  labelled cases, split it by kind of question, and know where the model is and is not
  reliable before it touches production. [Accuracy by kind of question](accuracy-by-kind-of-question.md)
  explains why the split matters more than the overall number.

A general assistant has none of these properties. That is why a model that is weak as a
chatbot can be useful as a component.

## Small vs large on the same job

On 2,000 yes/no questions about three business policies that none of the models was tuned on,
with answers computed by code, the hosted Jev was right 0.927 of the time and jevos 0.815. The
gap was largest on additive point scores, where several signals are summed and compared with a
cut-off: a computation again.

The other side of the trade is speed and place. On the same two requests, jevos took 54 and
220 ms on a laptop CPU; the hosted API took 344 and 345 ms from Europe, network included. The
full comparison is on [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md). A small model is the
cheaper, faster, local first reader; a large one is the better judge of hard cases. The choice
between them is laid out on [when a small model is enough](when-a-small-model-is-enough.md).

## Why small-model benchmarks deserve suspicion

A benchmark built like the data a model was developed on measures familiarity, not
generalisation. On a held-out split built the usual way, jevos scored 0.855 overall, with a
calibration error of 0.009 on natural yes/no questions. On the 999 questions written from
scratch afterwards, it scored 0.757. The gap is the subject of
[our held-out benchmark said 0.855](held-out-benchmark-too-optimistic.md). The lesson applies
to any small model: trust a test built from your own cases over any published number, including
ours.

## Short answers to the questions that lead here

**What is a small language model?** A language model small enough, roughly a billion parameters,
to run on ordinary hardware without a GPU. There is no fixed cut-off.

**Are small language models accurate?** At reading, fairly: 0.954 on stated facts in our test.
At computing, poorly: 0.584 on arithmetic. The kind of question matters more than the model.

**What are small models used for?** Narrow tasks such as classification, routing, filtering and
yes/no checks, where the answer is in the text and the output is simple.

**Can a small model replace a large one?** For many reading decisions, yes. For rules, sums,
dates, other languages or open-ended answers, keep the large model or move the logic into code.

**Why does a small model say yes when it does not know?** In our measurement it leans toward
yes on questions it cannot compute. Keep computation out of the question.

**See also:** [run an LLM locally without a GPU](run-an-llm-locally-without-a-gpu.md),
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md)
and [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md).

## Sources

- All accuracy, error-direction and calibration figures are our own measurements: the
  999-question set on `jevos-q4_k_m`, the held-out split on `jevos-q8_0`, and the 2,000-question
  policy comparison.
- Latency on the two requests: our measurements, reported in the
  [jev README](https://github.com/feder-cr/jev).

---

*From the notes of [jev](https://github.com/feder-cr/jev), a small model we describe by where it
fails as much as by where it works.*
