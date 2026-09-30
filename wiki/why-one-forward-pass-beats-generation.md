---
title: "Why one forward pass beats generating an answer"
description: "Generating even a one-word yes or no costs a decode step, parsing and retries. Reading a probability costs only the pass that reads the prompt."
parent: "Speed"
nav_order: 3
---

# Why one forward pass beats generating an answer

**When the answer is yes or no, generating it as text is slower and more fragile than reading
it as a probability.** A chat model has to read the prompt, then produce at least one token,
then hand your code a string that must be parsed back into a boolean, and sometimes it produces
the wrong string. A model that returns P(yes) stops after reading the prompt: the pass that
reads the text is the answer, so there are no output tokens and no format to break.

The time saved is only part of it. The bigger gain is that a probability carries information a
word throws away. "Yes" from a chat model looks the same whether the model was sure or barely
leaning; 0.93 and 0.52 do not, and that difference is what lets you set a threshold.

This page is what a forward pass is, what a generated one-word answer really costs, why no
output means no format errors, what you get back instead, and where this design is the wrong
one.

## What is a forward pass, and what does generation add?

A forward pass is one run of the input through the model. For a prompt, the whole text goes
through at once: the Splitwise paper describes all input tokens running "through the forward
pass of the model in parallel to generate the first output token".

Generation is what happens after. Each further token is produced by another pass on the last
token, "sequentially", in the same paper's words, with a cache of what came before so the
prompt is not recomputed. Hugging Face's documentation on caching puts it plainly:
autoregressive generation "makes a prediction one token at a time".

So a text answer always costs one prompt pass plus one pass per output token. A probability
answer costs the prompt pass. The two phases, and why they have different speeds, are on
[prefill vs decode: where LLM latency comes from](prefill-vs-decode-llm-latency.md).

## What a one-word answer really costs

Ask a chat model "Answer yes or no: is this a billing problem?" and follow the work.

1. **Read the prompt.** The same cost either way.
2. **Pick the first token.** A sampled or greedy choice among the whole vocabulary. It might be
   "Yes", "yes", " Yes", "YES", or "The".
3. **Keep going until a stop.** A chat model may add punctuation, a sentence, or an
   explanation unless you cap the output length, and a cap can cut off an answer that did not start with
   the word you wanted.
4. **Parse.** Your code lowercases, strips, matches "yes" or "no", and decides what to do with
   "Yes, but only if the charge was duplicated".
5. **Retry or default** when the parse fails, which costs another full call.

Steps 2 to 5 do not exist when the answer is a number between 0 and 1. On a hosted API, each
retry also pays the network again: our hosted measurement from Europe was about 344 ms per call,
nearly the same for a short and a long text.

## No output tokens, no format errors

jevos never writes. Every response reports `output_tokens: 0`, and the answer to each question
comes back as a `noul`, the probability that the answer is yes:

```json
{
  "model": "jev-latest",
  "state": "I was charged twice for the same order.",
  "questions": {"billing": {"type": "noul", "instructions": "Is this a billing problem?"}}
}
```

In the README's example this comes back as `"noul": 0.9` with 27 input tokens. There is no
string to match, so there is nothing to misspell, no preamble to strip, and no refusal sentence
to interpret. A response is either a well-formed probability or an HTTP error you handle like
any other.

Structured output features on chat APIs attack the same problem from the other side, by
constraining what the model may generate. They make the format dependable; they do not remove
the generation. The comparison is on [structured output vs a probability](structured-output-vs-a-probability.md).

## What you get instead of a word

A word is a decision already made at an unknown cut-off. A probability lets you place the
cut-off yourself:

- **Act on the confident ends, review the middle.** Above 0.8 do it, below 0.2 do not, and send
  the rest to a person; how to size that band is on
  [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).
- **Move the bar where mistakes are expensive.** If a wrong yes costs more than a wrong no,
  require more than 0.5. Our measurements show this model leans toward yes when it cannot work
  out the answer (152 wrong yeses against 91 wrong noes on 999 new questions), which is one
  more reason to raise it; see [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).
- **Combine answers in code.** Probabilities can be compared, averaged and combined with AND
  and OR; strings have to be converted first.

On data like its held-out split, jevos is well calibrated (calibration error 0.009 on 6,397
natural yes/no questions), which is what makes the number usable as a probability and not just
a score. On new kinds of questions that calibration does not fully carry over; the caveat is on
[what P(yes) means, and what it does not](what-p-yes-means.md).

## Where generating is the right design

A single forward pass answers one thing: how likely is yes. Anything else needs text.

- **Explanations.** If a reviewer needs to read why, you need a model that writes.
- **Extraction.** Pulling a date, an amount or a name out of a text is generation, or regex.
- **Open answers.** Summaries, replies, translations.
- **Scores that need arithmetic.** jevos answers `score` questions, early, and is weakest where the
  level is a sum of points.

A common pattern is to keep the generator for the one step that needs words and move every
"is it X?" in the pipeline to a decision model. How to find those steps in an existing app is on
[replacing chat LLM calls with yes/no questions](replacing-llm-calls-with-yes-no-questions.md).

## Short answers to the questions that lead here

**Can I get a probability from a chat model instead of a word?** If your runtime or API exposes
token log-probabilities, they give the probability of "yes" as the first token. You still pay the
generation call and have to decide which spellings count as yes.

**Is one output token really slower than zero?** Yes, by at least one more pass through the
model, plus parsing. The larger cost is usually everything that follows the first token.

**Does no output mean no hallucination?** No. The model can still give a wrong probability. It
cannot give a malformed answer.

**Why not just set max tokens to 1?** It shortens generation, but the first token may be a
different spelling, a space, or the start of a refusal, so you still parse and handle failures.

**Is the probability the same as the model's confidence?** It is the model's estimate that the
answer is yes. How far to trust it depends on calibration on data like yours.

**See also:** [the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md),
[ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md) and
[LLM confidence scores: probabilities vs self-reported confidence](llm-confidence-score-probability-vs-self-report.md).

## Sources

- `output_tokens: 0`, the billing example and its answer, and the `score` answers: the
  [jev README](https://github.com/feder-cr/jev).
- Error counts (152 and 91) and the 999-question set; calibration error 0.009 on the held-out
  split: our own measurements. Hosted latency from Europe: our measurement of Jev, network
  included.
- Parallel prompt phase and sequential token phase: Patel et al.,
  [Splitwise](https://arxiv.org/abs/2311.18677), fetched 2026-09-29.
- Generation one token at a time and the KV cache:
  [Hugging Face Transformers, caching](https://huggingface.co/docs/transformers/main/en/cache_explanation),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model with no way to write a word:
every answer it gives is a number between 0 and 1.*
