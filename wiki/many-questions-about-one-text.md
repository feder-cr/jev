---
title: "Many questions about one text: why the extra ones are cheap"
description: "Questions in one request share the text, which is read once: three questions took 66 ms against 49 ms for one. Why, and how to group them."
parent: "Speed"
nav_order: 7
---

# Many questions about one text: why the extra ones are cheap

**When several questions are about the same text, sending them in one request makes each extra
question cost a fraction of the first, because the text is read once and shared.** In the jev
README's refund example, three questions about one 95-token record take about 66 ms together,
against 49 ms for one of them alone. Sent as three separate requests, each one would pay for
reading the whole record again.

The saving comes from a general property of language models, not a trick of one server: the
expensive part of a request is processing the input, and when many prompts begin with the same
text, that part can be done once. For a decision model it matters more than usual, because
processing the input is nearly all the work there is.

This page is the measurement, why shared text is cheap, how to group questions, when to split
them anyway, and what it does to the cost of a pipeline.

## The measurement

| Request | Questions | Input tokens | Time |
|---|---|---|---|
| refund record, one question | 1 | 68 | 49 ms |
| same record, three questions | 3 | 95 | about 66 ms |

Measured with jevos-v2 on an Intel Core Ultra 7 255H with 16 threads, with the record read from
scratch. The two extra questions added about 17 ms between them, roughly 8.5 ms each, against
49 ms for the first.
That per-question figure is arithmetic on these two measurements, not a measurement of its
own: it will be different for longer questions, and we have not published timings for larger
groups.

## Why the extra questions are cheap

A language model's cost is dominated by the tokens it has to process. Serving systems have long
used the fact that identical leading text produces identical intermediate results: the llama.cpp
server re-uses its cache from a previous request "so the common prefix does not have to be
re-processed", and vLLM's automatic prefix caching reuses cached blocks when a request arrives
"with the same prefix as previous requests". The mechanics of that cache are on
[prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md).

jev gives you the benefit inside one request. The README states it directly: questions in the
same request share the state, which is read once. What each question adds is its own words,
not another copy of the text. The longer the state is relative to the questions, the bigger
the saving, which is why grouping pays most on long records. States asked about again are also
kept (up to 16 states or 8,192 tokens), so a later request on the same text reads only its
questions: the same two requests took 24 ms and 39 ms when the record had been read before.

## How to group questions in one request

Give each question a name and put them in the same `questions` object:

```json
{
  "model": "jev-latest",
  "state": {
    "channel": "email",
    "customer_message": "Third time asking. My invoice shows two charges for March and nobody replies. Fix it or I cancel."
  },
  "questions": {
    "billing":  {"type": "noul", "instructions": "Is this message about a billing problem?"},
    "cancel":   {"type": "noul", "instructions": "Does the customer threaten to cancel?"},
    "repeat":   {"type": "noul", "instructions": "Does the customer say they have asked before?"},
    "abusive":  {"type": "noul", "instructions": "Does the message contain insults or abuse?"}
  }
}
```

Each question comes back as its own `noul` under its name, so the code that acts on them reads
like the questions. Some rules of thumb:

- **One condition per question.** Four small questions are cheap together and each is easy; one
  compound question is no cheaper and hides which part failed. The case is made on
  [one condition per question](one-condition-per-question.md).
- **Combine in code.** "Billing and threatens to cancel" is `billing > t and cancel > t`, with
  the logic you choose; see [combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).
- **Keep the policy in the question that needs it.** A long rule written into every question is
  paid every time; put it only where it is read.

## When to split into separate requests

- **The questions are about different texts.** The saving only exists for a shared state. Two
  records are two requests.
- **Some answers decide whether others are needed.** If a cheap gate question ("Is this message
  in scope at all?") filters out most traffic, ask it first and send the rest only for what
  passes. The extra round trip on a local server is small.
- **A question needs different context.** If one question needs the full thread and the rest
  only the last message, the long state would slow down the short questions.
- **Timeouts.** A very large group on a very long state is one long request. If a caller has a
  deadline, keep each request within it; budgets are on
  [latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md).

## What grouping does to a pipeline

Grouping changes the arithmetic of anything that asks many questions: ticket routing with one
question per queue, an evaluation rubric with five criteria per output, a moderation policy
with a question per rule. The cost is roughly one reading of the text plus a small amount per
question, instead of one reading per question.

On the evaluation side, this is what makes a local judge practical, as described on
[LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md): a record with several criteria costs a
little more than a record with one. On the routing side, it means a queue can be added as one
more question without doubling the latency; see
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md).

Against a hosted API the saving has a second part: one request pays the network once, however
many questions it carries.

## Short answers to the questions that lead here

**Is it faster to ask several questions in one LLM call?** For questions about the same text,
yes. Three questions took about 66 ms together against 49 ms for one alone.

**Does the model answer each question independently?** Each question gets its own probability
under its own name. They share the text, not the answer.

**Is there a limit on questions per request?** The total must fit in the 8,192-token context.
Long instructions in many questions add up.

**Why not one question that asks everything?** A compound question is no faster and hides which
condition was true. Separate questions, combined in code, are clearer and easier to threshold.

**Does this work with Jev's SDK?** The wire format is the same, so a request with several named
yes/no questions works unchanged.

**See also:** [why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md),
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md)
and [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Sources

- The 66 ms and 49 ms timings, the 68 and 95 input tokens, the shared state read once, the kept
  states and the context size: our measurements and the [jev README](https://github.com/feder-cr/jev).
  The 8.5 ms per extra question is derived from those two figures.
- Prefix reuse in serving systems:
  [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
  and [vLLM automatic prefix caching](https://docs.vllm.ai/en/latest/design/prefix_caching.html),
  both fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose own demo asks its two questions
in one request for the same reason: the game waits for the model, and one reading is shorter
than two.*
