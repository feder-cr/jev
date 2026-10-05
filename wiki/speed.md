---
title: "Speed"
description: "Why jevos answers in 28 to 130 ms on a CPU, what makes an LLM fast or slow, and how to measure latency honestly."
nav_order: 4
has_children: true
---

# Speed

Latency is the reason a yes/no model exists: a decision that takes 28 ms can sit inside a request, a webhook or a loop. These pages explain where the time goes in a language model, why a model that generates nothing is fast, and how to measure it without fooling yourself. The measured numbers come from one laptop, an Intel Core Ultra 7 255H with 16 threads.

- [The fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md)
- [What makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md)
- [Why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md)
- [Prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md)
- [Why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md)
- [Why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md)
- [Many questions about one text: why the extra ones are cheap](many-questions-about-one-text.md)
- [CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md)
- [Latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md)
- [Measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md)
- [Q4_K_M vs Q8_0: speed and size for a small model](q4-k-m-vs-q8-0-speed-and-size.md)
- [Throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md)
