---
title: "Measurements"
description: "What we measured on jevos: yes-bias, arithmetic and a benchmark that overstated accuracy. Numbers from our own test sets, with their limits."
nav_order: 2
has_children: true
---

# Measurements

These pages report our own measurements of the released jevos model, including the ones that
do not flatter it. They describe how the model behaves, not how it was built.
The main instrument is a set of 999 yes/no questions written from scratch after training (10
scenarios, 10 texts each, 10 questions per text, half of them "yes"), which the model never saw
and which nothing was tuned on.

- [Why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md)
- [Small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md)
- [Our held-out benchmark said 0.855, new questions said 0.757](held-out-benchmark-too-optimistic.md)

Latency numbers everywhere in this wiki come from one laptop: an Intel Core Ultra 7 255H, 16
threads, no GPU. Other machines will differ.
