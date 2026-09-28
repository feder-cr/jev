---
title: "Edge AI decisions on a CPU"
description: "Yes/no decisions on branch servers and small machines near the data: the CPU-only, 1.2 GB profile, what we have not measured, how to test a device."
parent: "Local and private AI"
nav_order: 6
---

# Edge AI decisions on a CPU

**A yes/no model that runs on the CPU in about 1.2 GB of memory can make decisions on machines
at the edge, a branch server, a shop-floor PC, a kiosk, a laptop in the field, without a GPU or
a connection to a data centre.** jevos is a 619 MB file driven by a prebuilt llama.cpp runtime,
and the source pins runtime packages for x64 and arm64 on Linux and Windows and for macOS. What
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

- **Model file:** `jevos-q4_k_m.gguf`, 619 MB on disk; `jevos-q8_0.gguf`, 943 MB.
- **Memory:** about 1.2 GB more once the model is loaded.
- **Compute:** CPU only, with `--device cpu`. `--threads` defaults to 4.
- **Context:** up to 8,192 tokens per request.
- **Output:** one probability per question, no generated text, so there is no generation step
  whose length depends on the answer.
- **Network:** none after the download; the server listens on `127.0.0.1:8017` by default.

A device that cannot spare about 1.2 GB of memory for the model, on top of what else it runs,
is out before any timing. The runtime list in the source has no Android or iOS package, so
phones and tablets are out of scope for this setup.

## What we have and have not measured

Measured, on an Intel Core Ultra 7 255H laptop with 16 threads, no GPU, `q4_k_m`:

- 54 ms for a request of about 30 tokens, 220 ms for about 190 tokens: roughly 1.1 ms per
  prompt token;
- three questions on one text in about 165 ms, against 103 ms for one alone;
- `q8_0` about 1.7 times slower than `q4_k_m`, and `q4_0` and `iq4_nl` about as fast as
  `q4_k_m`.

Not measured: any ARM board, any mini PC, any older or low-power x64 processor, any server CPU.
We cannot tell you whether a given small device answers in 100 ms or in two seconds, and we
would rather say so than extrapolate from a laptop with 16 threads.

## How do you test a device before committing to it?

1. Install the runtime and model on the actual device, not a similar one.
2. Collect a few dozen real inputs at their real length. Latency grows with the number of
   tokens, as explained on
   [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md),
   so short test strings flatter the result.
3. Start the server with `--threads` at the device's core count, then try fewer; the README's
   advice is to go lower when other heavy programs share the machine, and on an edge box
   something always does.
4. Warm up, then record the median and the 90th percentile over many single requests, using the
   `Server-Timing` header for the model's share. The method is on
   [measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).
5. Repeat while the device does its normal job. An idle benchmark on a machine that is never
   idle is the wrong number.

If `q4_k_m` is too slow, a bigger file will not help: `q8_0` is slower. Shortening the input
usually helps more than anything else you control.

## Shaping requests for a small machine

- **Send only what the questions need.** A JSON `state` with three relevant fields costs fewer
  tokens than the full record. The method is on
  [sending JSON as the text: designing the state](designing-the-state-as-json.md).
- **Ask several questions in one request.** The text is read once, so the second and third
  questions cost a fraction of the first.
- **Compute in code.** Dates, totals and comparisons are cheap and exact in code and are the
  model's weakest questions: 0.584 on arithmetic and 0.598 on dates on our 999-question set,
  against 0.954 on stated facts. On a slow device, every question you remove is time saved too.

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

When the decision needs more than the small model gives. It reads English only, answers yes/no
only, and on 2,000 questions about business policies none of the models was tuned on it was
right 0.815 of the time against 0.927 for the hosted Jev. If a site can reach a data centre,
answering locally and sending only the doubtful cases upstream is often the better shape; see
[a model cascade: small model first](model-cascade-small-model-first.md).

## Short answers to the questions that lead here

**Can an LLM run on an edge device?** A small one can, if the device can spare about 1.2 GB of
memory and has a CPU the prebuilt runtime supports. Whether it is fast enough is a measurement
you make on that device.

**Does jevos run on a Raspberry Pi?** We have not tested it on one, or on any ARM board. The
source includes Linux arm64 runtime packages; the rest is untested.

**Do edge decisions need a GPU?** Not with jevos: it is built for `--device cpu`.

**Which quantization should an edge device use?** Start with `q4_k_m`. `q8_0` is larger and
about 1.7 times slower on the reference laptop, and the two builds' accuracy has not been
compared on the same set.

**What if the device loses its connection?** Nothing changes for the model; it needs no
network after the download.

**See also:** [an LLM on a laptop](an-llm-on-a-laptop.md),
[running llama.cpp CPU only](llama-cpp-cpu-only.md) and
[Q4_K_M vs Q8_0](q4-k-m-vs-q8-0-speed-and-size.md).

## Sources

- File sizes, memory, context, options and endpoints: the [jev README](https://github.com/feder-cr/jev).
- Runtime platforms: the pinned package list in `src/jev/runtime/llama_release.py`.
- Latency, quantization speed and accuracy figures: our measurements on an Intel Core Ultra 7
  255H laptop; no other hardware has been measured.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The list of machines we have not
measured on is longer than the list we have, and this page keeps it that way in writing.*
