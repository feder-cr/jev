---
title: "Reranking search results with yes/no questions"
description: "Rerank a retriever's top passages by asking whether each one answers the query and sorting by P(yes), and when a cross-encoder reranker is the better tool."
parent: "Use cases"
nav_order: 21
---

# Reranking search results with yes/no questions

**You can rerank the top results of a search or RAG retriever by asking one yes/no question per
passage, "Does this passage answer the question ...?", and sorting the passages by P(yes).** It is
pointwise reranking: each passage is judged on its own, and the same probability works as a cutoff
for passages that should not reach the generator at all. With jevos it runs on a CPU, one request
per passage. For plain topical relevance over many candidates per query, or for text that is not
English, a dedicated cross-encoder reranker is the better tool.

The non-obvious point is that a question lets you define relevance, where a reranker has learned
one. A question can ask "Does it answer this for the 2026 version of the product?" or "Does it
state the refund period, not just mention refunds?", which no off-the-shelf relevance score knows
about.

This page is the method with a code sketch, how it compares with cross-encoders and with LLM
listwise reranking, the cost per query, when a dedicated reranker wins, and how to combine them.

## How does yes/no reranking work?

The retriever (BM25, embeddings or both) returns the top k passages. Each passage gets the same
question with the query written into it. Sort by P(yes) and drop what falls below a threshold.

```python
import requests

URL = "http://127.0.0.1:8017/v1/systemone"

def rerank(query, passages, threshold=0.5):
    scored = []
    for passage in passages:
        body = {"model": "jev-latest", "state": passage, "questions": {
            "relevant": {"type": "noul",
                         "instructions": f'Does this passage answer the question "{query}"?'}}}
        answers = requests.post(URL, json=body).json()["answers"]
        scored.append((answers["relevant"]["noul"], passage))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [(p, text) for p, text in scored if p >= threshold]
```

The question asks whether the passage answers, not whether it is about the query: a passage can
share every keyword and still lack the answer. The stricter wording is on
[ask whether the text says it at all](ask-whether-the-text-says-it.md). The 0.5 is a placeholder;
pick the cutoff on labelled queries, as on
[how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).

## How is this different from a cross-encoder reranker?

The standard design is retrieve and rerank. In the sentence-transformers documentation a
bi-encoder produces "e.g. 100 possible candidates which are then re-ranked by the Cross-Encoder",
whose advantage is "the higher performance, as they perform attention across the query and the
document", while scoring "thousands or millions of (query, document)-pairs would be rather slow".
Yes/no reranking keeps that division of labour.

The differences are what the judge was built for and what has been measured. The model card of
`cross-encoder/ms-marco-MiniLM-L6-v2` says it "was trained on the MS Marco Passage Ranking task"
and reports NDCG@10 of 74.30 on TREC DL 19 and 1,800 documents per second, with "Runtime was
computed on a V100 GPU". jevos has no reranking benchmark: we have not run it on MS MARCO, TREC or
BEIR, so there is no number to set beside those.

Reading a word's probability as relevance is an old idea: in monoT5 (Nogueira, Jiang and Lin,
2020) a model generates relevance labels as "target words", and "the underlying logits of these
target words can be interpreted as relevance probabilities for ranking". A yes/no decision model
is that pattern with the question left for you to write.

## What about asking an LLM to sort the whole list?

That is listwise reranking. RankGPT (Sun et al., 2023) numbers the passages and asks the model "to
generate the permutation of passages in descending order based on their relevance to the query",
sliding a window over lists too long for one prompt; the authors state it "requires 10 API calls
per query to re-rank 100 passages", and report that properly instructed LLMs "can deliver
competitive, even superior results to state-of-the-art supervised methods".

A listwise model compares passages with each other, which pointwise questions never do, but each
call is a generation with a ranking to parse. The same paper notes that earlier pointwise LLM methods
"rely on the log probability of LLM, which is often unavailable for LLM API"; a decision model
returns that probability as its whole answer. Qin et al. (2023) argue that off-the-shelf LLMs "do
not fully understand" pointwise and listwise prompts and propose Pairwise Ranking Prompting; the
yes/no version is on
[pairwise comparison with a yes/no judge](pairwise-comparison-with-a-yes-no-judge.md).

## What does it cost per query?

One request per passage, because each passage is a different text. On the README's laptop (Intel
Core Ultra 7 255H, 16 threads) a short request read from scratch took 28 ms and a long one 130 ms.
If your passages are the size of that long request, 20 of them one after another is roughly
20 times 130 ms, about 2.6 seconds: illustrative arithmetic, not a measurement of reranking. Why
length drives the time is on
[why LLM latency grows with the length of the text](why-llm-latency-grows-with-text-length.md).

