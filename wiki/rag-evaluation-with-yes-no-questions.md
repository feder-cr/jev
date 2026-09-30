---
title: "RAG evaluation with yes/no questions"
description: "Score a RAG pipeline locally with yes/no questions about each passage and each answer: retrieval relevance, faithfulness and answer relevance."
parent: "Evaluation"
nav_order: 1
---

# RAG evaluation with yes/no questions

**You can evaluate a retrieval-augmented generation (RAG) pipeline with three kinds of yes/no
question: is this retrieved passage relevant to the query, is every claim in the answer
supported by the passages, and does the answer respond to what was asked.** Each question
returns a probability, the probabilities become a rate per stage, and the rates tell you whether
a bad answer came from retrieval or from generation. With a local model such as jevos the whole
evaluation runs on a CPU, and your documents and user queries never leave the machine.

The non-obvious point is that a single quality score for a RAG system is close to useless for
fixing it. A wrong answer built on the wrong passages needs a better retriever. A wrong answer
built on the right passages needs a better prompt or a better generator. Asking one question per
stage separates the two cases at no extra cost.

This page is the failures to look for, the requests for retrieval and for the answer, how to turn
the probabilities into a diagnosis of the pipeline, and where a small judge stops being reliable.

## What can go wrong in a RAG pipeline?

Three things, and each one gets its own question.

| Stage | Failure | Yes/no question |
|---|---|---|
| retrieval | the passages do not contain the answer | Does this passage contain information that helps answer the query? |
| grounding | the answer adds or changes facts | Is every claim in the answer supported by the passages? |
| relevance | the answer is true but beside the point | Does the answer respond to the query that was asked? |

The Ragas paper splits RAG evaluation along similar lines (whether retrieval finds relevant and
focused passages, whether the generator uses them faithfully, and the quality of the generation)
and stresses doing it without human-written reference answers. Yes/no questions are
reference-free in the same sense: they need the query, the passages and the answer, not a gold
answer to compare against.

## How do I score retrieval?

One passage per question, never "are these passages relevant?". A set of five passages with one
good one in the middle has no single right answer to that question, and the model has to guess
what you meant. The general rule is on
[one condition per question](one-condition-per-question.md).

```json
{
  "model": "jev-latest",
  "state": {
    "query": "How long do I have to return an unworn pair of shoes?",
    "passage": "Unworn items in their original box can be returned within 30 days of delivery."
  },
  "questions": {
    "relevant": {"type": "noul", "instructions": "Does the passage contain information that helps answer the query?"}
  }
}
```

With one relevance probability per retrieved passage, two numbers fall out in code:

- **precision at k**: the mean relevance of the top k passages, or the share above your
  threshold. It says how much noise the generator has to read through.
- **hit rate at k**: whether the highest relevance in the top k clears the threshold. It says
  whether the answer was findable at all.

Recall, the share of all relevant passages in your corpus that were retrieved, cannot come from
this question alone: it needs to know which passages exist that were not retrieved, and that
means labels. Be straight about it in your reports.

## How do I score the answer?

Put the query, the retrieved passages and the answer in one `state` and ask several questions at
once. The passages are read once and each extra question costs little: in the README's
measurement, three questions on one text take about 66 ms against 49 ms for one.

```json
{
  "model": "jev-latest",
  "state": {
    "query": "How long do I have to return an unworn pair of shoes?",
    "passages": ["Unworn items in their original box can be returned within 30 days of delivery."],
    "answer": "You can return them within 30 days, as long as they are in the original box."
  },
  "questions": {
    "grounded":  {"type": "noul", "instructions": "Is every claim in the answer supported by the passages?"},
    "on_topic":  {"type": "noul", "instructions": "Does the answer respond to the query that was asked?"},
    "declines":  {"type": "noul", "instructions": "Does the answer say the information is not available?"}
  }
}
```

The `declines` question is specific to RAG and easy to forget. When retrieval found nothing
useful, the correct behaviour of the generator is to say so, and a pipeline that answers
confidently from empty passages is the one that invents things. Checking faithfulness claim by
claim, rather than for the whole answer at once, is the subject of
[RAG faithfulness checks with a local LLM](rag-faithfulness-check-with-a-local-llm.md).

## Reading the results: which stage failed?

Combine the retrieval and the answer questions per query, and each case lands in one of four
cells.

| Relevant passage retrieved? | Answer | What it means |
|---|---|---|
| yes | grounded and on topic | the pipeline worked |
| yes | not grounded | the generator ignored or distorted good passages: fix the prompt or the model |
| no | declines | the retriever failed, the generator behaved: fix retrieval |
| no | answers anyway | both failed, and this is where invented answers come from |

Counted over a few hundred real queries, the share of each cell is a far better description of a
pipeline than one average. It also makes comparisons honest: when you try a new embedding model
or chunk size, the retrieval cells should move and the generator cells should not. If both move,
something else changed.

Keep the per-query probabilities, not just the pass or fail. Queries whose `grounded` score sits
near your threshold are the ones to read by hand, and they are usually where the rubric wording
needs work.

## Where a small judge stops being reliable

Being straight about the limits:

- **Numbers.** If an answer says "you have 44 days left" and the passage gives a date, checking it
  is arithmetic, and a one-pass model is weak there (0.584 on our arithmetic questions). Extract
  and compare numbers in code, as described on
  [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).
- **Long context.** jevos reads up to 8,192 tokens, and latency grows with length. Many retrieved
  chunks plus a long answer can exceed that; score passages one by one and split long answers.
- **Knowledge outside the passages.** The judge reads; it does not know. "Is the answer correct?"
  without passages is a question about the world, not about a text, and a 1B model is the wrong
  tool for it.
- **A lean toward yes.** On new kinds of question jevos made more wrong yeses than wrong noes, so
  a "grounded" pass deserves a bar above 0.5. The measurement is on
  [why a small LLM says yes](why-a-small-llm-says-yes.md).
- **English only.** For documents in other languages, use a multilingual judge.

For a final release decision on a hard domain, a large hosted judge on a sample of the same
queries is a reasonable check on the small one.

## Short answers to the questions that lead here

**How do I evaluate a RAG pipeline without reference answers?** Ask yes/no questions that only
need the query, the passages and the answer: passage relevance, groundedness and answer
relevance. None of them needs a gold answer.

**Can a local model evaluate RAG?** For reading questions about English text that fits in its
context, yes. It will not check facts that are not in the passages.

**What is the most useful single RAG metric?** There is not one. Splitting failures into
retrieval and generation is what makes the numbers actionable.

**How do I measure retrieval recall?** Only with labels saying which passages are relevant for
each query. Relevance questions give you precision and hit rate, not recall.

**How fast is it?** On our reference laptop a request of about 190 tokens read from scratch takes about 112 ms, and
extra questions on the same state cost a fraction of that.

**See also:** [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md),
[hallucination detection with a local LLM](hallucination-detection-with-a-local-llm.md) and
[building a yes/no test set for your own data](building-a-yes-no-test-set.md).

## Sources

- Latency and the three-question timing: our measurements on an Intel Core Ultra 7 255H with 16
  threads, reported in the [jev README](https://github.com/feder-cr/jev).
- Arithmetic accuracy and the yes/no error split: our 999-question test set, `jevos-q4_k_m`.
- Es, James, Espinosa-Anke and Schockaert, "Ragas: Automated Evaluation of Retrieval Augmented
  Generation", [arXiv:2309.15217](https://arxiv.org/abs/2309.15217), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The four-cell table is the part of RAG evaluation we would keep if we could keep
only one.*
