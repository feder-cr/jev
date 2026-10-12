---
title: "An open-source alternative to Microsoft-Decision-1"
description: "What Microsoft-Decision-1 is, by Microsoft's own pages, what jevos is, and what an open decision model on your own CPU changes and does not."
parent: "Comparisons"
nav_order: 14
---

# An open-source alternative to Microsoft-Decision-1

**jevos is an open-source (MIT) decision model that does the same kind of job as
Microsoft-Decision-1, but on your own CPU, with the weights published for anyone to download.**
Both read a text, take yes/no, multiple-choice or score questions with a fixed set of allowed
answers, and return a probability per answer instead of generated text. Microsoft-Decision-1,
announced by Microsoft on 2026-10-09, is reached through a deployment in Microsoft Foundry or
through OpenRouter and billed per input token; jevos is one binary and a model folder that you
run yourself. We know of no measurement of the two against each other, so this page compares
what each one is, not which is faster or more accurate.

We build jevos. We are not affiliated with Microsoft.

The real choice is where the text goes. A hosted model sends every text to someone else's data
center and adds a network round trip to every decision; a local one keeps the text on the
machine and works offline. Those properties hold whatever a benchmark says.

This page is what Microsoft says its model is, how jevos lines up with it, what running locally
changes, what jevos does not have, and how to choose.

## What is Microsoft-Decision-1?

Microsoft calls it "our new model for fast decision-scoring". This section is Microsoft's own
description:

- **What it returns.** "When given a fixed set of answer options, Microsoft-Decision-1 provides
  a calibrated probability score for each option." It "doesn't generate a free-form response or
  written rationale."
- **Question types.** `noul` (a probability from 0 through 1), `choice` (one option and a
  probability for each) and `score` (a value on an ordered scale and a probability per level),
  asked about a `state` that "can be text or JSON".
- **Where it runs.** In a Microsoft Foundry project, as a `DataZoneStandard` deployment in
  selected regions or a `GlobalStandard` one, and through OpenRouter. Microsoft's Foundry post
  says it is in public preview.
- **Price.** "Input tokens cost $0.042 USD per million tokens. Output tokens are free."
- **Limits Microsoft lists.** Scores "can change based on how you phrase or order questions and
  options"; "Calibration is strongest on familiar task types"; for consequential decisions about
  people, "Don't use it as the sole decision-maker."

Microsoft also reports its own benchmark results, for example "the highest accuracy in our
36-benchmark comparison", measured against models it chose. None of the four Microsoft pages we
read offers the weights for download: the way in is a deployment or an API call.

## How does jevos line up with it?

The request shapes are close. Microsoft's documentation says its "request pattern is similar to
a system-one API", and jevos speaks TypeSafe Jev's wire format at `POST /v1/systemone`. From
Microsoft's pages and our README:

| | Microsoft-Decision-1 | jevos-v4 |
|---|---|---|
| Who runs it | Microsoft, in Foundry or via OpenRouter | you, on your machine |
| Weights | not offered on the pages we read | MIT, on GitHub and Hugging Face |
| Hardware | Microsoft's | your CPU, no GPU, about 1 GB of memory |
| Question types | `noul`, `choice`, `score` | `noul`, `choice`, `score` (scores early) |
| `criteria` on a yes/no | used for borderline cases | checked, not read |
| Authentication | Microsoft Entra ID or `api-key` header | none, or a Bearer key with `JEV_API_KEY` |
| `model` in the request | your deployment name | `jev-latest` or the served model's name |
| Languages, context | not stated on the pages we read | English, 8,192 tokens |
| Price | per input token, output free | free, on your hardware |

The `criteria` row is the one to watch. Microsoft suggests defining true and false there to make
borderline yes/no questions more precise; jevos accepts the field and does not read it, so it
belongs in `instructions`, as on
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).
The model name and auth header differ too; we have not run Microsoft's sample code on jevos.
The step-by-step switch, written for TypeSafe's Jev, is on
[an open-source alternative to Jev](open-source-alternative-to-jev.md).

## What does a local decision model change?

**The text stays on the machine.** jevos listens on 127.0.0.1:8017 and needs no network to
answer. Microsoft's `DataZoneStandard` "keeps inference processing within that data zone"; that
narrows where the text goes, but it still leaves your network.

