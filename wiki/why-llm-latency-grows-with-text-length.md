---
title: "Why LLM latency grows with the length of the text"
description: "A local LLM reads every token of its input, so latency rises with length: about 0.6 ms per prompt token on our laptop. What it means and how to trim."
parent: "Speed"
nav_order: 5
---

# Why LLM latency grows with the length of the text

**A language model has to process every token of its input before it can answer, so a longer
text takes longer, roughly in proportion to its length.** On our reference laptop, jevos
answered a request of about 30 tokens in 28 ms and one of about 190 tokens in 130 ms, reading
each text from scratch: about 0.6 ms for each additional prompt token. Double the text and you should expect close to double the
time, which is why the cheapest speed-up is usually sending less.

The counterintuitive part is where the tokens come from. The text you care about is only part of
the input: the question, any rule written into it, JSON keys and punctuation are all tokens too.
Trimming a noisy record often saves more than choosing a faster model.

This page is the measurement and what it implies, what counts as a token, what happens on long
documents, how to trim the input, and why a hosted API does not show the same slope.

## How much does each token cost?

| Request | Input tokens | jevos, text read from scratch | jevos, same text asked again |
|---|---|---|---|
| short | about 30 | 28 ms | not published |
| long | about 190 | 130 ms | 22 ms |

The difference is about 102 ms for about 160 extra tokens, a little over half a millisecond each,
which is where the "about 0.6 ms per prompt token" figure comes from. Measured on an Intel Core
Ultra 7 255H with 16 threads and no GPU in use, median of 10 requests after 3 warm-up requests,
with jevos-v3, which has the same size and speed as jevos-v4.

The last column is the same request sent again. jev keeps texts it has read (up to 16 of them,
8,192 tokens in all, by default), so a second question on the same text reads only the
question, and length stops mattering.

Two readings of the table matter in practice. The slope is what you pay per token of state;
the short request tells you there is also a base cost that does not go away however short the
text. And both are specific to this CPU: on another machine the slope changes, the shape does
not. The reasons the shape holds, prompt processing that touches every token, are on
[prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md).

## What counts as a token?

Everything the model reads: the `state`, the `instructions` of every question, and whatever
wording the server adds around them. The README's one-line billing example, "I was charged
twice for the same order." with "Is this a billing problem?", comes to 27 input tokens. The
refund example, a three-field JSON object with three questions and a policy sentence, comes to
95.

Do not estimate from word counts. Every response reports `usage.input_tokens`, so the reliable
way to know what a record costs is to send a few real ones and read that field.

## What happens on a long document?

jevos accepts up to 8,192 tokens. If the slope stayed at 0.6 ms per token all the way, a full
context would take on the order of 5 seconds on our laptop. We have not measured that, and the
straight-line assumption is optimistic rather than safe: attention over a long prompt does more
work per token as the prompt grows, so treat the extrapolation as a rough idea, not a figure.

The practical conclusion does not depend on the exact number. At a few hundred tokens the model
fits an interactive loop; at thousands it fits a background job. For long documents, the
options are to ask about the part that matters, or to split the document and ask per chunk,
combining the answers in code; that approach is on
[yes/no questions about long documents](yes-no-questions-about-long-documents.md).

## How to send fewer tokens without losing the answer

- **Send only the fields the questions need.** A refund question needs the item, the delivery
  and the customer's message, not the full order history.
- **Compute in code, send the result.** `"delivered": "5 days ago"` is shorter than two
  timestamps, and it turns a date calculation, the model's weakest kind of question, into
  reading. The reasoning is on [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).
- **Drop noise.** Signatures, quoted reply chains, tracking footers and HTML carry tokens and
  rarely carry the answer.
- **Keep field names readable, not long.** `customer_message` is worth its tokens because it
  tells the model what the text is; a nested wrapper object that only your database needed is
  not.
- **Ask several questions in one request.** The state is read once, so three questions about one
  text cost about 66 ms against 49 ms for one alone; see
  [many questions about one text](many-questions-about-one-text.md).

A trimmed state looks like the README's own example:

```json
{
  "model": "jev-latest",
  "state": {
    "item": "wireless mouse",
    "delivered": "5 days ago",
    "customer_message": "The box arrived empty. This is the second time!"
  },
  "questions": {"upset": {"type": "noul", "instructions": "Is the customer upset?"}}
}
```

More on choosing fields and names is on
[sending JSON as the text: designing the state](designing-the-state-as-json.md).

## Why a hosted API looks flat

On the same two requests, the hosted Jev API took 311 ms and 314 ms, network
included. Its time barely changed while the local model's more than quadrupled. A hosted model reads every
token too; the flat line only says that, from where we measured, the part that depends on length
was small next to the fixed part, the network round trip and whatever happens before the model
starts.

That has a consequence for choosing where to run: local wins by the widest margin on short
texts, and the gap narrows as texts grow. On long enough documents a hosted model can be the
faster option end to end. Where the fixed cost comes from is on
[why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md),
and the wider trade-off is on
[local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md).

## Short answers to the questions that lead here

**Why is my LLM slower on long prompts?** Because it processes every input token before
answering. On our laptop each extra token cost jevos about 0.6 ms.

**Does the length of the question matter, or only the text?** Both. Instructions are input
tokens like any other, and a long policy written into each of several questions adds up.

**How many tokens can jevos read?** 8,192 per question, the text plus that question, by default.

**Is latency exactly linear in length?** Close to it over the range we measured, about 30 to 190
tokens. We have not measured the full context and would not assume it stays linear.

**What is the fastest fix for a slow request?** Send less: the fields the question needs, dates
turned into durations, no quoted email history.

**See also:** [what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md),
[latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md) and
[ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md).

## Sources

- Latency of the short and long requests, the per-token figure, the three-question timing,
  the hosted Jev timings and the 8,192-token context: our own measurements and the
  [jev README](https://github.com/feder-cr/jev).
- Token counts of the two examples: `usage.input_tokens` as shown in the README.
- The 5-second figure is an extrapolation from the measured slope, not a measurement.
- Attention work growing with sequence length:
  [Hugging Face Transformers, caching](https://huggingface.co/docs/transformers/main/en/cache_explanation),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where the quickest speed-up we know
of is deleting the fields nobody asked about.*
