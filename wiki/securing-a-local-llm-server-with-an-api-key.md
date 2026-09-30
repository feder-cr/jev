---
title: "Securing a local LLM server with an API key"
description: "Protect jev serve: JEV_API_KEY for Bearer auth, what stays open without a key, the 127.0.0.1 default, and a TLS reverse proxy before exposing it."
parent: "Integrations"
nav_order: 9
---

# Securing a local LLM server with an API key

**Set the `JEV_API_KEY` environment variable when you start `jev serve`, and every call except
`GET /health` then needs `Authorization: Bearer <key>`; anything else gets a `401`.** Keep the
default bind address, `127.0.0.1`, unless another machine has to reach the server, and if one
does, put a reverse proxy with TLS in front, because `jev serve` itself speaks plain HTTP and the
key would otherwise cross the network in clear text.

Without a key, the server trusts anyone who can reach its port. On `127.0.0.1` that means
programs on the same machine, which is often fine. The moment you pass `--host` to listen on a
network address, the key stops being optional.

This page is how to turn the key on and check it, what remains reachable without it, the bind
address, TLS through a proxy, and what the key does not protect against. The commands are
minimal sketches to adapt; the behaviour described is read from jev's source.

## Turning the key on

The variable is read once, when the server starts:

```bash
export JEV_API_KEY="$(openssl rand -hex 32)"
./jev serve
```

```powershell
$env:JEV_API_KEY = "<a long random string>"
.\jev.exe serve
```

The start-up line on stderr says which mode you are in: it ends with `(Bearer auth)` when a key
is set and `(no auth)` when it is not. Check that line after every deployment change; it is the
fastest way to catch a service manager that did not pass the variable through. An empty value
counts as no key.

Clients send the header on every request:

```bash
curl http://127.0.0.1:8017/v1/models -H "Authorization: Bearer $JEV_API_KEY"
```

A missing or wrong key gets `401` with `WWW-Authenticate: Bearer` and the detail "Missing or
invalid API key". The server compares the whole header, `Bearer ` plus the key. This is the same Bearer
scheme the hosted Jev API uses, which is why clients written for it work unchanged; how to
switch such a client is on [an open-source alternative to Jev](open-source-alternative-to-jev.md).

## What stays reachable without the key

Every call except `GET /health` checks the key. With a key set:

| Path | Needs the key | What it exposes |
|---|---|---|
| `POST /v1/systemone` | yes | the decisions |
| `GET /v1/models` | yes | served model name and the `jev-latest` alias |
| `GET /health` | no, by design | readiness and the model name |

`/health` stays open so that load balancers and process supervisors can check readiness without
a secret. It tells a caller which model you run, not what you asked or were answered. If even
that is too much on your network, block the path at the proxy.

## The bind address

`--host` defaults to `127.0.0.1` and `--port` to `8017`. On the loopback address the server is
unreachable from other machines whatever the key says, which is the safest setting and the right
one when the client, a script, n8n or Home Assistant, runs on the same machine. Clients in a
container are the usual reason to change it; the details for that case are on
[local LLM yes/no decisions in n8n](n8n-local-llm-yes-no-decisions.md).

If you listen on a network address, do three things together: set the key, restrict the port to
the machines that need it with your firewall, and add TLS.

## TLS with a reverse proxy

`jev serve` has no certificate options, so it serves HTTP only. For anything that leaves
the machine, terminate TLS in a reverse proxy and keep jev on `127.0.0.1` behind it. With Caddy,
whose documentation says it "will serve your proxy over HTTPS automatically and by default if it
knows the hostname", a two-line Caddyfile is enough:

```
decisions.example.com
reverse_proxy 127.0.0.1:8017
```

Per Caddy's docs, a public domain needs DNS pointing at the machine and ports 80 and 443 open to
get a publicly trusted certificate; `.localhost` names get self-signed ones. Any other proxy you
already run works the same way. The proxy is also where to add what jev does not have: rate
limits, IP allow-lists and access logs. The operational side of running your own model server is
on [self-hosted AI for decisions](self-hosted-ai-for-decisions.md).

## What one key does not do

Be clear about the scope:

- **One key, one role.** There are no users, scopes or per-client keys. Anyone with the key can
  ask anything. Changing it means restarting the server with a new value.
- **No rate limiting.** The server runs one model on the CPU: small requests arriving together
  are read in one model call, but throughput stays around 10 requests per second on the
  reference laptop, so a single client sending a flood keeps everyone else waiting. A request is bounded (the state at 256 KB, at most 1,024
  questions, the context at 8,192 tokens by default), but the number of requests is not.
- **Not a data policy.** The key controls who can call the server; it says nothing about who can
  read your logs or the texts your application stores. That part is on
  [a private LLM for text classification](private-llm-for-text-classification.md).
- **Never in a browser.** A key in front-end code is public. Call the server from your backend;
  [calling a local LLM decision server from JavaScript](javascript-fetch-for-local-llm-decisions.md)
  explains why the browser cannot call it cross-origin anyway.

## Short answers to the questions that lead here

**How do I add an API key to jev serve?** Set `JEV_API_KEY` in the environment before starting
it. Clients then send `Authorization: Bearer <key>`.

**Why does /health work without the key?** On purpose: readiness checks should not need a
secret. It reports readiness and the model name, not decisions.

**Does jev serve support HTTPS?** Not by itself. Put a reverse proxy with TLS in front and keep
the server on `127.0.0.1`.

**Is it safe to expose on the internet?** Not on its own. With a key, TLS, a firewall rule and
rate limits in a proxy it is a normal internal service; without them it is not.

**See also:** [curl examples for a local LLM decision API](curl-examples-for-a-local-llm-api.md),
[on-premise LLM for business decisions](on-premise-llm-for-business-decisions.md) and
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## Sources

- `JEV_API_KEY`, the start-up line, the 401 response, the header comparison, which routes check
  the key, the `--host`/`--port` defaults, plain HTTP and the request bounds: read from the
  source of [jev](https://github.com/feder-cr/jev). Throughput: our measurements on an Intel
  Core Ultra 7 255H laptop.
- [Caddy: reverse proxy quick-start](https://caddyserver.com/docs/quick-starts/reverse-proxy),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The start-up line prints "no auth" on purpose: it should be the first thing you
see.*
