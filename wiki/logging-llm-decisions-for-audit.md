---
title: "Logging LLM decisions for audit"
description: "What to log for every LLM decision so it can be explained and re-run later: state hash, questions, probabilities, threshold, model file hash, timing."
parent: "Agents and routing"
nav_order: 7
---

# Logging LLM decisions for audit

**To audit an LLM decision later you need to know exactly what the model read, what it was
asked, what it answered, what rule turned the answer into an action, and which model file and
runtime produced it.** For a yes/no decision that is a short record: a hash (or a copy) of the
state, the questions, each probability, the threshold and the action taken, the model name and
file hash, and the timing. With those fields a reviewer can explain the decision, and you can
re-run the same request against the same file and compare.

Most LLM logs miss the two fields that matter most for audit: the threshold, which is where the
decision is actually made, and the exact model file, which is what changes silently when
someone updates a dependency. A model name such as `jev-latest` is an alias, not an identity.

This page is an example record, what each field is for, how to pin the model's identity, how to
reproduce a decision, what not to store, and how logs feed review.

## An example record

One line per decision, as JSON. The answer below is the README's billing example; the hashes are
shortened placeholders.

```json
{
  "ts": "2026-09-29T10:14:03Z",
  "decision_id": "d-7f3a",
  "caller": "ticket-router",
  "state_sha256": "9c1e...",
  "state_tokens": 27,
  "questions": {"billing": "Is this a billing problem?"},
  "answers": {"billing": 0.9},
  "rule": "billing > 0.5",
  "action": "queue:billing",
  "model": "jevos-v2",
  "model_file_sha256": "e41b...",
  "jev_release": "jevos-v2",
  "inference_ms": 50,
  "total_ms": 54
}
```

The timing values in the record are placeholders too; log what the response tells you.

## What each field is for

| Field | Why it is there |
|---|---|
| state hash or copy | proves what the model read; the hash lets you match a later complaint to the record without storing the text |
| input token count | tells you whether the text was the one expected (a doubled or truncated input changes it) |
| questions, verbatim | a changed word changes the answer; see [why wording changes an LLM's answer](why-wording-changes-the-answer.md) |
| probabilities | the evidence; keep all of them, not only the one that drove the action |
| rule and action | the decision itself, in the form code applied it |
| model name and file hash | which model answered, exactly |
| jev release | the rest of what produced the numbers |
| timing | spots slow paths and lets you check latency budgets after the fact |
| caller | which part of the system asked, so one bad caller can be found |

The probabilities are the field people most often throw away after thresholding. Keep them. A
decision taken at 0.51 and one taken at 0.99 are different events for a reviewer, and a pile of
decisions just above the threshold is the first sign that it is in the wrong place.

## Pinning the model's identity

`GET /health` on the jevos server reports, once the model is loaded, the SHA-256 of each model file
and a fingerprint of them all. Read it at startup and attach those values to every record the process
writes, instead of calling it per decision.

Two consequences follow. Any change of model file shows up as a new hash in the log, so a before and after comparison is a
query. And the release file can be checked against the published `SHA256SUMS.txt`, so the hash
in your log can be tied to a specific public release file.

## Timing from the response

Every successful jevos response carries a `Server-Timing` header with `inference` and `total` durations.
Log both. The difference between them, and between them and the wall clock of your client, tells
you whether a slow decision was the model, the server or the network. The general method is on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

## Reproducing a decision

An audit question is often "would the same input give the same answer today?". Keep enough to
rebuild the request body: the state (or a way to fetch it again), the questions and the model
name. Then run it offline against the same model file:

```bash
./jev decide request.json --output replay.json
```

`--output` writes to a new file and never overwrites one, which suits an audit trail. Comparing
the replay's probabilities with the logged ones shows whether the model still answers the same
way.

Being straight about the limit: we have not published a test of bit-for-bit repeatability across
machines or runtime releases, so treat the replay as a check to run and compare, not as a
promise. Pin the file and the runtime release, and differences have far fewer places to come
from.

## What not to put in the log

- **Raw personal data by default.** If the state is a customer message, store its hash and a
  pointer to where the message already lives under its own retention rules. A decision log that
  duplicates every message becomes a second copy of your most sensitive data.
- **API keys.** If the server runs with `JEV_API_KEY`, every call except `/health` carries a
  Bearer token. Do not log request headers wholesale.
- **Free-text explanations generated afterwards.** jevos generates no text (`output_tokens` is
  always 0), so there is no model rationale to store. An explanation written later by another
  model is not a record of why this one answered.

Running the model locally keeps the text off third-party servers, but it does not decide who in
your company can read the logs. That is access control, and it is covered on
[a private LLM for text classification](private-llm-for-text-classification.md).

## From logs to review

A log is useful when someone reads it. Three uses repay the effort:

- **A review queue.** Decisions in the uncertain band go to a person, and the person's verdict
  is logged next to the model's. The design is on
  [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).
- **A test set.** Every reviewed case is a labelled case. After a few weeks you have a set drawn
  from real traffic to re-check thresholds on.
- **Appeals.** When someone contests a decision, the record answers what was read, asked and
  decided, and by which model file.

For decisions about people, the law may require more than a log; the EU case is discussed on
[GDPR and automated decision-making with an LLM](gdpr-and-automated-decision-making.md).

## Short answers to the questions that lead here

**What should I log for each LLM decision?** State hash, questions, all probabilities, the rule
and action, the model name and file hash, jev release, and timing.

**Is the model name enough?** No. An alias such as `jev-latest` points at whatever file is
served. Log the fingerprint from `/health`.

**Should I store the input text?** Store a hash and a pointer by default. Store the text only
when you need replays and your retention rules allow it.

**Can I re-run an old decision?** Yes, with `jev decide` on the same request file and model file,
then compare the probabilities.

**Why keep probabilities after thresholding?** They show how close each decision was, and a
cluster near the threshold means the threshold needs a look.

**See also:** [securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md),
[batch decisions from files with jev decide](batch-decisions-with-jev-decide.md) and
[gating AI agent tool calls](gating-ai-agent-tool-calls.md).

## Sources

- The `/health` fields, `Server-Timing` header, `jev decide` behaviour, `JEV_API_KEY`, release
  files and `SHA256SUMS.txt`: the [jev README](https://github.com/feder-cr/jev) and source.
- The billing example (0.9, 27 input tokens): the jev README.
- No outside sources are used on this page.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. Its server reports the model's file hashes on /health, the one field most decision
logs are missing.*