Three things bring it down:

1. **A smaller k.** Rerank 10 or 20 candidates, not 100, once you know the retriever's top k still
   holds the answers.
2. **Kept texts.** By default the server keeps recently read texts for later requests (16 texts,
   8,192 tokens in all; `--state-cache`), and the README's long request took 22 ms instead of
   130 ms when the same text was asked again. With the passage as the `state`, popular queries that
   bring back the same passages benefit; a large corpus with new passages each time mostly does not.
3. **Extra questions ride along.** Questions about one text share a single reading: three took
   about 66 ms together against 49 ms for one.

## When is a dedicated reranker the better tool?

Plainly, in these cases:

- **Many candidates per query.** Reordering 100 passages for every query is a cross-encoder's job.
  Its card's figure is from a GPU and ours are per request on a laptop CPU, so they do not compare
  directly, but one request per passage is not built for that volume.
- **Plain topical relevance.** A model built and benchmarked for exactly that, with published
  numbers to check, is the stronger default.
- **Other languages.** jevos reads English only. The model card of `BAAI/bge-reranker-v2-m3` calls
  it a "Lightweight reranker model, possesses strong multilingual capabilities", with 0.6B
  parameters.
- **You still want it local.** llama.cpp's server has a reranking endpoint (`--rerank`,
  `POST /v1/rerank`) that "Requires a reranker model (such as bge-reranker-v2-m3)"; the two
  servers are compared on [jev serve vs llama.cpp server](jev-serve-vs-llama-cpp-server.md).

## Where do yes/no questions earn their place?

As the last stage. Let the retriever or a cross-encoder cut the list to 5 or 10, then ask what
relevance means for you: does it answer the question, does it apply to this customer's plan.
Because P(yes) is a probability, a cutoff can leave the generator with nothing, so it says "I
don't know" instead of answering from noise; that is the case the
`declines` question on [RAG evaluation with yes/no questions](rag-evaluation-with-yes-no-questions.md)
looks for. The cheap-first pattern is on
[a model cascade: small model first, large model on doubt](model-cascade-small-model-first.md).

## Short answers to the questions that lead here

**What is a reranker?** A second-stage model that reorders a retriever's top results by relevance
to the query, reading the query and each passage together.

**Can an LLM be used as a reranker?** Yes: pointwise (a relevance probability per passage, as
here), pairwise (which of two is better) or listwise (the model writes an ordering, as in RankGPT).

**Is yes/no reranking better than a cross-encoder?** Not for plain relevance at volume, and we
have no benchmark that says otherwise. It is useful on a short English list when relevance is a
rule you can state.

**Can I send all the passages in one request?** You can put several passages in one state and ask
one question per passage, read once. The questions must then point at passages by number, all must
fit 8,192 tokens, and we have not measured whether answers hold up as well as one passage per
request.

**Does a high P(yes) mean the passage is true?** No. It means the model reads the passage as
answering the query; whether the passage is correct is a question no reranker answers.

**See also:** [RAG faithfulness check with a local LLM](rag-faithfulness-check-with-a-local-llm.md),
[semantic routing vs yes/no questions](semantic-routing-vs-yes-no-questions.md) and
[latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md).

## Sources

- Our measurements, from the [jev README](https://github.com/feder-cr/jev): 28 and 130 ms read from
  scratch (median of 10, measured with jevos-v3, same size and speed as jevos-v4), 22 ms for a text
  asked again, 66 ms against 49 ms, the cache defaults, the context and English only. No reranking
  measurement of jevos exists; the 2.6 seconds is arithmetic.
- Fetched 2026-10-12: sentence-transformers
  [Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html);
  model cards of [cross-encoder/ms-marco-MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2)
  and [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3); the
  [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
- Papers, fetched 2026-10-12: Nogueira, Jiang and Lin, monoT5,
  [arXiv:2003.06713](https://arxiv.org/abs/2003.06713); Sun et al., RankGPT,
  [arXiv:2304.09542](https://arxiv.org/abs/2304.09542) and its [full text](https://arxiv.org/html/2304.09542);
  Qin et al., Pairwise Ranking Prompting, [arXiv:2306.17563](https://arxiv.org/abs/2306.17563).

---

*From the notes of [jev](https://github.com/feder-cr/jev), which has no reranking benchmark of its
own: the cross-encoder figures on this page are the model card's, measured on a GPU.*
