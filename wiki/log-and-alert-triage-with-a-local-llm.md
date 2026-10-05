---
title: "Log and alert triage with a local LLM"
description: "Triage alerts with a local LLM: send the JSON log line as the state, ask if it is actionable, known benign or customer-facing, keep numbers in code."
parent: "Use cases"
nav_order: 13
---

# Log and alert triage with a local LLM

**A small local LLM can pre-sort alerts by answering yes/no questions about each one: is this
alert actionable, does it match a pattern we know is harmless, does it mention a
customer-facing service.** Send the alert or the log line as JSON in `state`, put your known
benign patterns in the question, and let code handle every threshold, count and timestamp. The
result is a queue where the on-call engineer sees the likely real problems first, not an
automatic silencer.

The value is in the messages that no rule was written for. Alert rules fire on metrics and
patterns you anticipated; the text that comes with them (an exception message, a free-form
description from a monitoring tool, a line from a third-party service) is where a reader helps.
A yes/no model reads that text on the same machine that holds the logs, which matters when logs
contain customer data.

This page is the questions that work, the state, how to describe known noise, what to keep out
of the model's hands, what the latency means for an alert stream, and what not to put in the
request or in your decision log.

## Which alert questions are reading questions?

The useful questions are about what the alert says, not about what the numbers add up to:

- **Actionable**: "Does this alert describe a problem that a person needs to fix?"
- **Known benign**: "Does this alert describe a scheduled restart, a deploy, or a health check
  retry?"
- **Customer-facing**: "Does the alert mention the checkout, login or public API service?"
- **Data risk**: "Does the message mention lost, corrupted or exposed data?"
- **Stated cause**: "Does the error message say what caused the failure?"

These sit in the part of our test results where a small model does well. On 999 hand-written
yes/no questions, over texts that included logs, the first jevos answered stated facts right
0.954 of the time and "the text does not say" 0.847 (measured on the first jevos; per-kind
numbers for jevos-v4 are not published). The last one matters for alerts:
"Does the error message say what caused the failure?" is a gate that stops the model from
guessing a cause the log does not contain. The pattern is on
[ask whether the text says it at all](ask-whether-the-text-says-it.md).

## What goes in the state?

A log line is already JSON in most stacks, and `state` accepts any JSON object. Send a trimmed
version:

```json
{
  "model": "jev-latest",
  "state": {
    "service": "checkout-api",
    "level": "error",
    "message": "payment provider timeout after retries, order left in pending state",
    "deploy_in_progress": false
  },
  "questions": {
    "actionable":      {"type": "noul", "instructions": "Does this alert describe a problem that a person needs to fix?"},
    "customer_facing": {"type": "noul", "instructions": "Does the alert concern a service that customers use directly, such as checkout or login?"},
    "known_benign":    {"type": "noul", "instructions": "Does the alert describe a scheduled restart, a deploy, or a health check retry?"}
  }
}
```

Keep field names that read as English (`deploy_in_progress`, not `dip`), drop fields the
questions do not need (trace ids, hostnames, long stack frames), and add computed booleans such
as `deploy_in_progress` from your own systems rather than asking the model to infer them. Every
token you send costs time. More on this in
[sending JSON as the text: designing the state](designing-the-state-as-json.md).

## How do you describe known noise?

Every team has alerts that look alarming and are not: the nightly job that logs a warning, the
retry that always succeeds on the second attempt. Write them into the question, specifically.
"Does the alert describe a scheduled restart, a deploy, or a health check retry?" works better
than "Is this alert noise?", because the model knows nothing about your systems except what the
request tells it.

When the list of benign patterns grows past a sentence or two, split it into separate
questions and combine with OR in code. One question per pattern also tells you which pattern
matched, which you want in the log when someone asks why an alert was down-ranked.

## What should stay in code?

Anything that is a comparison of numbers or times. Alert data is full of them: error rates,
latencies, counts per minute, timestamps. On the same 999-question set, the first jevos got questions that
compared a number with a threshold right 0.654 of the time, dates and times 0.598, and
arithmetic 0.584. "Is the error rate above 5%?" is a question for code, and so is "Did this
start within ten minutes of the last deploy?".

The first jevos also leaned toward yes on questions it could not compute: of its mistakes on that
set, 152 were wrong yeses and 91 wrong noes, and the lean sat mostly on numbers and dates. In alert
triage a wrong yes on "known benign" hides a real problem. Give that question a high bar, and
never let it suppress an alert that your metric rules consider critical. The measurement is on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

## Can it keep up with an alert stream?

On our reference laptop (Intel Core Ultra 7 255H, 16 threads, no GPU) a short request
took 28 ms and a long one 130 ms. Several questions on one alert cost much less than several requests, because the alert
is read once.

That is comfortable for alerts, which arrive in tens or hundreds per hour after deduplication.
It is not a tool for the raw log firehose. Filtering millions of lines per minute is the job of
your log pipeline's own queries and rules; send the model only the lines that already crossed
a rule, or one representative per deduplicated group. The difference between one request's
latency and a server's capacity is on
[throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).

## What should not go in the request or the log?

Logs leak. OWASP's Logging Cheat Sheet lists data that should usually not be recorded directly,
including session identifiers, access tokens, authentication passwords, database connection
strings, encryption keys and sensitive personal data, and recommends that such values be
removed, masked, sanitised, hashed or encrypted.

Two consequences for triage. First, strip those fields before building the state: the model
does not need a token to decide whether an alert is actionable. Running locally keeps the text
on your machine, but it does not make it safe to copy secrets into a second place. Second, when
you log the model's decisions for later review, log a hash of the state rather than the state
itself if the state could contain any of the above. What to record is on
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## Short answers to the questions that lead here

**Can an LLM triage alerts?** It can read an alert's text and answer whether it looks actionable,
matches a benign pattern you describe, or mentions a service you care about. It should rank,
not silence.

**Can I send raw JSON log lines?** Yes. `state` takes any JSON object. Trim it to the fields the
questions need.

**Should the model decide whether a metric crossed a threshold?** No. Compare numbers in code;
number and date questions were among the weakest on our test set (first jevos).

**Is it fast enough for real-time alerts?** On a laptop CPU a short request took 28 ms. That fits
an alert stream, not a raw log stream.

**Is this a security tool?** No. It helps sort operational alerts. Security detection needs
dedicated tools and people.

**See also:** [latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md),
[many questions about one text](many-questions-about-one-text.md) and
[a private LLM for text classification](private-llm-for-text-classification.md).

## Sources

- Our measurements: latency and the reference laptop from the
  [jev README](https://github.com/feder-cr/jev); accuracy by kind of question and the 152 to 91
  error split from our 999-question test set, measured on the first jevos. Latency was measured
  with jevos-v3 (same size and speed as jevos-v4). No alert-triage set was measured.
- OWASP, [Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html),
  data to exclude from logs, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The "known benign" question is the one to watch: its wrong yes is the expensive
mistake in this use case.*
