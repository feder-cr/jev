---
title: "Calling a local LLM decision server from JavaScript"
description: "Call a local yes/no LLM server with fetch from Node.js or a browser: timeouts, response.ok, 422 errors, and why cross-origin browser calls are blocked."
parent: "Integrations"
nav_order: 2
---

# Calling a local LLM decision server from JavaScript

**From JavaScript you call a local decision server with a plain `fetch` POST of JSON to
`/v1/systemone` and read `answers.<name>.noul`, the probability of yes.** In Node.js, where the
global `fetch` is stable since v21.0.0, that is all there is to it, plus a timeout and a check of
`response.ok`, because `fetch` does not reject on HTTP errors. In the browser it works only
from a page served by the same origin as the server: the server sends no CORS headers,
so a page on another origin is blocked by the browser.

The CORS point is the one that costs people an afternoon. The same request that works from
curl or Node fails in the browser, and the error JavaScript sees says nothing useful about why.

This page is the Node.js version, error handling, the browser rule and the two ways around it,
and where the API key must never go. The snippets are minimal sketches to adapt, using only the
documented request and response fields.

## A decision from Node.js

The Node.js documentation lists the global `fetch` as added in v17.5.0 and v16.15.0 and no
longer experimental since v21.0.0. `AbortSignal.timeout` is there too, from v17.3.0 and v16.14.0.

```js
const JEV_URL = process.env.JEV_URL ?? "http://127.0.0.1:8017";

async function decide(state, questions, ms = 10000) {
  const body = {
    model: "jev-latest",
    state,
    questions: Object.fromEntries(
      Object.entries(questions).map(([k, q]) => [k, { type: "noul", instructions: q }])
    ),
  };
  const headers = { "Content-Type": "application/json" };
  if (process.env.JEV_API_KEY) headers.Authorization = `Bearer ${process.env.JEV_API_KEY}`;

  const res = await fetch(`${JEV_URL}/v1/systemone`, {
    method: "POST", headers, body: JSON.stringify(body), signal: AbortSignal.timeout(ms),
  });
  if (res.status === 422) throw new Error(JSON.stringify((await res.json()).detail));
  if (!res.ok) throw new Error(`jev: HTTP ${res.status}`);
  const { answers } = await res.json();
  return Object.fromEntries(Object.entries(answers).map(([k, a]) => [k, a.noul]));
}
```

`decide("I was charged twice for the same order.", { billing: "Is this a billing problem?" })`
is the README's Quickstart request (the README shows `0.9` for it). Put every question about one
text in the same call: the state is read once, so on the reference laptop three questions take
about 165 ms together against 103 ms for one alone. The request shape is described in full on
[ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md).

## Errors that fetch will not throw for you

MDN is explicit: "A `fetch()` promise only rejects when the request fails, for example, because
of a badly-formed request URL or a network error", and it does not reject on `404`, `504` and
the like. So the code checks the status itself. What each case means here:

- **Network error or connection refused.** The server is not up, or is still loading the model:
  `jev serve` opens its port only once the model is loaded. Poll `GET /health` until it returns
  `{"status": "ready", ...}`.
- **`TimeoutError`.** The signal from `AbortSignal.timeout` aborts with a `TimeoutError`
  `DOMException`, which MDN distinguishes from the `AbortError` of a user abort. The server
  answers one decision at a time, so a timeout under load usually means the queue is long, not
  that the model hangs.
- **`422`.** The body is `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`. Common
  causes: a `choice` or `score` question (only `noul` is answered), a model name that is not
  `jev-*` or the served model, a misspelt field (unknown fields are rejected), or a text over the
  context limit.
- **`401`.** The server was started with `JEV_API_KEY` and the header is missing or wrong.

Do not retry a `422` or a `401`; the same request fails the same way.

## The browser rule: same origin or nothing

A POST with `Content-Type: application/json` is not a "simple" request in the CORS sense, and a
request with an `Authorization` header is not either. MDN's guide lists both as triggers for a
preflight `OPTIONS` request, after which the server must answer with
`Access-Control-Allow-Origin` and the allowed headers. The jev server's FastAPI app adds no CORS
middleware, so none of those headers are sent, and per MDN the browser then blocks access to the
response and reports a CORS error that "for security reasons" JavaScript cannot inspect.

For your own front end, two designs work:

1. **Call jevos from your backend.** The browser talks to your server, your server calls
   `127.0.0.1:8017`. This is the normal design and keeps the decision server off the network.
2. **Put both behind one origin.** A reverse proxy serves your page and forwards `/v1/` to the
   decision server, so the browser sees one origin. This also gives you a place for TLS; see
   [securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md).

Adding CORS headers to the server is possible in your own fork, but a permissive setting would
let any page a user opens read answers from a server on their machine, which is what the browser
rule exists to prevent. If you do it, allow one named origin, not `*`.

## Where the API key must never go

Never ship `JEV_API_KEY` to a browser. Anything in front-end code is readable by whoever loads
the page, and the server has one key for all callers. Keep the key in the backend's environment,
as the Node sketch does, and let the browser authenticate to your backend in whatever way it
already does.

## Being straight about what JavaScript adds

Nothing about the model changes with the language. The same limits apply: English only, yes/no
questions only, and a probability whose reliability depends on the kind of question. On our
999-question set a small model leaned toward yes on arithmetic and dates, which is why
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md) says to
compute numbers in code, and in JavaScript that is one line.

## Short answers to the questions that lead here

**Which Node.js version do I need?** One with a global `fetch`: added in v17.5.0 and v16.15.0,
stable since v21.0.0, according to the Node.js docs.

**Why does my browser say CORS error when curl works?** curl does not enforce CORS; browsers do.
The server sends no CORS headers, so only same-origin pages can read its answers.

**Can I use axios instead of fetch?** Any HTTP client works: it is one JSON POST. The error
handling rules are the same.

**How do I set a timeout on fetch?** Pass `signal: AbortSignal.timeout(ms)` and catch
`TimeoutError`.

**Can a web page call the server with the API key?** It can, but it should not: the key would
be visible to every visitor.

**See also:** [a Python client for local LLM decisions](python-client-for-local-llm-decisions.md),
[curl examples for a local LLM decision API](curl-examples-for-a-local-llm-api.md) and
[a Slack bot that uses local LLM decisions](slack-bot-with-local-llm-decisions.md).

## Sources

- Request and response fields, 422 and 401 behaviour, the absence of CORS middleware, the
  one-at-a-time engine: read from `src/jev/api/app.py`,
  `src/jev/api/wire.py`, `src/jev/engine/engine.py` of
  [jev](https://github.com/feder-cr/jev).
- Latencies and the billing example: the [jev README](https://github.com/feder-cr/jev).
- [Node.js globals: fetch and AbortSignal.timeout](https://nodejs.org/api/globals.html), fetched
  2026-09-29.
- [MDN: Window.fetch()](https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch),
  [MDN: AbortSignal.timeout()](https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal/timeout_static)
  and [MDN: CORS guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The server sends no CORS headers, so the browser question is decided by where the
page is served from, not by the code.*
