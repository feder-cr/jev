# jevos

**Yes/no decisions on a laptop CPU in 25–110 ms.** Send a text and a yes/no question, get back
P(yes).

<p align="center">
<a href="assets/dino_run.gif"><img src="assets/dino_run.gif" alt="jevos playing a Chrome Dino-style game on the CPU, answering two yes/no questions per step (recording at 2× speed)" width="100%" /></a>
</p>

## Benchmarks

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/jevos_bench_dark.png" />
  <img src="assets/jevos_bench.png" alt="Latency on a short request: jevos-v2 26 ms, Jev 344 ms, Laya 104 ms. On a long request: jevos-v2 112 ms, Jev 345 ms, Laya 449 ms. Accuracy on 2,000 yes/no questions from unseen policies: jevos-v2 0.810, Jev 0.927, Laya 0.489" width="100%" />
</picture>

jevos-v3 answers 80.8% of 999 hand-written yes/no questions correctly (jevos-v2 80.3%, the first jevos
75.8%), and 86.5% of 821 new ones written by another model family (jevos-v2 83.1%), with the same size
and speed. The latencies here were measured with jevos-v2: jevos-v3 has the same architecture and size.

Latency is the median of 10 requests through the HTTP API, after 3 warm-up requests, on an Intel Core
Ultra 7 255H laptop with 16 threads, each request reading its text from scratch (`--state-cache 0`).
By default the server keeps the texts it has read, so asking about the same text again takes 22 ms for
the long request.

## What each one does

| | **jevos-v3** | Jev | Laya |
|---|:---:|:---:|:---:|
| Yes/no questions | ✓ | ✓ | ✓ |
| Multiple choice | ✓ | ✓ | ✓ |
| Scores | ✓ (early) | ✓ | ✓ |
| Runs on | your machine | cloud | your machine |
| Cost | free | per token | free |
| Context | 8,192 tokens | not stated | 512 tokens |

## Quickstart

