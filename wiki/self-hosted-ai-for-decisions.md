---
title: "Self-hosted AI for decisions"
description: "What self-hosting a yes/no decision model involves: one model file, a prebuilt runtime, a port, and the operations work a hosted API used to do for you."
parent: "Local and private AI"
nav_order: 1
---

# Self-hosted AI for decisions

**Self-hosting a decision model means running three things you control: a model file, a
runtime that executes it, and a server on a port that your application calls.** For jevos that
is the model folder from `jevos-v2-openvino-int8.zip`, the prebuilt `jev` binary for your
platform with OpenVINO's libraries beside it, and `jev serve` listening on `127.0.0.1:8017`.
There is no GPU to provision and no account to open. What you take on instead is the
work a hosted API did quietly: knowing which model answered, updating it deliberately, keeping
the port private, and noticing when it is down.

The non-obvious part is that the hard problem of self-hosting a large chat model, finding
hardware that can run it, mostly disappears for a small decision model. What remains is
ordinary service operations, and the one habit worth building early is identifying the model by
its file hash rather than by its name.

This page is what you install, how to run it as a service, how to know which model is
answering, how to update it, what stays your job, and when a hosted API is still the better
choice.

## What do you actually install?

Three pieces, all from the
[release page](https://github.com/feder-cr/jev/releases/tag/jevos-v2), with `SHA256SUMS.txt`
next to them:

1. The `jev` folder, from `jev-linux-x64.tar.gz`, `jev-windows-x64.zip` or
   `jev-macos-arm64.tar.gz`: the binary, OpenVINO's libraries and the licenses. Nothing is
   compiled, and there is no Python to install.
2. The model, `jevos-v2-openvino-int8.zip`, unpacked into the `jev` folder as `jev/model`.
3. The server, started from the `jev` folder (`.\jev.exe serve` on Windows):

```bash
./jev serve
```

`--threads` defaults to all logical CPUs; set it lower if other heavy programs run on the same
machine. `--host` and `--port` change where it listens, and `--model-dir` points at a model
folder elsewhere. If you
do not need a server at all, `jev decide` answers one request file and exits, which suits batch
jobs; see [batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).

## Running it as a service

The server is one process holding one model. Treat it like any other internal HTTP dependency.

- **Readiness.** `GET /health` returns `{"status": "ready", ...}` once the model is loaded.
  Point your service manager's health check, or your load balancer, at it, and do not send
  traffic before it answers.
- **Timing.** Every response carries a `Server-Timing` header with the inference time and the
  total. Log it next to your own wall-clock measurement, so you can tell the model's cost from
  your network's.
- **Capacity.** The measured figures come from one laptop, an Intel Core Ultra 7 255H with 16
  threads: 26 ms for a short request and 112 ms for a 191-token one read from scratch, and
  8.7 requests per second from one client, 10.1 from eight. Your hardware and inputs will
  differ; measure them as described on [measuring LLM latency](measuring-llm-latency-median-and-p90.md).
- **Restarts.** Loading takes time and memory. A supervisor that restarts the process on crash
  and waits for `/health` before routing to it is enough for most setups.

## How do you know which model is answering?

By hash. Answers name the served model, `jevos-v2`, but a name is not an identity. Check the
release archives you unpack against `SHA256SUMS.txt`, and record those hashes with every
deployment: two servers unpacked from the same archives run the same binary on the same model.

This matters more than it seems. A file renamed on disk, a copy that did not finish, or a
different quantization behind the same file name all look identical in a config file and give
different answers. Recording the hashes in every decision log turns "which model made this
decision in March?" into a lookup; [logging LLM decisions for audit](logging-llm-decisions-for-audit.md)
shows what else to keep with it.

## Updating deliberately

Nothing updates itself. A new model means a new model folder, and a new runtime means a new
`jev` release. That is the property you want from a decision service, where silent changes
of behaviour are the expensive kind. A reasonable update routine:

1. Download the new file and check it against `SHA256SUMS.txt`.
2. Run your own labelled test set against old and new side by side, per kind of question; a
   hundred real cases is a useful start, as on
   [building a yes/no test set](building-a-yes-no-test-set.md).
3. Re-check your thresholds, because a new model's probabilities are not the old model's.
4. Switch, and keep the old file until the logs show the new one behaves.

The runtime works the same way. OpenVINO's libraries ship inside the `jev` folder, so the
runtime changes only when you unpack a new release, and its hash is part of what you record;
the reasons for pinning a runtime are on
[using llama.cpp prebuilt binaries](llama-cpp-prebuilt-binaries.md).

## What stays your job

Self-hosting moves the model onto your machine and the responsibilities with it.

- **Access.** The server listens on `127.0.0.1` by default, so only the same machine can reach
  it. If you bind it to another interface, set `JEV_API_KEY` when you start it: every call
  except `/health` then needs `Authorization: Bearer <key>`, and a missing or wrong key gets a
  401. The server does not terminate TLS; put a reverse proxy in front if the traffic leaves the
  host. Details on [securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md).
- **Data.** The text never leaves the machine, but your application, your proxy and your logs
  can still keep it. Self-hosting does not decide retention for you.
- **Quality.** A hosted provider may improve its model under you; a self-hosted file does not
  change. That is stability, and it is also the reason to re-measure when your inputs drift.

## When a hosted API is still the better choice

Being straight about the limit: jevos answers yes/no and multiple-choice questions in English
and, early, scores (54% on held-out score questions). On 2,000 yes/no questions about business
policies none of the models was tuned on, the hosted Jev was right 0.927 of the time against
0.810 for jevos. If the decision needs that accuracy, other languages, or scores,
the hosted model is the right tool, and because the wire format is the same, moving between
the two is a base URL change. The broader trade-off is on
[local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md).

## Short answers to the questions that lead here

**What does self-hosted AI mean?** Running the model on hardware you control instead of calling
someone else's API. For a decision model that is a file, a runtime and a local server.

**Do I need a GPU to self-host?** Not for jevos. jev runs on the CPU only: x86-64 with AVX2, or
Apple silicon.

**How do I update a self-hosted model safely?** Verify the new file's hash, test it against
your own labelled cases, re-check thresholds, then switch, keeping the old file.

**Can other machines call it?** Only if you bind it to a reachable interface. Set `JEV_API_KEY`
first, and add a reverse proxy for TLS.

**Is it free?** The code is MIT and the model file is a download; the cost is your hardware and
your time running it.

**See also:** [offline AI for decisions](offline-ai-for-decisions.md),
[on-premise LLM for business decisions](on-premise-llm-for-business-decisions.md) and
[ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Sources

- Commands, options, endpoints and release files: the [jev README](https://github.com/feder-cr/jev).
- Latency, throughput and the 2,000-question comparison: our measurements, reported in the README.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a decision server that is one binary
beside one model folder, both known by the hashes you record.*