**The network floor goes away.** Microsoft advises creating the Foundry resource "in a region
close to your application and users" to minimize network latency, because every hosted call pays
a round trip before the model starts; [why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md)
works through it. This is about network hops, not speed: we have not timed Microsoft-Decision-1.

**The cost changes shape.** A per-token price grows with volume; a local model costs the same
for a thousand questions or a million, and the limit becomes CPU time.

**It works offline and stays put.** A local model answers in CI or on a machine with no route
out ([offline AI for decisions](offline-ai-for-decisions.md)). `/health` reports the SHA-256 of
each model file, so a log line shows which files made a decision.

## What does jevos not have?

Being straight about the limits:

- **No measurement against Microsoft-Decision-1.** We have not run one and know of no published
  one.
- **A hosted decision model can be more accurate.** On the six tasks in our README, TypeSafe's
  hosted Jev scored higher than jevos-v4 on every one, for example 0.69 against 0.50 on fraud
  points ([the full table](jevos-vs-jev-vs-laya.md)). That says nothing about
  Microsoft-Decision-1; it says a local model has to be measured on your cases, not assumed equal.
- **English only, 8,192 tokens of context, and early scores:** the most probable level is right
  on 58.5% of held-out score questions, 86% within one level.
- **You operate it.** Uptime and scaling are yours; Microsoft's `GlobalStandard` gives "access to
  global capacity", jevos has the threads of one machine.

## Which one should you use?

Pick **Microsoft-Decision-1** if your stack already lives in Azure, if you want capacity someone
else manages, or if your texts are not in English (check first: the pages we read do not list
languages).

Pick **jevos** if the text must not leave the machine, if a network round trip hurts the loop the
decision sits in, if you need it offline, or if you want the weights in hand.

Either way, test on your own labelled cases. Microsoft says the same: "Validate the model on data
that's representative of your use case." Since the question types match, one test set can be
asked of both, and [a model cascade](model-cascade-small-model-first.md) can keep confident
answers local and send the doubtful middle to a hosted model.

## Short answers to the questions that lead here

**Is there an open-source alternative to Microsoft-Decision-1?** jevos is one: an MIT-licensed
decision model that answers yes/no, choice and score questions with probabilities on a CPU. It
has not been measured against Microsoft's model.

**Can I download Microsoft-Decision-1's weights?** None of the Microsoft pages we read offers
them; they describe a Foundry deployment or OpenRouter. jevos's weights are on GitHub and
Hugging Face.

**Is jevos faster or more accurate than Microsoft-Decision-1?** No one we know of has measured
it. A local call has no network round trip, and on our six tasks the hosted Jev was more accurate
than jevos-v4.

**Does Microsoft-Decision-1 use the same request format as jevos?** The field names in
Microsoft's documentation (`state`, `questions`, `noul`, `choice`, `score`, `criteria`) are the
ones jevos reads. The model name, the authentication and `criteria` on yes/no questions differ.

**See also:** [what is a decision model in AI?](what-is-a-decision-model.md),
[local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md) and
[self-hosted AI for decisions](self-hosted-ai-for-decisions.md).

## Sources

- jevos facts, the six-task table and the score figures: the
  [jev README](https://github.com/feder-cr/jev); the accuracy numbers are our own measurements.
- Microsoft's description, price, benchmark claim and OpenRouter:
  [Introducing Microsoft-Decision-1](https://commandline.microsoft.com/microsoft-decision-1-model-foundry/),
  Command Line blog, dated 2026-10-09, fetched 2026-10-12.
- Request fields, deployments, limitations and advice:
  [Deploy and use Microsoft-Decision-1 in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision),
  Microsoft Learn, fetched 2026-10-12.
- Public preview:
  [Introducing Microsoft-Decision-1 in Microsoft Foundry](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/introducing-microsoft-decision-1-in-microsoft-foundry-for-decision-and-classific/4562742),
  Microsoft Tech Community, fetched 2026-10-12.
- No measurement of jevos against Microsoft-Decision-1 exists, ours or any we know of.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose repository calls jevos an
open-source alternative to Jev and Microsoft-Decision-1; here it is compared on what it is.*
