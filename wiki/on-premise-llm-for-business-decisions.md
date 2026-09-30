---
title: "On-premise LLM for business decisions"
description: "Run a yes/no LLM on CPU servers you already own: what it needs, how to size it without guessing, and the governance a decision model needs on premises."
parent: "Local and private AI"
nav_order: 3
---

# On-premise LLM for business decisions

**An on-premise LLM for business decisions can run on the CPU servers already in your data
centre: jevos needs no GPU, one folder with the binary and an 8-bit model, and about 1 GB of memory once loaded.** It
answers yes/no questions about a text or a JSON record with a probability, so it slots in
wherever a system needs to read free text before a rule acts: a claim description, a ticket, a
supplier email. The hardware question is small. The governance question, who owns the questions,
the thresholds and the model file, is the one to settle before the first decision goes live.

That inversion is the non-obvious part. With a large model, the first on-premise question is
which GPUs to buy. With a small CPU model that question disappears, and what is left is the work any decision
system needs: change control, a test set, and a record of why each decision was made.

This page is what the model needs from a server, how to find out whether your servers are fast
enough, how it fits next to existing systems, and the governance that makes its decisions
defensible.

## What does it need from a server?

| Resource | What jevos needs | Where the figure comes from |
|---|---|---|
| Accelerator | none; CPU only (x86-64 with AVX2, or Apple silicon) | README |
| Memory | about 1 GB with the model loaded, up to 1.4 GB with its cache of recent texts full | README |
| Disk | the `jev` folder: binary, OpenVINO's libraries and the INT8 model | release files |
| Context | up to 8,192 tokens per request | README |
| Network | one port, `127.0.0.1:8017` by default | README |
| Runtime | one prebuilt binary; no Python, no compiler | release files |

The release has prebuilt archives for Linux on x64 (glibc 2.35+, such as Ubuntu 22.04+),
Windows on x64 and macOS on Apple silicon, so a typical server image does not need a build toolchain. Which of
those platforms we have timed is a separate question, answered next.

## Will it be fast enough on our servers?

We do not know, and neither does anyone who has not run it there. Every latency figure we
publish comes from one machine, a laptop with an Intel Core Ultra 7 255H, 16 threads, no GPU,
with the text read from scratch: 26 ms for a request of about 30 tokens, 112 ms for about 190
tokens. Server CPUs differ in cores, clock, cache and memory bandwidth, and
have other workloads on them. The number that matters is yours, measured like this:

1. Take a sample of real inputs, at their real length.
2. Start the server with `--threads` set to the cores you can give it; the README's advice is
   your core count, fewer if other heavy applications share the machine.
3. Warm it up, then take the median and the 90th percentile of many requests, one at a time.
   Read the `Server-Timing` header for the model's share. The method is on
   [measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).
4. Only then look at concurrency. One laptop figure is latency, not capacity, as explained on
   [throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).

Two effects you can predict without measuring: long inputs cost more than short ones, and
several questions about the same text cost much less than separate requests, because the text
is read once. On the reference laptop, three questions took about 66 ms against 49 ms for one.

## How does it fit next to systems we already run?

As a small internal HTTP service. The common shapes:

- **Sidecar.** One jevos process on the same host as the application that needs it, reached on
  `127.0.0.1`. No network exposure, no authentication to manage.
- **Shared internal service.** One or more hosts serving several applications. Bind to an
  internal interface with `--host`, set `JEV_API_KEY` so every call except `/health` needs a
  Bearer token, and terminate TLS at a reverse proxy.
- **Batch.** `jev decide` answers a request file without a server, for nightly jobs over a
  queue of documents; see [batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).

Because the server speaks the same wire format as TypeSafe's hosted Jev for yes/no questions,
an application written against Jev's SDK can point at the internal server instead, and back,
by changing the base URL.

## Who owns the questions and the thresholds?

This is the governance point most teams skip. In a yes/no system the business logic lives in
three places, and each needs an owner:

- **The questions.** "Does the customer report the item as damaged?" is a specification. A
  reworded question can give different answers on the same text, so questions belong in version
  control and change through review, like code.
- **The thresholds.** Acting on yes above 0.5 or above 0.9 is a business decision about which
  mistake costs more. Write down who chose it and why, as on
  [thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).
- **The rule.** Anything that is really a policy ("refund if reported within 30 days") should
  be computed in code from facts the model reads, not left to the model. On 2,000 yes/no
  questions about business policies none of the models was tuned on, jevos was right 0.810 of
  the time; the hosted Jev, 0.927. That is a good first reader, not a final judge. The pattern
  is on [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

## What does change control look like for a model?

The model is a file, so it can be controlled like one.

- **Identify it by hash.** `/health` reports the SHA-256 of each loaded model file and a
  fingerprint. Record the fingerprint in every
  decision log; [logging LLM decisions for audit](logging-llm-decisions-for-audit.md) lists the
  rest.
- **Verify before deploying.** Check new files against `SHA256SUMS.txt` from the release.
- **Test before switching.** Keep a set of your own labelled cases, split by kind of question,
  and run old and new models on it before any change. A hundred real cases is a start; see
  [building a yes/no test set](building-a-yes-no-test-set.md).
- **Treat the weights as a model change.** jev runs 8-bit (INT8) weights. The GGUF files in
  the release are the same model for other tools, and on 215 parity cases jev's answers are
  within 0.056 of the `q8_0` GGUF's. Do not swap one runtime for another without measuring on
  yours.

## Short answers to the questions that lead here

**Can an LLM run on premise without a GPU?** A small one can. jevos runs on the CPU through
OpenVINO and needs about 1 GB of memory with the model loaded.

**How many requests per second will our server handle?** Unmeasured on any server. On the
reference laptop, one client got 8.7 requests per second and eight clients 10.1; time your own
hardware with your own inputs.

**Does on-premise mean compliant?** No. It keeps the text inside your network; access control,
retention and the rules on automated decisions still apply.

**Which decisions should it make alone?** Low-stakes reading decisions such as routing and
tagging. Anything with real consequences should combine the model's reading, a rule in code, and
a person for the uncertain middle.

**Does it need internet access?** Only to download the binary and the model once; see
[offline AI for decisions](offline-ai-for-decisions.md).

**See also:** [self-hosted AI for decisions](self-hosted-ai-for-decisions.md),
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md) and
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

## Sources

- Requirements, options, endpoints and the wire format: the [jev README](https://github.com/feder-cr/jev).
- Release platforms: the [jevos release](https://github.com/feder-cr/jev/releases/tag/jevos-v2).
- Latency, requests per second, the 215 parity cases and the 2,000-question comparison: our
  measurements on an Intel Core Ultra 7 255H laptop.

---

*From the notes of [jev](https://github.com/feder-cr/jev). We have timed jevos on one laptop,
and this page says so every time it quotes a number.*