From the [release](https://github.com/feder-cr/jev/releases/tag/jevos-v3), download the archive for your
system (`jev-windows-x64.zip`, `jev-linux-x64.tar.gz` or `jev-macos-arm64.tar.gz`) and the model,
`jevos-v3-openvino-int8.zip`. Unpack the model into the `jev` folder, so that it sits in `jev/model`:

```bash
tar -xzf jev-linux-x64.tar.gz                 # Windows: unzip jev-windows-x64.zip
cd jev
unzip ../jevos-v3-openvino-int8.zip           # creates model/
./jev serve                                   # Windows: jev.exe serve
```

```bash
curl http://127.0.0.1:8017/v1/systemone -H 'Content-Type: application/json' -d '{
  "model": "jev-latest",
  "state": "I was charged twice for the same order.",
  "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}}}'
```

```json
{
  "model": "jevos-v3",
  "answers": {"billing": {"type": "noul", "noul": 0.94}},
  "usage": {"input_tokens": 27, "output_tokens": 0}
}
```

`jev` runs on the CPU: jevos-v3 with 8-bit weights through [OpenVINO](https://github.com/openvinotoolkit/openvino),
in one binary with no Python and no GPU. The same release has the model as GGUF files
(`jevos-v3-q4_k_m.gguf`, `jevos-v3-q8_0.gguf`) for llama.cpp and the tools built on it.

## API

The server speaks TypeSafe Jev's wire format, so code written for Jev's SDK works unchanged for
yes/no questions.

### `POST /v1/systemone`

| Field | What it is |
|---|---|
| `model` | `jev-latest` (any `jev-*` name works) or the served model's name |
| `state` | the text to decide on: a string, or any JSON object or array |
| `questions` | one or more named questions, such as `{"type": "noul", "instructions": "…?"}` |

Here every question is a `noul`, and its answer is the probability that the answer is yes (0 to 1).
Questions in the same request share the state, which is read once: the three questions below take
about 66 ms together, against 49 ms for one of them alone, and 39 ms when the same state is asked
about again.

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
  "model": "jevos-v3",
  "answers": {
    "refund": {"type": "noul", "noul": 0.93},
    "upset": {"type": "noul", "noul": 0.83},
    "wrong_item": {"type": "noul", "noul": 0.04}
  },
  "usage": {"input_tokens": 95, "output_tokens": 0}
}
```

- **Put the rule in the question.** If the decision depends on a policy, write it into
  `instructions`, as in `refund` above. On a `noul`, Jev's optional `criteria` field is checked but
  not read; `choice` and `score` require it.
- **Every question type.** `noul`, `choice` and `score`, in Jev's shapes (see below for the last two).
- **Timing.** Every successful response carries a `Server-Timing` header: parsing, validation,
  tokenization, queue and inference times.

### Multiple choice

A `choice` question names its options in `criteria`, each with an optional description, and gets back
the most probable one, a probability per option and Jev's `confidence` (the peak probability rescaled
from uniform, 0, to certain, 1):

```json
{
  "model": "jev-latest",
  "state": {"item": "wireless mouse", "customer_message": "The box arrived empty. This is the second time!"},
  "questions": {
    "team": {
      "type": "choice",
      "instructions": "Which team should handle this message?",
      "criteria": {
        "billing": "payments, invoices, refunds",
        "shipping": "deliveries, missing or damaged parcels",
        "tech": "a product that does not work"
      }
    }
  }
}
```

```json
{
  "model": "jevos-v3",
  "answers": {
    "team": {"type": "choice", "choice": "shipping",
             "probabilities": {"billing": 0.02, "shipping": 0.93, "tech": 0.05}, "confidence": 0.89}
  },
  "usage": {"input_tokens": 233, "output_tokens": 0}
}
```

jevos answers yes/no questions, so a choice is asked as one yes/no question per option, each listing all
the options ("... Among the candidates, is it this one? Candidate: shipping"), the way the model saw
choices in training. The option's probability is its P(yes) divided by the sum over the options.
All of them are read as a prefix tree: what the option questions have in common, the state, the
instructions and the list of options, is read once, and each option then costs only its last line,
also when the request asks other questions beside the choice. A request whose questions fit in up to
1,024 tokens is one model call; a longer one (a long state, many questions) is several, the state read
in pieces of up to 2,048 tokens. Each option still
sees only its own question: the answers are the same as asking each option alone. On the laptop where
one yes/no question takes about 20 ms, this three-option choice takes about 100 ms, a ten-option one
about 170 ms.

On 2,676 held-out choice questions, the most probable option is the right one 78.8% of the time, with
jevos-v3 as with jevos-v2. With jevos-v2: 74.2% on rental questions with labels from code, 81.2%
agreement with Jev on workflow questions, and the `confidence` says when to trust it: at 0.75 or more, 95% of the answers are right, on 46% of the
questions; below 0.25, 47%.

### Scores

A `score` question lists its levels in `criteria`, lowest first, and gets back Jev's answer: the
expected level (`score`, from 0 to the number of levels minus one), the levels as they were sent
(`legend`), a probability per level and a `confidence`:

```json
"anger": {"type": "score", "instructions": "How angry is the customer?",
          "criteria": ["calm", "annoyed", "angry", "furious"]}
```

```json
"anger": {"type": "score", "score": 1.25, "legend": {"0": "calm", "1": "annoyed", "2": "angry", "3": "furious"},
          "probabilities": {"0": 0.32, "1": 0.27, "2": 0.25, "3": 0.16}, "confidence": 0.0}
```

Here jevos cannot place the message on the scale (it gives "Is the customer angry?" a P(yes) of 0.28
too), and `confidence` 0 says so: route answers like this one to a person or to another question.

A score is asked as one yes/no question per level above the lowest, "is it at this level or higher?"
("... Scale from lowest to highest: calm < annoyed < angry < furious. Is the answer at the following
level or higher? Level: angry"), as in training. P(level ≥ k) is made non-increasing where the separate
answers are not (pool adjacent violators, 19% of held-out questions), and P(level = k) is
P(≥ k) − P(≥ k + 1). The `confidence` is Jev's: how concentrated the probabilities are around the most
probable level, from 0 for a uniform spread to 1.

On 2,350 held-out score questions the most probable level is right 56.5% of the time with jevos-v3
(jevos-v2 54%), and within one level 83% (82%). On 329 everyday ratings (how angry, how urgent, how
severe; 3–5 levels, labels by Claude) it is right 61% of the time and within one level 96% (jevos-v2 55%).
It depends on the kind of question (measured with jevos-v2):

- **Rubrics** (contract clauses, logistics events, survey responses; 1,389 questions, labels from Jev):
  69% right, 93% within one level, against 45% for always the most common level. Confidence 0.75 or
  more: 93% right, on 24% of the questions.
- **Points to add up** (a fraud score from six rules; 961 questions, labels from code): 34% right,
  barely above the most common level's 33%, and confidently wrong: jevos overrates, and at confidence
  0.75 or more it is right 44% of the time. Compute sums in code and ask jevos the parts as yes/no
  questions.

### Other endpoints

| Endpoint | Returns |
|---|---|
| `GET /v1/models` | the served model and its `jev-latest` alias |
| `GET /health` | `{"status": "ready", …}` once the model is loaded |

### From Python

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

### From the command line

`jev decide` answers one request file without starting a server. The file holds the same body as
`POST /v1/systemone`, and the answer comes back in the same shape:

```bash
./jev decide request.json
```

`--output answer.json` writes the answer to a new file instead of printing it; an existing file is
never overwritten. A request the server would refuse prints the same error body on stderr, with exit
status 1.

## Server options

| Option | Default | |
|---|---|---|
| `--model-dir` | `model` beside the binary | the model folder |
| `--name` | the name in `model/model.json` | the served model's name |
| `--threads` | all logical CPUs | CPU threads; fewer if other heavy apps are running |
| `--host`, `--port` | `127.0.0.1`, `8017` | where the server listens |
| `--ctx` | 8,192 | most tokens in one question's prompt (the state plus that question) |
| `--state-cache`, `--state-cache-tokens` | 16, 8,192 | texts kept for later requests, how many and how many tokens in all; 0 turns it off |
| `--batch-tokens` | 384 | small requests arriving together are read in one model call while their tokens fit; at most 1,024 |
| `--warmup` | 384 | prompt lengths from 1 to this many tokens are compiled while the server is idle; at most 384, 0 turns it off |
| `--dynamic-quantization` | 128 | activations in INT8 groups of this many values; 0 keeps them f32, slower |

With `JEV_API_KEY` set, every call but `/health` needs `Authorization: Bearer <key>`. The server needs about
1 GB of memory once the model is loaded, up to 1.4 GB with its cache of recent texts full. `/health`
reports the SHA-256 of each model file and a fingerprint of them all (`model_files`, `fingerprint`), so a
logged decision can be tied to the exact model that made it.

## Build from source

```bash
python -m pip install -r requirements.txt     # OpenVINO's SDK, CMake, Ninja, the tests' packages
python scripts/build.py                       # dist/jev; on Windows, from a Visual Studio developer prompt
python tests/check.py                         # with the model in dist/jev/model
```

A C++17 compiler is the only other requirement; CMake fetches llama.cpp (the tokenizer) itself.
`export/export_openvino.py` is how the model folder was made from the trained weights.

## Guides

The [wiki](https://github.com/feder-cr/jev/wiki) has the long version:
[zero-shot text classification with yes/no questions](https://github.com/feder-cr/jev/wiki/zero-shot-text-classification-yes-no-questions),
[LLM as a judge on a CPU](https://github.com/feder-cr/jev/wiki/llm-as-a-judge-on-a-cpu),
[policy decisions](https://github.com/feder-cr/jev/wiki/llm-policy-decisions-put-the-rule-in-the-question),
and what we measured about the model, including
[why a small LLM says yes when the answer is no](https://github.com/feder-cr/jev/wiki/why-a-small-llm-says-yes).

## Credits

Built together with [Loris Salsi (@LosaLosSantos)](https://github.com/LosaLosSantos).
