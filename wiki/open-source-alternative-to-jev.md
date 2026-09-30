---
title: "An open-source alternative to Jev for yes/no decisions"
description: "Moving yes/no questions from TypeSafe's hosted Jev to a local jevos server: same wire format, a new base URL, and what is refused or ignored."
parent: "Comparisons"
nav_order: 2
---

# An open-source alternative to Jev for yes/no decisions

**jevos is an open-source (MIT) local server that speaks TypeSafe Jev's wire format, so yes/no
questions written for Jev move over by pointing the client at `http://127.0.0.1:8017` instead of
TypeSafe's API.** The request body, the `jev-latest` model name and the shape of the answers stay
the same, for `choice` and `score` questions too. Two things do not: `score` answers are early
(54% on held-out score questions, 82% within one level), and on a yes/no question Jev's optional
`criteria` field is accepted but not read, so the rule has to live in `instructions`. Whether the switch is worth it depends on how a local 1B model does on your questions, not on the
code.

Conflict of interest, in one line: we build jevos, and we are not affiliated with TypeSafe AI,
which builds Jev.

The code change is the easy part of a migration. The part that deserves a day of work is
checking accuracy on your own cases, because on 2,000 rule questions neither model had been
tuned on, Jev was right 0.927 of the time and jevos 0.810. For some applications that gap is
irrelevant; for others it is the whole decision.

This page is what stays the same, the switch step by step, what the local server refuses or
ignores, how to confirm which model answered, and when to keep Jev.

## What stays the same when you switch

The endpoint is `POST /v1/systemone` on both. A request has `model`, `state` (a string, or any
JSON object or array) and named `questions`; each yes/no question is
`{"type": "noul", "instructions": "...?"}`, and each answer comes back as
`{"type": "noul", "noul": <P(yes)>}` under the same name. A `choice` question,
`{"type": "choice", "instructions": "...", "criteria": {"<option>": "<optional description>", ...}}`,
comes back as `{"type": "choice", "choice": <most probable option>, "probabilities": {...}, "confidence": ...}`,
Jev's shape. The `usage` block is there too, with
`output_tokens` always 0, because jevos generates no text.

The model name also carries over. `jev-latest` is accepted, and so is any other `jev-*` name, so a
client pinned to a Jev version string does not need editing. The response always names the model
that actually answered, `jevos-v2`, which is how you tell the two apart in logs.

Authentication works the same way when you want it. Start the server with the `JEV_API_KEY`
environment variable set and every call except `/health` requires `Authorization: Bearer <key>`,
with a `401` otherwise, which is the header TypeSafe's API reference documents for Jev.

## The switch, step by step

