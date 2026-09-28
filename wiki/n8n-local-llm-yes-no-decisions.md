---
title: "Local LLM yes/no decisions in n8n"
description: "Use a local yes/no LLM in n8n: an HTTP Request node posting to jev serve, an If node on P(yes), a review band, auth, and Docker networking."
parent: "Integrations"
nav_order: 3
---

# Local LLM yes/no decisions in n8n

**In n8n a local yes/no decision is two nodes: an HTTP Request node that POSTs the text and the
questions to `jev serve` at `/v1/systemone`, and an If node that compares
`answers.<name>.noul` with a threshold.** The HTTP Request node returns the response body by
default, so the next node reads the probability as `{{ $json.answers.refund.noul }}` and the If
node's Number comparison "is greater than" sends the item down the true or the false branch.
Both n8n and the decision server can run on the same machine, so the text never leaves it.

What makes this better than asking a chat model inside the workflow is that the output is
already a number. There is no reply to parse, no "Yes." versus "yes" versus "Yes, because...",
and the threshold is a field in the If node that anyone can see and change.

This page is the HTTP Request node settings, the If node and a three-way review band, auth,
errors, and the networking catch when n8n runs in Docker. The configurations are minimal
sketches to adapt; field names are from the n8n docs as fetched on 2026-09-29.

## Start the decision server next to n8n

Download `jevos-q4_k_m.gguf` from the [release](https://github.com/feder-cr/jev/releases/tag/jevos)
and, from a clone of the repo:

```bash
uv sync
uv run jev download --only runtime
uv run jev serve --gguf jevos-q4_k_m.gguf --device cpu --threads 8
```

`--threads` should match the cores you can spare. n8n on the same box also needs CPU, so leave
it some; the README's advice is "set it to your core count, fewer if other heavy apps are
running". The server listens on `127.0.0.1:8017` and takes about 1.2 GB of memory with the
model loaded.

## The HTTP Request node

The quickest route is the node's **Import cURL** feature, which the n8n docs describe for
exactly this case: paste the README's curl command and the node is filled in. Then adjust:

- **Method**: `POST`. **URL**: `http://127.0.0.1:8017/v1/systemone`.
- **Send Body**, with **Using JSON**. To use values from the incoming item, n8n's common-issues
  page says to wrap the entire JSON in double curly brackets, which makes it an expression:

```
{{
  {
    "model": "jev-latest",
    "state": { "subject": $json.subject, "message": $json.message },
    "questions": {
      "refund": { "type": "noul", "instructions": "Does the customer ask for their money back?" },
      "angry": { "type": "noul", "instructions": "Is the customer angry?" }
    }
  }
}}
```

- **Options, Timeout**: set it. The n8n docs define it as how long the node waits for response
  headers. The server answers one decision at a time, so a burst of executions queues up.

Put all the questions you have about one text in this one node. The state is read once, and on
the reference laptop three questions take about 165 ms together against 103 ms for one alone. A
separate HTTP Request node per question reads the text again each time. Sending `state` as a
JSON object with readable field names, as above, is covered on
[sending JSON as the text: designing the state](designing-the-state-as-json.md).

## The If node, and a band for a person

An If node with a Number condition, `{{ $json.answers.refund.noul }}` "is greater than" `0.5`,
splits the workflow in two. For anything with a cost, split it in three instead:

1. If `noul` is greater than or equal to 0.9, act automatically (the true branch).
2. On the false branch, a second If node: `noul` is less than or equal to 0.1, act on the no.
3. Everything in between goes to a person, for example as a message in the team's channel.

The numbers 0.9 and 0.1 are placeholders, not a recommendation. Where to put them depends on
what a wrong yes costs you and on your own labelled cases; the reasoning is on
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md). Keep the
band honest about the model's lean: on our 999-question set wrong answers were 152 "said yes, was
no" against 91 the other way, mostly on arithmetic and dates. If your question needs a sum or a
date comparison, compare the raw fields in the workflow itself, for example with an If node, and ask the model only
what has to be read from the text.

## Auth, errors and timing

- **API key.** If the server was started with `JEV_API_KEY` set, every call except `/health`
  needs `Authorization: Bearer <key>`. In n8n, store it as a credential rather than in the node:
  Header Auth is one of the generic credential types the docs list. Details are on
  [securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md).
- **422.** A request the server cannot answer, such as a `choice` question, an unknown field or
  a model name that is not `jev-*`, comes back as `422` with a `detail` list. By default the node
  "returns success only when the response returns with a 2xx code", so the execution fails,
  which is usually right. Turn on **Never Error** only if you route errors yourself.
- **Server-Timing.** Every answer carries a `Server-Timing` header with the inference time.
  The node returns only the body unless you turn on **Include Response Headers and Status**.

## When n8n runs in Docker

`jev serve` listens on `127.0.0.1` by default, and inside a container `127.0.0.1` is the
container itself. n8n's own common-issues page for the HTTP Request node covers the resulting
`ECONNREFUSED`: on Docker Desktop use `http://host.docker.internal:<port>`, on Linux pass
`--add-host=host.docker.internal:host-gateway` (or `extra_hosts` in compose), and between
containers use the service name as the hostname.

A server bound to 127.0.0.1 on the host may still not accept connections that arrive through
the Docker gateway, depending on your setup. If it does not, start `jev serve` with `--host` set
to an address the container can reach, set `JEV_API_KEY` when you do, and make sure the port is
not open to the wider network.

## Being straight about the fit

n8n is a good home for this when the decision is one step in a workflow that already exists:
a form arrives, a ticket is created, a message is routed. It is not the tool for scoring a
hundred thousand stored records; a script or
[batch decisions from files with jev decide](batch-decisions-with-jev-decide.md) is simpler for
that. The model reads English only and answers yes/no questions only; a workflow step that needs
generated text, a summary or a reply, still needs a generative model. The same HTTP call from a
home automation hub is on [Home Assistant automations with local LLM decisions](home-assistant-local-llm-decisions.md).

## Short answers to the questions that lead here

**Can n8n use a local LLM without a cloud API?** Yes. Point an HTTP Request node at a server on
the same machine or network; nothing goes to a third party.

**Is there an n8n node for jevos?** No dedicated node. The HTTP Request node is enough, and
Import cURL fills it from the README example.

**How do I branch on the answer?** An If node with a Number condition on
`{{ $json.answers.<name>.noul }}`.

**Why does n8n get connection refused?** Usually because n8n runs in a container and
`127.0.0.1` is the container. See the Docker section above.

**Does self-hosted n8n need a GPU for this?** No. The decision server is built for the CPU.

**See also:** [ask a local LLM a yes/no question and get P(yes)](ask-a-local-llm-yes-no-questions.md),
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md)
and [Home Assistant automations with local LLM decisions](home-assistant-local-llm-decisions.md).

## Sources

- Server command, defaults, endpoints, `JEV_API_KEY`, `422` and `Server-Timing`: the
  [jev README](https://github.com/feder-cr/jev) and `src/jev/cli.py`, `src/jev/api/app.py`.
- Latencies, memory and the 152 to 91 error split: the README and our 999-question test set.
- [n8n HTTP Request node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)
  and its [common issues](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/common-issues.md),
  fetched 2026-09-29.
- [n8n If node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/) and
  [n8n expressions](https://docs.n8n.io/build/work-with-data/transform-data/expressions-for-data-transformation.md),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. In a workflow tool the threshold ends up as a visible field, which is where it
belongs.*
