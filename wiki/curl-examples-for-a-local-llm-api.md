---
title: "curl examples for a local LLM decision API"
description: "curl POST JSON examples for a local yes/no LLM server: --json and -d, bodies from a file, Bearer auth, Server-Timing, /health, /v1/models, a 422."
parent: "Integrations"
nav_order: 10
---

# curl examples for a local LLM decision API

**To POST JSON with curl, send the body with `-d` and a `Content-Type: application/json` header,
or use `--json`, which sets that header and `Accept: application/json` for you and implies
POST.** Against a local `jev serve` that is one command to `http://127.0.0.1:8017/v1/systemone`,
and the answer comes back as JSON with one `noul`, the probability of yes, per question. Add
`-D -` to print the response headers, including `Server-Timing`, the server's own inference and
total time.

curl is the fastest way to find out whether a problem is in the model, the server or your
client. If the same request works from curl and fails from your code, the model is not the
problem.

This page is the basic request, bodies from files, auth, timing, the other endpoints and what a
`422` looks like. Each command is a minimal sketch to adapt; curl facts are from its manual,
fetched 2026-09-29.

## The basic POST

This is the README's Quickstart:

```bash
curl http://127.0.0.1:8017/v1/systemone -H 'Content-Type: application/json' -d '{
  "model": "jev-latest",
  "state": "I was charged twice for the same order.",
  "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}}}'
```

```json
{
  "model": "jevos-q4_k_m",
  "answers": {"billing": {"type": "noul", "noul": 0.9}},
  "usage": {"input_tokens": 27, "output_tokens": 0}
}
```

The `-H` matters. curl's manual says `-d` sends data with the POST method using the content type
`application/x-www-form-urlencoded`, so without the header the server is told the body is a
form, not JSON. Since
curl 7.82.0, `--json '<body>'` does both jobs: it "adds Content-Type: application/json and
Accept: application/json headers" and "implies POST unless a different method is set". The
`model` field accepts `jev-latest`, any other `jev-*` name, or the served model's name; the
answer always names the model that answered.

## Bodies from a file

Long JSON on a command line is fragile, and quoting rules differ between shells, Windows shells
in particular. Put the body in a file and let curl read it:

```bash
curl http://127.0.0.1:8017/v1/systemone -H 'Content-Type: application/json' \
  --data-binary @request.json
```

The manual describes `--data-binary` as posting data "exactly as specified with no extra
processing whatsoever", with `@` followed by a filename to read from and `@-` for stdin. The same
`request.json` can be answered without any server by `jev decide`, which reads the identical
body; that route is on [batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).
Writing the questions inside the file well is its own subject, covered by
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## With an API key

If the server was started with `JEV_API_KEY`, every call except `/health` needs the key:

```bash
curl http://127.0.0.1:8017/v1/systemone -H "Authorization: Bearer $JEV_API_KEY" \
  -H 'Content-Type: application/json' --data-binary @request.json
```

Without it the response is `401` with `WWW-Authenticate: Bearer`. Double quotes around the header
let the shell expand the variable; single quotes would send the literal text `$JEV_API_KEY`. Setup
and what stays open is on [securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md).

## Reading Server-Timing

`-D -` writes the received headers to stdout; `-s` keeps the progress meter out of the way, and
`-o /dev/null` drops the body when you only want the headers:

```bash
curl -s -D - -o /dev/null http://127.0.0.1:8017/v1/systemone \
  -H 'Content-Type: application/json' --data-binary @request.json -w 'wall: %{time_total}s\n'
```

Every response to `/v1/systemone` carries `Server-Timing: inference;dur=..., total;dur=...`, in
milliseconds: `inference` is the model's work, `total` is everything inside the engine,
including any wait for an earlier request, because the engine answers one decision at a time.
`%{time_total}` is curl's wall-clock time for the whole transfer, in seconds. The gap between
the two is the HTTP layer and the connection, which on `127.0.0.1` should be small and over a
network is not. For honest numbers, repeat the call, discard the first runs and take the median
and p90, as described on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md). On the
reference laptop the README gives 54 ms for a 30-token request and 220 ms for 190 tokens.

## /health and /v1/models

```bash
curl -s http://127.0.0.1:8017/health
curl -s http://127.0.0.1:8017/v1/models -H "Authorization: Bearer $JEV_API_KEY"
```

`/health` returns `{"status": "ready", ...}` once the model is loaded, with the served model's
name and engine metadata such as the model file's sha256 and the llama.cpp release; it never
needs a key. Before the model is loaded the port does not accept connections at all, so in a
start-up script, loop on `/health` until it answers. `/v1/models` lists the served model and
its `jev-latest` alias. The `Authorization` header is only needed when a key is set.

## A 422, on purpose

Send a model name the server does not serve:

```bash
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:8017/v1/systemone --json '{
  "model": "my-model", "state": "test",
  "questions": {"q": {"type": "noul", "instructions": "Is this a test?"}}}'
```

The status is `422` and the body has the shape FastAPI uses for validation errors, with `loc`
pointing at the field. For this request `loc` is `["body", "model"]` and the message says that
the server answers as its served model and accepts any `jev-*` alias. Other requests that get a
`422`: a `choice` or `score` question (only `noul` is answered), an unknown or misspelt field,
an empty state, or a text longer than the context limit.

In scripts, `--fail-with-body` makes curl return error 22 on HTTP 400 and above while still
showing the body, so a shell `&&` chain stops on a `422` and you can still read why. Add `-S`
with `-s` to see curl's own error message when a connection fails.

## Short answers to the questions that lead here

**How do I POST JSON with curl?** `curl URL -H 'Content-Type: application/json' -d '<json>'`,
or `curl URL --json '<json>'` with curl 7.82.0 or later.

**How do I send a JSON file with curl?** `--data-binary @file.json` with the Content-Type
header; `@` followed by a filename tells curl to read the data from that file.

**How do I see response headers with curl?** `-D -` prints them to stdout; `-i` includes them
in the output before the body.

**Why does the server reject my curl request with 422?** Read `loc` in the body: usually the
model name, a misspelt field or a question type other than `noul`.

**Why does my request fail with 401?** The server was started with `JEV_API_KEY`; add
`-H "Authorization: Bearer <key>"`.

**See also:** [ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md),
[a Python client for local LLM decisions](python-client-for-local-llm-decisions.md) and
[calling a local LLM decision server from JavaScript](javascript-fetch-for-local-llm-decisions.md).

## Sources

- The Quickstart request and answer and the latencies: the [jev README](https://github.com/feder-cr/jev).
- Endpoints, `Server-Timing` format, the 401 and 422 responses and the unknown-model message:
  read from `src/jev/api/app.py`, `src/jev/api/translate.py` and `src/jev/api/wire.py`.
- [curl manual](https://curl.se/docs/manpage.html) (`-d`, `--json`, `--data-binary`, `-H`,
  `-D`, `-i`, `-s`, `-S`, `-w`, `--fail-with-body`), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The first command on this page is the one in the README, and it is still the best
first test.*
