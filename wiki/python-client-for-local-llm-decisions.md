---
title: "A Python client for local LLM decisions"
description: "A small Python helper for a local yes/no LLM server: one requests Session, timeouts, retries that are safe, and what to do with a 422 or a 401."
parent: "Integrations"
nav_order: 1
---

# A Python client for local LLM decisions

**A good Python client for a local decision server is about twenty lines: one `requests.Session`
reused for every call, an explicit timeout, retries only for connection failures, and a helper
that returns the `noul` of each question as a float.** The server is `jev serve` on
`127.0.0.1:8017`, the call is `POST /v1/systemone`, and the only answer type is `noul`, the
probability that the answer is yes. Everything else in the client is about failing loudly: a
`422` means the request itself is wrong and must not be retried, a `401` means the key is
missing.

The README's four-line example is enough to try the model. It is not what you want in a service
that makes thousands of calls, because `requests` has no timeout by default and opens a new
connection per call unless you use a session. Both are cheap to fix, and on a server that
answers in 54 to 220 ms on a laptop CPU the connection setup is not a rounding error.

This page is the helper, the three settings that matter (session, timeout, retries), how to
read the errors the server returns, and what the server does when several threads call it at
once. The snippets are minimal sketches to adapt, not a published library; they use only the
documented API.

## The helper

```python
import os
import requests

URL = os.environ.get("JEV_URL", "http://127.0.0.1:8017")
session = requests.Session()
if os.environ.get("JEV_API_KEY"):
    session.headers["Authorization"] = f"Bearer {os.environ['JEV_API_KEY']}"

def decide(state, questions, timeout=(3.05, 10)):
    """state: a string or a JSON-able dict/list. questions: {name: question text}."""
    body = {
        "model": "jev-latest",
        "state": state,
        "questions": {k: {"type": "noul", "instructions": q} for k, q in questions.items()},
    }
    r = session.post(f"{URL}/v1/systemone", json=body, timeout=timeout)
    if r.status_code == 422:
        raise ValueError(r.json()["detail"])
    r.raise_for_status()
    return {k: a["noul"] for k, a in r.json()["answers"].items()}
```

Called as `decide("I was charged twice for the same order.", {"billing": "Is this a billing
problem?"})`, this is the README's Quickstart request, for which the README shows `0.9`. The
helper keeps the question names you chose, so the result is a plain dict of floats you can
threshold. Ask every question you have about one text in one call: the text is read once and
the extra questions cost a fraction of the first (three questions about 165 ms against 103 ms
for one, on the reference laptop).

## Why a Session and why a timeout

The requests documentation is direct on both. A `Session` "will use urllib3's connection
pooling. So if you're making several requests to the same host, the underlying TCP connection
will be reused". And on timeouts: "By default, requests do not time out unless a timeout value
is set explicitly. Without a timeout, your code may hang for minutes or more."

A tuple sets the two timeouts separately: the connect timeout (the docs suggest a value slightly
larger than a multiple of 3) and the read timeout, which is the wait for the server's reply.
Size the read timeout from your own traffic, not from the laptop figures. Two things make a
reply slower than one inference:

- **Long texts.** On the reference CPU latency grows by about 1.1 ms per prompt token; how that
  adds up is on [why latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).
- **Queueing.** The engine holds a lock around each decision and runs model work on a single
  inference thread, so concurrent requests are answered one after another. Ten threads calling
  at once do not get ten parallel answers; the last one waits for the other nine. A thread pool
  in the client raises throughput only up to the point where the server is busy all the time.
  The difference between the two numbers is the subject of
  [throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).

## Retries that do not hide bugs

Requests itself "does not retry failed connections", and the documented way to add retries is a
`urllib3.util.Retry` mounted on the session through an `HTTPAdapter`. One detail matters for
this API: urllib3 by default retries only methods "considered to be idempotent", and POST is not
among them, so you must opt in:

