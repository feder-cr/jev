---
title: "Prefill vs decode: where LLM latency comes from"
description: "LLM latency has two parts: prefill reads the prompt in parallel, decode writes one token at a time. Why chat latency tracks answer length."
parent: "Speed"
nav_order: 4
---

# Prefill vs decode: where LLM latency comes from

**Every language model request has two phases: prefill, which reads the whole prompt in one
parallel pass, and decode, which writes the answer one token at a time.** Prefill time grows
with the length of the input; decode time grows with the length of the output, one pass per
token. A chat answer pays both, so its latency depends on how much it says. A model that returns
a probability instead of text pays only prefill.

The two phases do not just differ in length, they stress different parts of the hardware.
Prefill is heavy arithmetic on many tokens at once; decode is light arithmetic on one token
that still has to read the model's weights each time. That is why a model can read hundreds of
tokens in the time it takes to write a sentence.

This page is how the two phases work, what connects them, how to write latency as a formula,
why a decision model skips half of it, and how to see the split in your own numbers.

## What happens in prefill

Prefill takes the prompt, all of it, and runs it through the model in one go. In the words of
the Splitwise paper, "all the input prompt tokens run through the forward pass of the model in
parallel to generate the first output token". The paper calls this phase compute-intensive:
many tokens share each weight that is loaded, so the processor spends its time multiplying.

Two things come out of it: the model's prediction for what follows the prompt, and a cache of
intermediate values for every prompt token, so they never have to be computed again.

Prefill cost rises with the number of input tokens. On our reference laptop, a request of about
30 tokens took 54 ms end to end with jevos and one of about 190 tokens took 220 ms, roughly 1.1 ms
per prompt token. What that means for long documents is on
[why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).

## What happens in decode

Decode produces the answer. Each new token comes from a pass over just the last token, reading
the cache for everything before it. Splitwise describes this phase as sequential and "more
memory bandwidth and capacity bound": the work per pass is small, but the weights still have to
travel from memory to the processor for every single token.

The cache is what makes decode tolerable. Hugging Face's documentation explains that without
it each step would recompute all previous keys and values, and that with it each step computes
only the current token's. It also notes the cost: the cache's memory grows with the sequence.

## What connects the two: the KV cache

The cache built during prefill is the hand-off between the phases. It is why decode can start
without rereading the prompt, and it is also why a shared prompt can be reused: if two requests
begin with the same text, the cached values for that text are the same.

Serving systems exploit this. The llama.cpp server's `cache_prompt` option reuses the cache
from a previous request "so the common prefix does not have to be re-processed", and vLLM's
automatic prefix caching reuses cached blocks "when a new request comes in with the same prefix
as previous requests". Within one request, the same idea is what makes extra questions about
the same text cheap; see [many questions about one text](many-questions-about-one-text.md).

## Latency as a formula

Benchmarking guides write end-to-end latency as time to first token plus generation time.
NVIDIA's documentation defines time to first token as including queueing, prefill and network,
and inter-token latency as the average time between consecutive output tokens. So, roughly:

`latency = network + queue + prefill + (output tokens - 1) x time per output token`

An illustrative example, with made-up numbers that are not a measurement of any model: if
prefill takes 100 ms and each output token takes 20 ms, a 5-token answer costs about 180 ms of
model time and a 200-token answer about 4.1 seconds. The prompt was the same; only the length
of the answer changed.

That is why chat latency is hard to predict from the question: it depends on what the model
decides to say. It is also why a prompt that says "answer in one word" is a speed optimisation,
and an incomplete one, because the model may not obey.

## A decision model only pays prefill

Set output tokens to zero in the formula and only the first terms remain. That is the design of
jevos: it reads the state and the questions and returns P(yes) for each, and `output_tokens` is
always 0. There is no decode phase to wait for, no answer length to vary, and no stop condition
to get wrong.

Two consequences follow.

- **Latency tracks the input, not the answer.** A long text costs more, a long answer is
  impossible. For capacity planning, the input size is the whole story.
- **Everything that makes prefill cheaper helps directly.** Shorter state, fewer instruction
  tokens, questions grouped on one text. The longer argument, including what a probability gives
  you that a word does not, is on
  [why one forward pass beats generating an answer](why-one-forward-pass-beats-generation.md).

The same reasoning is what moves decisions off a paid API: output tokens are the slow part of a
call, and with per-token pricing they are billed as well, while a decision needs none; see
[reducing LLM cost with local yes/no decisions](reducing-llm-cost-with-yes-no-decisions.md).

## How to see the split in your own numbers

- **With a streaming chat API**: time to the first token is network plus queue plus prefill;
  the gaps between later tokens are decode.
- **With a local runtime**: llama.cpp's own tools report prompt processing and text generation
  speed separately, in tokens per second. Its quantization README, for example, gives both
  figures for each quantization of the model it uses as an example.
- **With jevos**: every response carries a `Server-Timing` header with `inference` and `total`
  durations, and `jev decide` on a native request (a file without `model`) returns the engine's
  timings. Since there is no decode, the inference time is essentially prompt processing.

Measure more than once and report the median; the method is on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).
When many requests share one server, the two phases also interact with batching; that is the
subject of [throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).

## Short answers to the questions that lead here

**What is prefill in an LLM?** The phase that reads the whole prompt in one parallel pass,
builds the cache, and produces the first prediction.

**What is decode?** The phase that generates output tokens one by one, each from a pass over the
last token and the cache.

**Which is slower?** Per token, decode. In total, whichever has more tokens to process: a long
document with a one-word answer is prefill-bound, a short question with an essay answer is
decode-bound.

**Why does time to first token grow with prompt length?** Because it includes prefill, which
processes every input token before anything can be written.

**Does a yes/no model have a decode phase?** Not jevos. It returns a probability after prefill,
with zero output tokens.

**See also:** [what makes a local LLM fast on a CPU](what-makes-a-local-llm-fast-on-a-cpu.md),
[the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md) and
[why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md).

## Sources

- jevos latency on the reference laptop (Intel Core Ultra 7 255H, 16 threads), zero output
  tokens and the `Server-Timing` header: our measurements and the
  [jev README](https://github.com/feder-cr/jev).
- The two phases and their bottlenecks: Patel et al.,
  [Splitwise](https://arxiv.org/abs/2311.18677), fetched 2026-09-29.
- KV cache behaviour:
  [Hugging Face Transformers, caching](https://huggingface.co/docs/transformers/main/en/cache_explanation),
  fetched 2026-09-29.
- Latency definitions:
  [NVIDIA NIM benchmarking metrics](https://docs.nvidia.com/nim/benchmarking/llm/latest/metrics.html),
  fetched 2026-09-29.
- Prefix reuse: [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
  and [vLLM automatic prefix caching](https://docs.vllm.ai/en/latest/design/prefix_caching.html),
  both fetched 2026-09-29; separate prompt and generation speeds:
  [llama.cpp quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md),
  fetched 2026-09-29.
- The 100 ms and 20 ms figures in the formula section are illustrative, not measured.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model that lives entirely in the
first half of this page.*
