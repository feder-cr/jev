---
title: "jevos: yes/no decisions from a local LLM on the CPU"
description: "jevos is a 1B local LLM that answers yes/no questions about a text with one probability, on a laptop CPU in 50 to 220 ms. Guides, measurements and limits."
nav_order: 0
---

# jevos: yes/no decisions from a local LLM on the CPU

**jevos is a small local LLM that answers one kind of question: a yes/no question about a
text.** You send the text and the question, and it sends back P(yes), the probability that the
answer is yes. It runs on a laptop CPU through llama.cpp, in 54 ms for a short request and
220 ms for a 190-token one, and it generates no text, so there is nothing to parse.

That narrow job is the point. A router, a filter, a policy check, a judge in an evaluation
loop: most decisions an application asks a language model for are yes/no questions with a
threshold on top, and they do not need a chat model on a GPU or a call to a hosted API.

This wiki is the long version of the [README](https://github.com/feder-cr/jev): how to use the
server, how to turn other kinds of decisions into yes/no questions, what we measured about the
model, including where it is wrong, and how it compares with the alternatives.

## Start here

- [Ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md):
  the request, the answer, Python, the command line, and what to do with the number.
- [Zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md):
  routing a ticket to one of several labels with one question per label.
- [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md):
  refunds, access rules and thresholds, and why rules are the model's hardest case.
- [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md): evaluation criteria as yes/no
  questions, scored locally.
- [An LLM plays a Dino game on the CPU](llm-plays-dino-game-on-the-cpu.md): the demo in the
  README, and the control loop behind it.

## What we measured

- [Why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md): 152 wrong
  yeses against 91 wrong noes on 999 new questions, and why calibration does not fix it.
- [Small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md):
  0.58 on questions that need a sum, against 0.95 on questions that only need reading.
- [Our held-out benchmark said 0.855, new questions said 0.757](held-out-benchmark-too-optimistic.md):
  why a test split built like the training data is not held out enough.

## How it compares

- [jevos vs Jev vs Laya for yes/no decisions](jevos-vs-jev-vs-laya.md): speed, accuracy,
  context, cost and what each one can answer.

## What it is not

jevos answers yes/no questions in English, and only those. Multiple choice and scores are on
the roadmap and are refused today with a `422`. On rules it has never seen it is right about
four times in five (0.815 on 2,000 such questions), which is good for a first pass and not good
enough to be the last word on a refund, and the measurement pages say exactly where it fails.

---

*jevos is built by [feder-cr](https://github.com/feder-cr) with
[Loris Salsi (@LosaLosSantos)](https://github.com/LosaLosSantos). The code is MIT, the model is
on the [release page](https://github.com/feder-cr/jev/releases/tag/jevos).*