```python
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

retries = Retry(total=3, backoff_factor=0.1,
                status_forcelist=[502, 503, 504], allowed_methods={"POST"})
session.mount("http://", HTTPAdapter(max_retries=retries))
```

Retrying a decision is safe in the sense that matters: the server stores nothing about a
request, so sending it twice changes no state. What you should not retry is a `4xx`. The
`status_forcelist` above covers the gateway errors a reverse proxy in front of the server might
return; the server's own `422` and `401` are left alone, because the same request will fail the
same way.

## Reading a 422 and a 401

The server answers a request it cannot handle with `422` and a body of the form
`{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`, the same shape FastAPI uses for
its own validation errors. From the code, the usual causes are:

- a `choice` or `score` question: only `noul` is answered on this server;
- a `model` that is neither a `jev-*` alias nor the served model's name;
- an unknown field, for example a misspelt `instructions`: requests reject fields they do not
  know, so a typo fails loudly instead of being ignored;
- an empty `state`, a `state` over 256 KB, or a text longer than the context limit (8,192 tokens
  per question by default).

`loc` points at the offending field, which is why the helper raises it as it is. A `401`
carries `WWW-Authenticate: Bearer` and appears only when the server was started with
`JEV_API_KEY`; setup is on [securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md).

## Waiting for the server at start-up

`jev serve` loads the model before it starts listening, so while it loads, the port refuses
connections, and once it answers, `GET /health` returns `{"status": "ready", ...}`. `/health`
needs no key. A worker that starts together with the server can poll it with a short timeout
and a sleep between attempts, and begin sending decisions only after the first `ready`. The same
endpoint reports the model file's sha256 and the llama.cpp release, which are worth logging next
to every decision; [logging LLM decisions for audit](logging-llm-decisions-for-audit.md) covers
what else to keep.

## Being straight about the limits of the client

The helper does nothing about the model's own weaknesses. It returns a probability, and what
that probability is worth depends on the question: on our 999-question test it was right 0.954
of the time on facts stated in the text and 0.584 on arithmetic. A threshold of 0.5 is the
neutral starting point; [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md)
is the next step. The model reads English only.

## Short answers to the questions that lead here

**Is there an official Python SDK for jevos?** No separate one. The server speaks TypeSafe's
Jev wire format, so code written for Jev's SDK works unchanged for yes/no questions; otherwise a
plain `requests` call is all it takes.

**Should I use async?** Only if your application is already async. The server answers one
decision at a time, so concurrency on the client side does not make one server faster.

**What timeout should I set?** A connect timeout of a few seconds and a read timeout sized from
your longest texts and your peak concurrency, measured on your machine.

**Why do I get 422 on a question that looks fine?** Check `loc` in the body: a misspelt field,
a `choice` question, or a model name that is not `jev-*` are the common causes.

**Can I send a dict as the state?** Yes. `state` accepts a string, an object or an array.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[calling a local LLM decision server from JavaScript](javascript-fetch-for-local-llm-decisions.md)
and [curl examples for a local LLM decision API](curl-examples-for-a-local-llm-api.md).

## Sources

- Endpoints, status codes, error shape, the lock and single inference thread, the 256 KB state
  limit and the default context: read from `src/jev/api/app.py`, `src/jev/api/wire.py`,
  `src/jev/api/translate.py`, `src/jev/engine/engine.py`, `src/jev/engine/schema.py` and
  `src/jev/cli.py` of [jev](https://github.com/feder-cr/jev).
- Latencies and the billing example: the [jev README](https://github.com/feder-cr/jev) (Intel
  Core Ultra 7 255H, 16 threads). Accuracy by kind: our 999-question test set, `jevos-q4_k_m`.
- Sessions, timeouts and the retry example:
  [Requests, Advanced Usage](https://requests.readthedocs.io/en/latest/user/advanced/), fetched
  2026-09-29.
- Default retried methods: [urllib3 `Retry`](https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The helper is short on purpose: the server has one endpoint and one answer type.*
