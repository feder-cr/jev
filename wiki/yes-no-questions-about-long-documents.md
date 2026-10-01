---
title: "Yes/no questions about long documents"
description: "Yes/no questions about contracts, threads and reports with an 8,192-token context: what length costs, how to chunk, and how to combine the answers."
parent: "Question design"
nav_order: 11
---

# Yes/no questions about long documents

**If a document fits in 8,192 tokens together with each question, you can send it whole; if it
does not, or if speed matters, split it into chunks, ask the same questions of each chunk, and
combine the answers in code, usually with OR: the document says X if any chunk says X.**
Cost grows with every token the model reads, so a long document is also a slow one, and
chunking often pays before the limit does. The combination rule is where the design lives:
"Does the contract contain an auto-renewal clause?" is an OR over chunks, "Is the whole report
written in a neutral tone?" is an AND.

What chunking cannot do is answer a question whose evidence is spread across chunks. "Does the
termination date in section 9 come before the renewal date in section 3?" needs both sections
at once. For those, you either bring the pieces together in one request, or accept that this
is not a question for a small model.

This page is what length costs, when to send the whole document, how to chunk, how to combine,
and where the approach stops.

## How long is too long?

The context of jevos is 8,192 tokens by default, and it applies to each question's prompt on its
own: the `state` plus that one question. The questions of a request do not add up against it.
How many words that is depends on the text, so measure it: send a document with one short
question, and the `input_tokens` in the response's `usage` field is about what each prompt uses;
a dozen of your real documents tell you where you stand. With several questions, `input_tokens`
counts the state once plus every question, so it can pass 8,192 on a request that is accepted.
Shorter contracts, email threads and reports can fit whole; books and full policy manuals will
not.

The limit is not the whole story. Some models are known to use long inputs unevenly: Liu and
colleagues (2023) found that several language models answered best when the relevant
information was at the start or end of the input, and worse when it was in the middle, even
models built for long contexts. We have not measured this on jevos, so treat it as a reason to
test rather than as a known property. It is one more argument for chunks, where nothing is far
from an edge.

## What does length cost?

Every token is read before any question is answered. On the reference laptop (Intel Core Ultra
7 255H, 16 threads) we measured 26 ms for a request of about 30 tokens and 112 ms for one of
about 190, reading each text from scratch, about 0.5 ms per prompt token over that range. We
have not published measurements near the full context, and the cost per token of reading a long
input can grow with length, so do not multiply 0.5 ms by 8,000 and call it a benchmark. Measure your own
document sizes. The mechanics are on
[why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md)
and [prefill vs decode](prefill-vs-decode-llm-latency.md).

Questions are cheap next to the text. In the README example, three questions about one text
take about 66 ms against 49 ms for one alone, because the text is read once. So the rule for
long documents is: many questions per request, few tokens per request.

## Chunk the document

Split on the document's own structure where you can: sections of a contract, messages in a
thread, pages of a report. A clause cut in half is a clause neither chunk contains.

```json
{
  "model": "jev-latest",
  "state": {
    "document": "Service agreement between Example Ltd and the customer",
    "section": "7. Term and renewal",
    "text": "This agreement renews automatically for successive twelve-month periods unless either party gives written notice sixty days before the end of the current term."
  },
  "questions": {
    "auto_renewal": {"type": "noul", "instructions": "Does this section say the agreement renews automatically?"},
    "notice_period": {"type": "noul", "instructions": "Does this section state a notice period for cancelling?"}
  }
}
```

Three habits help:

- **Keep a little context in every chunk.** The document title and section heading, as fields
  of the state, tell the model what it is reading. Structured states are covered on
  [sending JSON as the text: designing the state](designing-the-state-as-json.md).
- **Overlap only if you cannot split on structure.** When cutting by length, repeat a sentence
  or two between chunks, so a condition at a boundary appears whole in one of them.
- **Ask about the chunk, not the document.** "Does this section say..." is true to what the model
  can see. "Does the contract say..." invites a guess about text it has not been shown.

## Combine the chunk answers

```python
import math

p = [chunk_answers[i]["auto_renewal"]["noul"] for i in range(len(chunks))]

any_chunk = max(p)                                    # OR: cautious
any_chunk_indep = 1 - math.prod(1 - x for x in p)     # OR: if chunks are independent
every_chunk = min(p)                                  # AND: e.g. "is every section neutral?"
```

`max` is the usual choice for "does the document contain": one clear chunk is enough, and it
does not inflate with the number of chunks. The independent-OR formula does inflate: twenty
chunks at 0.1 each combine to about 0.88, which reads as a yes built from twenty noes. Use it
only when each chunk is real, separate evidence. The general arithmetic is on
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

Keep the chunk that produced the maximum. It is the evidence, and it is what a person reviewing
the decision will want to read.

## Ask fewer chunks

The cheapest chunk is the one you never send. If a question is about renewal, a keyword search
for "renew", "term" and "notice" picks the few sections worth asking, and the model reads a
fraction of the document. This is ordinary retrieval, and a yes/no model is a good second stage
behind it: the search finds candidates, the model decides whether each one really says the
thing. A gate question per chunk, "Does this section discuss renewal at all?", can play the same
role, as on [ask whether the text says it at all](ask-whether-the-text-says-it.md).

## When this is the wrong tool

- **Questions that need the whole document at once**: comparing dates in two sections, checking
  that a total matches a list of items, summarising. Bring the parts into one request if they
  fit, compute in code if they are numbers, and otherwise use a larger model with a long context.
- **Arithmetic across a document.** Computation is the model's weakest kind of question even in
  a short text, as measured on [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).
- **Short-context models.** For comparison, the zero-shot model Laya that we measured has a
  512-token context, and it truncated long rule texts in our 2,000-question test.

## Short answers to the questions that lead here

**How long a document can jevos read?** 8,192 tokens for the text and each question, by default;
the limit is per question, not per request. The `input_tokens` of a request with one question
tells you about how much of it a document uses.

**How do I ask a yes/no question about a document longer than the context?** Split it into
chunks, ask each chunk, and combine with max for "does it contain" or min for "is it all".

**Why is my long document slow?** Every token is read before any question is answered. Send only
the sections the question needs.

**Can the model compare two parts of a long document?** Only if both parts are in the same
request. Across chunks, no.

**See also:** [contract clause detection with a local LLM](contract-clause-detection-with-a-local-llm.md),
[document classification with a local LLM](document-classification-with-a-local-llm.md) and
[RAG evaluation with yes/no questions](rag-evaluation-with-yes-no-questions.md).

## Sources

- 8,192-token context, the 26 ms and 112 ms latencies, the three-question timing, and Laya's
  512-token context: the [jev README](https://github.com/feder-cr/jev) and our measurements on
  the reference laptop.
- Nelson F. Liu et al., "Lost in the Middle: How Language Models Use Long Contexts", 2023,
  [arXiv:2307.03172](https://arxiv.org/abs/2307.03172), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev). A document is read once per request,
so the design question for long texts is always how little of it each request needs.*
