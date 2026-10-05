---
title: "Ask a local LLM a yes/no question and get P(yes)"
description: "Send a text and a yes/no question to a local LLM on your CPU and get back one probability, not text. The request, the answer, Python, CLI, thresholds."
parent: "Guides"
nav_order: 1
---

# Ask a local LLM a yes/no question and get P(yes)

**To get a yes/no answer from a local LLM as a number, send the text and the question to a
jevos server and read `noul`, the probability that the answer is yes.** The model does one
forward pass over your text and returns that probability directly: no tokens are generated, so
there is no "Yes." or "I think so" to parse, and no answer that comes back in the wrong format.
On a laptop CPU a short request takes about 28 ms and a long one about 130 ms.

A chat model can be pushed into the same job by asking it to answer with one word and reading
the word, or its log-probabilities. That works, and it is slower, needs a larger model, and
makes the probability a by-product of text generation instead of the output.

This page is the request and the answer, several questions in one call, the same thing from
Python and from the command line, and what to do with the number once you have it.

## Start the server

Download the archive for your platform (`jev-linux-x64.tar.gz`, `jev-macos-arm64.tar.gz` or
`jev-windows-x64.zip`) and the model, `jevos-v4-openvino-int8.zip`, from the
[release](https://github.com/feder-cr/jev/releases/tag/jevos-v4), then:

```bash
tar -xzf jev-linux-x64.tar.gz
cd jev
unzip ../jevos-v4-openvino-int8.zip     # creates model/
./jev serve
```

On Windows, unzip `jev-windows-x64.zip` and run `jev.exe serve` (`.\jev.exe serve` in
PowerShell). There is no Python, no download step and nothing to compile; `jev` runs on the CPU
only. `--threads` defaults to all logical CPUs; set it lower if other heavy programs share the
machine. The server listens on `127.0.0.1:8017`.

## One question

```bash
curl http://127.0.0.1:8017/v1/systemone -H 'Content-Type: application/json' -d '{
  "model": "jev-latest",
  "state": "I was charged twice for the same order.",
  "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}}}'
```

```json
{
  "model": "jevos-v4",
  "answers": {"billing": {"type": "noul", "noul": 0.94}},
  "usage": {"input_tokens": 27, "output_tokens": 0}
}
```

Three fields go in:

| Field | What it is |
|---|---|
| `model` | `jev-latest` (any `jev-*` name works) or the served model's name |
| `state` | the text to decide on: a string, or any JSON object or array |
| `questions` | one or more named questions, each `{"type": "noul", "instructions": "...?"}` |

One number comes out per question. `output_tokens` is always 0, because nothing is generated.

`state` does not have to be prose. A JSON record works as it is, which saves you from
flattening a ticket, an order or a log line into a sentence before asking about it.

## Several questions about the same text

Questions in one request share the `state`, and the text is read once. On the README's
example, three questions take about 66 ms together, against 49 ms for one of them alone, so
the second and third cost a fraction of the first:

```json
{
  "model": "jev-latest",
  "state": {
    "item": "wireless mouse",
    "delivered": "5 days ago",
    "customer_message": "The box arrived empty. This is the second time!"
  },
  "questions": {
    "refund": {
      "type": "noul",
      "instructions": "Our policy refunds items reported missing within 30 days of delivery. Should this customer get a refund?"
    },
    "upset": {"type": "noul", "instructions": "Is the customer upset?"},
    "wrong_item": {"type": "noul", "instructions": "Does the customer say they received the wrong item?"}
  }
}
```

```json
{
  "model": "jevos-v4",
  "answers": {
    "refund": {"type": "noul", "noul": 0.93},
    "upset": {"type": "noul", "noul": 0.83},
    "wrong_item": {"type": "noul", "noul": 0.04}
  },
  "usage": {"input_tokens": 95, "output_tokens": 0}
}
```

So if you need several facts about one text, ask them in one call rather than in a loop. That
is also the basis of [zero-shot classification with one question per label](zero-shot-text-classification-yes-no-questions.md).

## From Python

```python
import requests

answer = requests.post("http://127.0.0.1:8017/v1/systemone", json={
    "model": "jev-latest",
    "state": "I was charged twice for the same order.",
    "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}},
}).json()

if answer["answers"]["billing"]["noul"] > 0.5:
    print("send to billing")
```

The wire format is the one TypeSafe's Jev uses, so code already written against Jev's SDK works
against this server for yes/no, `choice` and `score` questions. Scores are early: the most probable level is right
58.5% of the time on 2,350 held-out score questions and within one level 86%, weak on points to add up.

## From the command line, without a server

`jev decide` answers one request file and exits. The file holds the same body as the HTTP
request, and the answer comes back in the same shape:

```bash
./jev decide request.json
```

`--output answer.json` writes the answer to a new file instead of printing it, and never
overwrites an existing one. That makes it usable in a batch job or a CI step where running a
server would be one moving part too many.

## What to do with the number

A probability is more useful than a word because you choose where to cut it.

- **0.5 is the neutral threshold**, and on the natural yes/no questions of our held-out split
  the probabilities were well calibrated on an earlier jevos (calibration error 0.009: an answer
  of 0.8 is right about 80% of the time; not re-measured on jevos-v4).
- **Move the threshold with the cost of a mistake.** If a wrong "yes" means a refund paid by
  mistake, act automatically only above 0.9 and send the middle band to a person.
- **Watch the middle.** The model leans toward "yes" on questions it cannot compute, such as
  dates and sums, so an answer around 0.5 to 0.6 on those deserves suspicion. The measurement is
  on [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Put the context in the question

The model knows only what is in `state` and in `instructions`. If the answer depends on a rule,
write the rule into the question, as the `refund` example does. On a yes/no question, Jev's
optional `criteria` field is accepted for compatibility and checked, but not read. How to phrase rules, and how much to trust the answer
when you do, is on [LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

## The other endpoints

| Endpoint | Returns |
|---|---|
| `GET /v1/models` | the served model and its `jev-latest` alias |
| `GET /health` | `{"status": "ready", ...}` once the model is loaded |

Every successful response to `/v1/systemone` carries a `Server-Timing` header with the inference time,
which is the number to log if you want to know what the model costs you, separate from the
network. If the `JEV_API_KEY` environment variable is set when the server starts, every call
except `/health` needs `Authorization: Bearer <key>`, as the hosted API does.

## Short answers to the questions that lead here

**Can a local LLM return a probability instead of text?** Yes. jevos returns P(yes) for each
question and generates no text at all.

**How fast is it on a CPU?** About 28 ms for a short request and 130 ms for a long one on an
Intel Core Ultra 7 255H with 16 threads. Extra questions on the same text cost less than the
first.

**Do I need a GPU?** No. The server runs on the CPU only.

**Can I send JSON instead of text?** Yes. `state` accepts a string, an object or an array.

**What languages does it understand?** English only.

**Can it answer multiple-choice questions?** Yes. Send a `choice` question with the options as
the keys of `criteria`; the answer is the most probable option, a probability for each option and
a confidence. A three-option choice takes about 100 ms and a ten-option one about 170 ms on the laptop where a yes/no question takes about 20 ms.

**See also:** [zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md),
[LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md) and
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- The request and answer examples and the latencies are from the
  [jev README](https://github.com/feder-cr/jev); the billing question returns 0.94 there.
- Calibration error: our held-out split, 6,397 natural yes/no questions, measured on an earlier jevos.
- The `JEV_API_KEY` behaviour is read from jev's server code.
- TypeSafe's Jev wire format: [docs.typesafe.ai](https://docs.typesafe.ai).

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The billing question above is the README's Quickstart.*
