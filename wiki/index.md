---
title: "jevos: yes/no decisions from a local LLM on the CPU"
description: "jevos-v4 is a local model that answers yes/no, choice and score questions about a text, on a laptop CPU in 28 to 130 ms. Guides, measurements, limits."
nav_order: 0
---

# jevos: yes/no decisions from a local LLM on the CPU

**jevos is a small local LLM that answers yes/no questions about a text.** You send the text and the question, and it sends back P(yes), the probability that the
answer is yes. It runs on a laptop CPU, in 28 ms for a short request and
130 ms for a long one, and it generates no text, so there is nothing to parse.

That narrow job is the point. A router, a filter, a policy check, a judge in an evaluation
loop: most decisions an application asks a language model for are yes/no questions with a
threshold on top, and they do not need a chat model on a GPU or a call to a hosted API.

This wiki is the long version of the [README](https://github.com/feder-cr/jev): how to use the
server, how to turn other kinds of decisions into yes/no questions, what we measured about the
model, including where it is wrong, and how it compares with the alternatives.

![jevos playing a browser game on the CPU, answering two yes/no questions per step (recording at 2x speed)](https://raw.githubusercontent.com/feder-cr/jev/main/assets/dino_run.gif)

## Start here

- [Ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md):
  the request, the answer, Python, the command line, and what to do with the number.
- [Zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md):
  routing a ticket to one of several labels with one question per label.
- [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md):
  refunds, access rules and thresholds, and why rules are the model's hardest case.
- [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md): evaluation criteria as yes/no
  questions, scored locally.

## What we measured

- [Why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md): 152 wrong
  yeses against 91 wrong noes on 999 new questions (first jevos), and why calibration does not fix it.
- [Small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md):
  on the first jevos, 0.58 on questions that need a sum, against 0.95 on questions that only need reading.
- [Our held-out benchmark said 0.855, new questions said 0.757](held-out-benchmark-too-optimistic.md):
  why a test split built like the training data is not held out enough.

## How it compares

- [jevos vs Jev vs Laya for yes/no decisions](jevos-vs-jev-vs-laya.md): speed, accuracy,
  context, cost and what each one can answer.

## Browse by topic

- [Speed](speed.md): where LLM latency comes from, and why a model that generates nothing is fast.
- [Probability and thresholds](probability-and-thresholds.md): what P(yes) means, calibration,
  and how to turn a probability into a decision.
- [Question design](question-design.md): how to write questions a small model answers well.
- [Use cases](use-cases.md): moderation, triage, routing, screening, documents.
- [Evaluation](evaluation.md): grading RAG pipelines, judges, CI checks and test sets.
- [Agents and routing](agents-and-routing.md): routers, cascades, tool gating and guardrails.
- [Integrations](integrations.md): Python, JavaScript, curl, n8n, Slack, CI and more.
- [Local and private AI](local-and-private-ai.md): self-hosted, offline and on-premise decisions.
- [llama.cpp and GGUF](llama-cpp-and-gguf.md): the runtime and the file format of the release's
  GGUF builds, and the tokenizer jev takes from llama.cpp.

## What it is not

jevos-v4 answers yes/no questions, picks one option from several (`choice`) and rates on a scale
(`score`), in English only. Scores are early (58.5% right on held-out score questions, 86%
within one level). On rules and scenarios it is right 0.76 to 0.95 of the time on our yes/no
and choice tasks, against 0.88 to 1.00 for Jev, which is good for a first pass and not good
enough to be the last word on a refund, and the measurement pages say exactly where it fails.

---

*jevos is built by [feder-cr](https://github.com/feder-cr) with
[Loris Salsi (@LosaLosSantos)](https://github.com/LosaLosSantos). The code is MIT, the model is
on the [release page](https://github.com/feder-cr/jev/releases/tag/jevos-v4).*
