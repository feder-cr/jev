---
title: "jevos vs the OpenAI API for yes/no classification"
description: "A hosted chat model asked to answer yes or no, with or without logprobs, next to a local model that returns P(yes): parsing, latency, cost, privacy."
parent: "Comparisons"
nav_order: 3
---

# jevos vs the OpenAI API for yes/no classification

**A hosted OpenAI model answers a yes/no question by generating an answer, which you parse or
read the token probabilities of; jevos answers it on your own CPU with a probability and no text
at all.** The OpenAI API is the stronger reader, handles many languages and can explain itself.
jevos avoids the network round trip, the per-token bill and sending the text anywhere, and it has
no output format to break. If the question is hard, or not in English, the API is the better
tool; if it is one of many simple reading questions about English text, a local probability is
usually enough.

Conflict of interest, in one line: we build jevos, and every OpenAI fact on this page comes from
OpenAI's own documentation, fetched 2026-09-29.

The difference is not only speed. A generated "Yes" is a string your code must interpret, and a
probability is a number your code can threshold. That changes how you handle doubt: with a
probability, "not sure" is a range you can route to a person instead of a parsing edge case.

This page is the three ways to get a yes or no from the API, what each one leaves you to parse,
where latency comes from, what you pay for, where the text goes, and when to prefer the API.

## Three ways to get a yes/no from a hosted chat model

**Ask for one word.** "Answer yes or no." The model generates a token or a few, and your code
compares the text with "yes". It works most of the time, and the rest of the time you get "Yes.",
"yes, because..." or a refusal, and you write the normalisation.

**Ask for a schema.** OpenAI's Structured Outputs "ensures the model will always generate
responses that adhere to your supplied JSON Schema", so a field such as `{"answer": boolean}`
arrives well formed. The same guide lists the exceptions: a safety refusal, reported in a
separate `refusal` field, and an incomplete response when a token limit is reached. You get a
clean boolean, but still no measure of doubt.

**Read the logprobs.** With `logprobs` enabled the API returns the log probability of each output
token, and `top_logprobs` (an integer from 0 to 5) adds the most likely alternatives at each
position. OpenAI's cookbook uses this for classification: read the probability of the label the
model chose, send results above a threshold through automatically and the less certain ones to
manual review. This is the closest thing to P(yes), with two caveats from the same cookbook:
logprobs are for output tokens, so the model still has to generate at least one, and you have to
find the "yes" and "no" tokens among the alternatives yourself.

## What each approach leaves you to parse

| | what comes back | what your code does |
|---|---|---|
| one-word answer | text | normalise and match, handle surprises |
| Structured Outputs | JSON matching your schema | check for `refusal` or an incomplete status |
| logprobs | tokens with log probabilities | find the yes and no tokens, convert, renormalise |
| jevos | `{"noul": 0.9}` per question | compare with a threshold |

The last row is not a claim that jevos is smarter. It is that nothing is generated
(`output_tokens` is always 0), so there is no text to be malformed. The general argument is on
[structured output vs a probability](structured-output-vs-a-probability.md).

## Where the latency comes from

OpenAI's latency guide says that generating tokens "is almost always the highest latency step
when using an LLM" and that each request adds round-trip latency. A one-word answer keeps
generation short, but the round trip stays: DNS, TLS, the request crossing the network, queueing
at the provider, and the response coming back.

We have not measured OpenAI's API, so there is no OpenAI number on this page. What we have
measured is a different hosted decision API from a laptop in Europe: TypeSafe's Jev took 344 ms
on a short request and 345 ms on a long one, network included, while jevos took 26 ms and 112 ms
on the same laptop. The flatness of the hosted numbers is the point: when the network dominates,
text length barely matters. The detail is on
[why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md).

Batching several questions into one request is the fix both sides share. OpenAI's guide suggests
putting sequential steps into a single prompt to avoid extra round trips; jevos reads the state
once for every question in a request, so three questions took about 66 ms against 49 ms for one.

## What you pay for

OpenAI prices its models per million tokens, with input, cached input and output listed as
separate rates. A yes/no call pays for the whole prompt on every request, the text plus the
instructions, and for the output tokens, however few.

jevos has no per-token price. The cost is the machine it runs on: a CPU and the
memory for the loaded model. At low volume the API is cheaper than keeping a server up; at high
volume on short decisions the arithmetic tends to flip. Where that line falls depends on your
volume and your prices, which is why
[reducing LLM cost with local yes/no decisions](reducing-llm-cost-with-yes-no-decisions.md)
starts with counting how many of your calls are really decisions.

## Where the text goes

OpenAI's data controls page states that data sent to the API is not used to train its models
unless you opt in, and that abuse monitoring logs are retained for up to 30 days unless longer
retention is required by law. Zero Data Retention and data residency in a list of regions exist,
subject to OpenAI's approval.

With jevos the text does not leave the machine, because the server listens on 127.0.0.1 by
default and answers without a network call. That removes a data processor from the picture. It does not
remove your own obligations: logs, access control and retention on your side are still yours,
as [a private LLM for text classification](private-llm-for-text-classification.md) explains.

## When the OpenAI API is the better choice

- The question needs reasoning or knowledge beyond the text, or arithmetic. jevos was right
  0.584 of the time on arithmetic questions in our 999-question test, against 0.954 on facts
  stated in the text.
- The text is not in English. jevos reads English only.
- You need a label with an explanation, or free text, alongside the decision.
- Your volume is low and you do not want to operate a server.

## Short answers to the questions that lead here

**Can I get a probability from the OpenAI API?** Partly: `logprobs` and `top_logprobs` return log
probabilities of the output tokens, so you can read how likely the generated "yes" was.

**Does Structured Outputs solve parsing?** It gives a well-formed JSON value, except on refusals
and incomplete responses, but a boolean carries no measure of doubt.

**Is a local model faster than the API?** We did not measure OpenAI. Against a hosted decision
API from Europe, jevos was faster on both of our requests: 26 and 112 ms against 344 and 345 ms.

**Is it cheaper?** There is no per-token price locally; you pay for the hardware. Whether that
is cheaper depends on volume.

**Is jevos as accurate as a large hosted model?** No, especially on computation. It is strongest
on reading questions: facts, tone, negation.

**See also:** [local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md),
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md) and
[LLM confidence scores: probabilities vs self-reported confidence](llm-confidence-score-probability-vs-self-report.md).

## Sources

- Our measurements: latency of jevos and of TypeSafe's Jev on the same two requests, the
  three-question timing, and accuracy by kind on our 999-question set (`jevos-q4_k_m`); see the
  [jev README](https://github.com/feder-cr/jev).
- OpenAI, [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
  fetched 2026-09-29.
- OpenAI cookbook, [Using logprobs](https://developers.openai.com/cookbook/examples/using_logprobs),
  fetched 2026-09-29.
- OpenAI, [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization),
  fetched 2026-09-29.
- OpenAI, [Data controls in the OpenAI platform](https://developers.openai.com/api/docs/guides/your-data),
  fetched 2026-09-29.
- OpenAI, [API pricing](https://developers.openai.com/api/docs/pricing), for the per-million-token
  structure only, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU and has no OpenAI number of its own to report, so it reports none.*
