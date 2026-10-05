---
title: "RAG faithfulness check with a local LLM"
description: "Check whether a RAG answer is faithful to its passages claim by claim, telling unsupported claims from contradicted ones, with a local yes/no model."
parent: "Evaluation"
nav_order: 2
---

# RAG faithfulness check with a local LLM

**A RAG answer is faithful when every claim in it is supported by the retrieved passages, and
the reliable way to check that is one claim at a time: split the answer into claims, then ask
for each one "is this supported by the passages?" and "do the passages contradict this?".** The
two questions are different on purpose. A claim can be unsupported without being contradicted
(the passages are silent), and that failure needs a different fix from a claim the passages
say is false. A local yes/no model answers both per claim in a fraction of a second on a CPU.

The non-obvious part is that asking about the whole answer at once hides the failure. An answer
with four correct sentences and one invented one reads as mostly supported, and a judge asked a
single question about it tends to agree. Claim by claim, the invented sentence has nowhere to
hide.

This page is why claims beat whole answers, how to get the claims, the request, the difference
between unsupported and contradicted, how to score, and what the check misses.

## Why check claim by claim?

"Is every claim in the answer supported?" is a compound question: it is really N questions
joined by AND, and a model answering it in one pass has to find the one weak link among many
strong ones. Splitting it turns one hard question into several easy ones, each of which is a
plain reading task: does this text say this thing? That is the kind of question small models
answer best. On our 999 test questions the first jevos was right 0.954 of the time on stated facts and
0.893 on paraphrases, against 0.721 on applying a rule (per-kind numbers for jevos-v4 are not
published). The general argument is on
[one condition per question](one-condition-per-question.md).

This is also how published metrics define it. Ragas computes faithfulness as the number of claims
in the response supported by the retrieved context divided by the total number of claims.
FActScore, for long-form text checked against a knowledge source, breaks a generation into
atomic facts and reports the share that are supported.

## Where do the claims come from?

jevos answers yes/no questions and does not generate text, so it cannot split an answer into
claims itself. You have three honest options:

- **Sentences.** Split the answer into sentences in code. Crude, free, and good enough when
  answers are short and each sentence says one thing.
- **Your generator.** Ask the model that wrote the answer to also return it as a list of claims.
  That costs generated tokens, but only once per answer.
- **A larger model offline.** For a fixed test set, extract claims once with any capable model,
  store them, and re-run only the cheap yes/no checks on every change after that.

Whichever you choose, each claim should be one statement that can be true or false on its own.
"The store accepts returns within 30 days and refunds shipping" is two claims.

## The request: passages in the state, one claim per question

The passages go in `state`, where they are read once. Each claim becomes its own pair of
questions, with the claim quoted in the question text.

```json
{
  "model": "jev-latest",
  "state": {
    "passages": [
      "Unworn items in their original box can be returned within 30 days of delivery.",
      "Return shipping is paid by the customer unless the item was faulty."
    ]
  },
  "questions": {
    "c1_supported":    {"type": "noul", "instructions": "Do the passages say that unworn items can be returned within 30 days?"},
    "c1_contradicted": {"type": "noul", "instructions": "Do the passages say something that makes this false: unworn items can be returned within 30 days?"},
    "c2_supported":    {"type": "noul", "instructions": "Do the passages say that the store refunds return shipping for every return?"},
    "c2_contradicted": {"type": "noul", "instructions": "Do the passages say something that makes this false: the store refunds return shipping for every return?"}
  }
}
```

Each question comes back as its own probability. Here the second claim is the one to watch: the
passages say the customer pays unless the item was faulty, so a faithful judge should give it a
low `c2_supported` and a high `c2_contradicted`. Quoting the claim inside the question, rather
than referring to "claim 2" in the state, keeps each question self-contained; pointing at items by
number is an extra step of lookup we have not measured.

Many claims about the same passages can share one request, because extra questions on a state
that has been read cost little. For very long answers, batch the claims into a few requests
rather than one huge one.

## Unsupported and contradicted are different failures

| supported | contradicted | Reading |
|---|---|---|
| high | low | faithful claim |
| low | high | the answer states something the passages say is false |
| low | low | the passages are silent: the claim came from the generator's own knowledge, or was invented |
| high | high | the judge is inconsistent on this claim: read it by hand |

The contradicted case is the serious one for users, because it is wrong by the system's own
sources. The silent case depends on your product. Some assistants are allowed to add general
knowledge; a support bot quoting policy is not. Decide which you are before you set thresholds,
and count the two cells separately in reports.

The fourth row is a free consistency check. A claim that scores high on both questions is one
the judge does not understand, and those are worth collecting: they are usually claims with
numbers, dates or a negation buried in them. Negation is a known trap; on that test set the first
jevos scored 0.858 on negation questions, and phrasing advice is on
[negation in yes/no questions](negation-in-yes-no-questions.md).

## From claims to a faithfulness score

- **Per answer:** the share of claims whose `supported` clears your threshold, which matches the
  Ragas definition. Add a hard fail if any claim is contradicted.
- **Per system:** the mean per-answer score over a test set, plus the rate of answers with at
  least one contradicted claim. The second number is the one users feel.
- **Threshold:** raise the bar for "supported" above 0.5. the first jevos leaned toward yes on questions it
  could not work out, measured on [why a small LLM says yes](why-a-small-llm-says-yes.md), and a
  lenient bar turns that lean into inflated faithfulness.

## What the check misses

- **Claims that need arithmetic.** "That leaves you 12 days" against a passage with two dates is a
  subtraction, not a reading question, and a one-pass model is weak at it. Compare numbers in
  code.
- **Bad claim splits.** If the extraction step drops a claim, no check will see it. Spot-check
  that claims cover the answer.
- **Passages that are wrong.** A faithful answer repeats its sources, including their mistakes.
  Faithfulness is not truth; the difference is covered on
  [hallucination detection with a local LLM](hallucination-detection-with-a-local-llm.md).
- **Long passages.** jevos has an 8,192-token context; long retrieved sets need to be checked in
  parts, with a claim counted as supported if any part supports it.

## Short answers to the questions that lead here

**What is faithfulness in RAG?** Whether the claims in a generated answer are supported by the
retrieved passages. Ragas scores it as supported claims divided by all claims.

**Why not ask one question about the whole answer?** Because one invented sentence among several
correct ones is easy to miss. Claim-level questions turn it into several easy reading tasks.

**Can jevos extract the claims?** No. It returns probabilities and generates no text. Split
sentences in code or have a generator list the claims.

**What is the difference between unsupported and contradicted?** Unsupported means the passages
do not say it; contradicted means they say the opposite. Report them separately.

**Is a faithful answer a correct answer?** Only if the passages are correct. Faithfulness
measures consistency with the sources, not with the world.

**See also:** [RAG evaluation with yes/no questions](rag-evaluation-with-yes-no-questions.md),
[LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md) and
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## Sources

- Accuracy by kind of question (stated fact, paraphrase, rule, negation) and the yes/no error
  split: our 999-question test set, run on the first jevos.
- Ragas faithfulness metric definition,
  [docs.ragas.io](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/),
  fetched 2026-09-29.
- Min et al., "FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text
  Generation", [arXiv:2305.14251](https://arxiv.org/abs/2305.14251), fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a local model that answers yes/no
questions and writes nothing, which is why the claim splitting has to happen somewhere else.*
