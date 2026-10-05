---
title: "Edge AI decisions on a CPU"
description: "Yes/no decisions on branch servers and small machines near the data: the CPU-only profile, what we have not measured, how to test a device."
parent: "Local and private AI"
nav_order: 6
---

# Edge AI decisions on a CPU

**A yes/no model that runs on the CPU only can make decisions on machines at the edge, a branch
server, a shop-floor PC, a kiosk, a laptop in the field, without a GPU or a connection to a data
centre.** jev is one binary with OpenVINO's libraries and a model folder of 8-bit weights,
released for Windows x64, Linux x64 and macOS on Apple silicon. What
we have not done is time it on any of those small machines: every latency figure we publish
comes from one laptop. So the profile tells you what could fit; only a test on your device
tells you what does.

That gap is the honest core of any edge claim. A model's memory footprint is a property of the
model; its latency is a property of the model and the machine together, and edge machines vary
more than any other class of hardware.

This page is the profile you can plan with, what we have and have not measured, how to test a
device before you commit to it, how to shape requests for a small machine, and how to fail
safely when the model is slow or missing.

## What counts as the edge here?

Any machine close to where the text is produced that you would rather not send it away from: a
server in a branch office reading scanned forms, a PC next to a production line reading log
lines, a point-of-sale back office, a field laptop with an unreliable connection. The common
thread is that the network is slow, expensive, intermittent or not allowed, and the decision
has to happen anyway. That is also the reason the offline setup on
[offline AI for decisions](offline-ai-for-decisions.md) matters here.

## The profile you can plan with

These are properties of the release, true on any machine that runs it:

- **Files:** the `jev` folder from `jev-windows-x64.zip`, `jev-linux-x64.tar.gz` (glibc 2.35+,
  for example Ubuntu 22.04+) or `jev-macos-arm64.tar.gz`, with `jevos-v4-openvino-int8.zip`
  unpacked into it as `jev/model`. No Python and no other runtime to install.
- **Compute:** CPU only, x86-64 (Windows or Linux) or Apple silicon. `--threads` defaults to all logical CPUs.
- **Context:** up to 8,192 tokens per question, the text plus that question.
- **Output:** one probability per question, no generated text, so there is no generation step
  whose length depends on the answer.
- **Network:** none after the download; the server listens on `127.0.0.1:8017` by default.

A device whose CPU is neither x86-64 nor Apple silicon is out before any timing. The
release has no Android, iOS or Linux arm64 build, so phones, tablets and ARM boards are out of
scope for this setup.

## What we have and have not measured

Measured, on an Intel Core Ultra 7 255H laptop with 16 threads, no GPU:

- 28 ms for a short request and 130 ms for a long one, with the text read from scratch; 22 ms
  for the long one when the same text is asked about again;
- three questions on one text in about 66 ms, against 49 ms for one alone;
- a three-option `choice` in about 100 ms and a ten-option one in about 170 ms, where a yes/no
  question takes about 20 ms.

Throughput with several clients at once is not measured on jevos-v4.

Not measured: any ARM board, any mini PC, any older or low-power x64 processor, any server CPU.
We cannot tell you whether a given small device answers in 100 ms or in two seconds, and we
would rather say so than extrapolate from a laptop with 16 threads.

## How do you test a device before committing to it?

1. Unpack the binary and the model on the actual device, not a similar one.
2. Collect a few dozen real inputs at their real length. Latency grows with the number of
   tokens, as explained on
   [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md),
   so short test strings flatter the result.
3. Start the server with the default `--threads` (all logical CPUs), then try fewer; go lower
   when other heavy programs share the machine, and on an edge box something always does.
4. Warm up, then record the median and the 90th percentile over many single requests, using the
   `Server-Timing` header for the model's share. The method is on
   [measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).
5. Repeat while the device does its normal job. An idle benchmark on a machine that is never
   idle is the wrong number.

If it is too slow, shortening the input usually helps more than anything else you control.

## Shaping requests for a small machine

- **Send only what the questions need.** A JSON `state` with three relevant fields costs fewer
  tokens than the full record. The method is on
  [sending JSON as the text: designing the state](designing-the-state-as-json.md).
- **Ask several questions in one request.** The text is read once, so the second and third
  questions cost a fraction of the first.
- **Compute in code.** Dates, totals and comparisons are cheap and exact in code and are the
  model's weakest questions: 0.584 on arithmetic and 0.598 on dates on our 999 hand-written questions (measured on the first
  jevos; per-kind numbers for jevos-v4 are not published), against 0.954 on stated facts. On a slow device, every question you remove is time saved too.

## Failing safely when the model is slow or missing

An edge deployment has to decide what happens when the model cannot answer in time.

- **Readiness.** `GET /health` returns `{"status": "ready", ...}` only once the model is
  loaded. Until then, the application should know it is running without the model.
- **Timeouts.** Put a timeout on every call, set from the p90 you measured, and choose the
  default action explicitly: hold for a person, queue for later, or take the safe branch.
- **Wait or skip.** A demo or an interactive tool can pause until the model answers. A process
  line usually cannot wait, and should skip to its safe default instead.
- **Log locally, sync later.** Keep the question names, probabilities, thresholds and the
  `/health` fingerprint on the device, and ship them when a connection is available.

## Where the edge is the wrong place

When the decision needs more than the small model gives. It reads English only, and on the
six-task comparison it trails the hosted Jev: 0.95 against 1.00 on Admission policy (yes/no rules),
0.76 against 0.91 on Rental policy (choice) and 0.50 against 0.69 on Fraud points (score). Five of
the six task sets helped choose the released checkpoint, so jevos's scores there may be slightly
optimistic. If a site can reach a data centre,
answering locally and sending only the doubtful cases upstream is often the better shape; see
[a model cascade: small model first](model-cascade-small-model-first.md).

## Short answers to the questions that lead here

**Can an LLM run on an edge device?** A small one can, if the device has a CPU jev supports:
x86-64 (Windows or Linux), or Apple silicon. Whether it is fast enough is a measurement you make on that
device.

**Does jevos run on a Raspberry Pi?** Not with jev: the release has no Linux arm64 build, and
we have not tested any ARM board.

**Do edge decisions need a GPU?** Not with jevos: jev runs on the CPU only.

**Which quantization should an edge device use?** jev runs the model with 8-bit (INT8) weights,
so there is none to choose. The `q4_k_m` and `q8_0` GGUF files in the release are for llama.cpp
and other tools.

**What if the device loses its connection?** Nothing changes for the model; it needs no
network after the download.

**See also:** [an LLM on a laptop](an-llm-on-a-laptop.md),
[running llama.cpp CPU only](llama-cpp-cpu-only.md) and
[Q4_K_M vs Q8_0](q4-k-m-vs-q8-0-speed-and-size.md).

## Sources

- Release files, CPU requirements, context, options and endpoints: the [jev README](https://github.com/feder-cr/jev).
- Platforms: the archives of the [jevos-v4 release](https://github.com/feder-cr/jev/releases/tag/jevos-v4).
- Latency and accuracy figures: our measurements on an Intel Core Ultra 7
  255H laptop; no other hardware has been measured.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The list of machines we have not
measured on is longer than the list we have, and this page keeps it that way in writing.*
