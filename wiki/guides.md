---
title: "Guides"
description: "How to use jevos: yes/no questions over HTTP, zero-shot classification, policy checks, LLM-as-a-judge criteria and the Dino demo, all on a CPU."
nav_order: 1
has_children: true
---

# Guides

Every guide here starts from the same request: a text, one or more yes/no questions, and one
probability back per question. What changes is what the question is for.

- [Ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md) is
  the reference: fields, answers, Python, the command line, thresholds.
- [Zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md)
  turns a set of labels into one question each.
- [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md)
  covers business rules, which is where the model is weakest and where the wording matters most.
- [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md) uses the same questions to grade another
  model's output.
- [An LLM plays a Dino game on the CPU](llm-plays-dino-game-on-the-cpu.md) is the loop behind
  the README demo, and a template for any program that asks a model what to do next.
