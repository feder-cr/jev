---
title: "LLM as a judge on a CPU"
description: "Run LLM-as-a-judge checks locally: write each evaluation criterion as a yes/no question and score outputs on a CPU with probabilities, not verdicts."
parent: "Guides"
nav_order: 4
---

# LLM as a judge on a CPU

**An LLM judge does not have to be a large model behind an API: if each evaluation criterion is
a yes/no question, a small local model can score it on a CPU and return a probability per
criterion.** "Does the answer use only facts from the context?", "Does it answer the question
that was asked?", "Is the tone polite?": each becomes one question about the same record, the
record is read once, and the scores come back in a fraction of a second with no data leaving
the machine.

What you give up is judgment on hard reasoning. A 1B model will not tell you whether a proof is
correct. What you keep is the bulk of what evaluation pipelines actually check, which is
whether an output does or does not have a property you can name.

This page is how to turn a rubric into questions, the request, how to aggregate the
probabilities, which criteria a small judge is good and bad at, and what it costs.

## Why yes/no criteria make a better judge

The common LLM-as-a-judge prompt asks for a score from 1 to 10 and a justification. Two
problems follow: the score is generated text, so it has to be parsed and it clusters on a few
favourite numbers, and one number mixes several criteria that you then cannot tell apart.

Splitting the rubric into yes/no criteria fixes both. Each criterion has one answer, each
answer is a probability you can threshold or average, and when an output fails you know which
criterion it failed. The same advice appears in most evaluation guides for large judges; with a
small one it is not a refinement but the condition for it to work at all.

## The request

Put everything the judge needs in `state`: the input, the context the answer was supposed to
use, and the answer.

```json
{
  "model": "jev-latest",
  "state": {
    "question": "Can I return shoes I have already worn outside?",
    "context": "Returns are accepted within 30 days for unworn items in their original box.",
    "answer": "Yes, you can return any shoes within 30 days for a full refund."
  },
  "questions": {
    "grounded":  {"type": "noul", "instructions": "Is every claim in the answer supported by the context?"},
    "on_topic":  {"type": "noul", "instructions": "Does the answer respond to the question that was asked?"},
    "contradicts": {"type": "noul", "instructions": "Does the answer say something the context contradicts?"},
    "polite":    {"type": "noul", "instructions": "Is the tone of the answer polite?"}
  }
}
```

That answer is on topic and polite, and it is wrong, because the context excludes worn shoes.
Asking both "grounded" and "contradicts" is deliberate: the same failure seen from two sides
gives you a consistency check on the judge itself.

## From probabilities to a score

Keep the per-criterion probabilities. They are the evaluation.

- **Pass/fail per criterion**: threshold each at 0.5, or higher for the criteria where a false
  pass is expensive.
- **A score per output**: the mean of the probabilities, with the negative criteria
  ("contradicts") flipped to 1 minus p first.
- **A score per system**: the pass rate of each criterion over your test set. Comparing two
  prompts or two models criterion by criterion is far more informative than comparing two
  averages.

The probabilities are calibrated well enough to average. On the natural yes/no questions of our
held-out split the calibration error is 0.009, meaning that across many answers of about 0.8,
about 80% are right.

## Which criteria a small judge gets right

On 999 yes/no questions written after training, labelled by the kind of reasoning they need:

| Criterion shape | Accuracy |
|---|---|
| is a fact stated in the text | 0.954 |
| what is the tone | 0.938 |
| do two phrasings say the same thing | 0.893 |
| what does the writer intend | 0.859 |
| does the text say something is not so | 0.858 |
| does the text not state it at all | 0.847 |
| is a number over a threshold | 0.654 |
| is an arithmetic result right | 0.584 |

Groundedness, contradiction, tone, relevance, refusal, "does it mention X": these are reading
questions, and the top of the table. Checking a calculation, a date or a count in the output is
the bottom, and for those a small judge is close to a coin that leans toward yes. Check numbers
in code; the detail is on [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).

## What it costs

On an Intel Core Ultra 7 255H with 16 threads, a 190-token record takes about 112 ms and each
additional criterion on the same record costs a fraction of that, because the record is read
once. The README's three-question example takes about 66 ms against 49 ms for one question.

So a test set of 1,000 outputs with five criteria is a few minutes on a laptop, costs nothing
per token, and can run in CI on every prompt change. A hosted judge on the same set means 1,000
round trips of about 340 ms each before the model does any work, plus the bill, plus sending
your outputs to someone else.

## When to use a large judge instead

- Criteria that need reasoning or knowledge beyond the text: "is this code correct", "is this
  medical advice sound".
- Languages other than English.
- The final evaluation of a release, where the extra accuracy is worth the cost. On 2,000
  rule-based questions the hosted Jev was right 0.927 of the time against 0.810 for jevos.

A common split is the small judge on every commit and the large one on the release candidate.
For retrieval pipelines, the same criteria applied per passage and per answer are on
[RAG evaluation with yes/no questions](rag-evaluation-with-yes-no-questions.md), and how to turn a
vague rubric into checkable criteria is on [rubric design for an LLM judge](rubric-design-for-an-llm-judge.md).

## Short answers to the questions that lead here

**What is LLM as a judge?** Using a language model to evaluate the outputs of another model, or
of a system, against criteria written in natural language.

**Can a small local model be an LLM judge?** For yes/no criteria about properties you can read
in the text, yes. For hard reasoning or maths, no.

**How do I avoid parsing the judge's answer?** Use a model that returns a probability. jevos
generates no text.

**Can it run in CI?** Yes. It needs only a CPU (x86-64 with AVX2, or Apple silicon), and `jev decide`
answers a request file without a server.

**Are the scores calibrated?** On our natural yes/no held-out questions, the calibration error
is 0.009.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md)
and [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Sources

- Latency, the three-question timing and the 2,000-question comparison: the
  [jev README](https://github.com/feder-cr/jev).
- Calibration error: our held-out split, 6,397 natural yes/no questions, `jevos-q8_0`.
- Accuracy by kind of question: our 999-question test set, run on `jevos-q4_k_m`.
- Background on the method: [LLM-as-a-Judge on Wikipedia](https://en.wikipedia.org/wiki/LLM-as-a-Judge).

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The shoe return example is the failure a judge exists to catch: fluent, polite,
on topic, and wrong.*