1. Download the archive for your machine (`jev-linux-x64.tar.gz`, `jev-windows-x64.zip` or
   `jev-macos-arm64.tar.gz`), `jevos-v2-openvino-int8.zip` and `SHA256SUMS.txt` from the
   [release page](https://github.com/feder-cr/jev/releases/tag/jevos-v2) and check the hashes.
2. Unpack the binary and the model, and start the server:

```bash
tar -xzf jev-linux-x64.tar.gz
cd jev
unzip ../jevos-v2-openvino-int8.zip     # creates model/
./jev serve --threads 16
```

3. Change the base URL in your client. With raw HTTP, replace
   `https://api.typesafe.ai/v1/systemone` with `http://127.0.0.1:8017/v1/systemone`. TypeSafe's
   Python SDK documents a `base_url` parameter and a `TYPESAFE_BASE_URL` environment variable
   for this, and reads the key from `TYPESAFE_API_KEY`:

```bash
export TYPESAFE_BASE_URL=http://127.0.0.1:8017
```

If the local server runs without `JEV_API_KEY`, it does not check the header, so whatever
placeholder key the SDK requires is enough.

4. Wait for `GET /health` to return `{"status": "ready", ...}` before sending traffic; the model
   loads once and then stays resident, using about 1 GB of memory.

The same steps are covered from the other direction, starting from nothing, on
[ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## What the local server refuses or ignores

| Jev feature | On jevos |
|---|---|
| `noul` questions | answered |
| `choice` questions | answered, 2 to 26 options |
| `score` questions | answered, 2 to 10 levels (early) |
| `criteria` on a `noul` | accepted, not read |
| unknown fields | rejected with `422` |
| languages other than English | not supported |

The `criteria` line is the one that bites quietly. A request that relied on
`criteria.true` and `criteria.false` to define what yes means will still be accepted and still
get an answer, but the definition will not have been used. Move it into the question: "Our
policy refunds items reported missing within 30 days of delivery. Should this customer get a
refund?" is the README's own example of a rule written into `instructions`, and the reasoning
behind it is on [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

A `choice` question is answered the way the model saw choices in training: one yes/no question
per option, each listing all the options, and each option's P(yes) divided by the sum over the
options. `probabilities` sum to 1, in the options' order, and `confidence` is Jev's: the peak
probability rescaled from uniform (0) to certain (1). The text is read once, and each option
costs about as much as one more yes/no question. When a text can fit several options at once,
separate yes/no questions per option, as in
[zero-shot classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md),
give each option its own probability instead of a share of 1. A `score` becomes one "is it at least level n?"
question per boundary.

## How to confirm which model answered

Three checks, all cheap:

- **The `model` field** of every response names the served model, not the alias you sent.
- **`GET /v1/models`** lists the served model and the `jev-latest` alias; the alias entry says it
  is answered by the local model and not by TypeSafe's Jev.
- **`GET /health`** reports the SHA-256 of the model's files, so a log line can prove which files made a
  decision.

Every response also carries a `Server-Timing` header with the inference time, which makes a
before-and-after latency comparison possible without a separate benchmark harness.

## When to keep Jev

Keep Jev, or keep it for part of the traffic, when:

- **Accuracy on hard rules matters most.** 0.927 against 0.810 on our 2,000 policy questions,
  with the gap largest on additive point scores, where several signals are summed and compared
  with a cut-off.
- **You need `score` today.**
- **Your texts are not in English.**
- **You do not want to operate anything.** A local server is a folder and a port, and
  you own its uptime.

Because the wire format is shared, the split does not have to be all or nothing. The pattern on
[a model cascade: small model first, large model on doubt](model-cascade-small-model-first.md)
answers confident cases locally and sends the middle band to the hosted model, and the only
difference between the two calls is the URL.

## Short answers to the questions that lead here

**Is there an open-source alternative to Jev?** For yes/no and multiple-choice questions, jevos: MIT code, a model
file on GitHub, and the same wire format, running on a CPU.

**Do I have to change my code?** For `noul` and `choice` questions, only the base URL. Code
using `score`, or `criteria` on a `noul`, needs the changes in the table above.

**Why did my `criteria` stop working?** On a yes/no question, jevos accepts the field and does
not read it. Put the
definition of yes into `instructions`.

**Is it faster?** From a laptop in Europe, on our two requests: 26 and 112 ms locally against 344
and 345 ms for the hosted API, network included.

**Is it as accurate?** No. On our 2,000 policy questions Jev was right 0.927 of the time and jevos
0.810. Measure on your own cases before moving everything.

**See also:** [jevos vs Jev vs Laya for yes/no decisions](jevos-vs-jev-vs-laya.md),
[securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md) and
[local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md).

## Sources

- Wire format compatibility, the `jev-*` aliases, the `choice` and `score` answers, the
  `criteria` behaviour, `/health`, `/v1/models`, `Server-Timing` and `JEV_API_KEY`: the
  [jev README](https://github.com/feder-cr/jev) and the jev source.
- Latency (26/112 ms against 344/345 ms) and accuracy (0.927 against 0.810): our own
  measurements, published in the README.
- Jev's base URL, the Bearer header and the SDK's `base_url`, `TYPESAFE_BASE_URL` and
  `TYPESAFE_API_KEY`: [TypeSafe API reference](https://docs.typesafe.ai/api.md) and
  [Python SDK usage](https://docs.typesafe.ai/sdk/python/usage.md), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which kept the wire format so that
leaving it, in either direction, is a one-line change.*
