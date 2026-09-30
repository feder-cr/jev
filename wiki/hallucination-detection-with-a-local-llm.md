---
title: "Hallucination detection with a local LLM"
description: "What a small local LLM can and cannot detect: grounded hallucinations against a source are checkable, open-world factual errors are not."
parent: "Evaluation"
nav_order: 3
---

# Hallucination detection with a local LLM

**A small local LLM can detect a hallucination when there is a source to check it against: it
reads the output and the source and answers whether the source supports each statement.** That
covers summaries, RAG answers, extracted fields and support replies built from a policy. It
cannot tell you whether a statement is true about the world when no source is given, because
a model of about 1B parameters does not hold enough reliable knowledge, and jevos in particular
is built to answer questions about the text it is given, not from memory.

So the useful question is not "can it detect hallucinations?" but "do I have the source?". If
you do, a yes/no check per statement is cheap enough to run on every output. If you do not, the
right tools are retrieval plus a grounded check, a large model with search, or a person.

This page is the two kinds of hallucination, the grounded checks that work, a cheap check for
invented names and numbers, what to do when there is no source, and the limits.

## Two kinds of hallucination, and which one is checkable

| | Grounded (against a source) | Open-world (against reality) |
|---|---|---|
| example | a summary says the meeting moved to Friday; the email says Thursday | an answer says a law was passed in 2019 |
| what the checker needs | the output and the source | knowledge of the world, or a search |
| a small local model | yes: it is a reading question | no: it would be guessing |
| typical fix | regenerate, or send for review | retrieval, a larger model, a human |

A grounded check asks what a text says. An open-world check asks what is true. The first is the
top of every accuracy table we have measured: on our 999 test questions, jevos was right 0.954
of the time on facts stated in the text. The second is not in any of our tables, because it is
not the job the model was built for. The broader case for matching the task to the model size
is on [when a small model is enough, and when it is not](when-a-small-model-is-enough.md).

## Checking an output against its source

Put the source and the output in `state` and ask about each statement the output makes. Splitting
the output into statements is covered on
[RAG faithfulness checks with a local LLM](rag-faithfulness-check-with-a-local-llm.md); the same
method works for a summary, a meeting note or a generated reply.

```json
{
  "model": "jev-latest",
  "state": {
    "source": "Hi all, the planning meeting moves from Tuesday to Thursday at 10:00. Same room.",
    "summary": "The planning meeting has moved to Friday at 10:00 in the same room."
  },
  "questions": {
    "day_supported":  {"type": "noul", "instructions": "Does the source say the meeting moved to Friday?"},
    "room_supported": {"type": "noul", "instructions": "Does the source say the meeting stays in the same room?"}
  }
}
```

Each statement gets its own probability, so the report says which part of the summary was
invented, not only that something was.

## A cheap first pass: names and numbers that appear from nowhere

Many hallucinations are specific: a person, an order number, an amount, a date, a product name
that is not in the source. You can catch a large share of them without splitting anything:

1. In code, pull the specific items out of the output: numbers, dates, capitalised names,
   identifiers. A regex and a date parser do most of it.
2. Check the easy ones in code. If "4,200" is in the output and not in the source, flag it; you
   do not need a model to compare two strings.
3. For items that may be paraphrased ("next Thursday" against a date, "the finance lead" against
   a name), ask the model: "Does the source mention the finance lead?"

This split keeps each tool on what it does well. String and number comparison is exact in code,
and weak in a one-pass model: jevos scored 0.584 on arithmetic questions and 0.598 on dates,
measured on [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md). Recognising
that two phrasings refer to the same thing is where the model helps.

## What about outputs with no source?

Being straight about the limit: a small local model is the wrong tool for checking open-world
facts, and a probability it returns about one should not be read as evidence. Options that work:

- **Give it a source.** Retrieve documents about the claim first, then run the grounded check.
  This turns an open-world question into a reading question, at the cost of a retrieval step
  whose own quality you then have to measure.
- **Use a large model with search** for claims that matter, and keep the small one for the
  grounded checks around it.
- **Compare samples.** SelfCheckGPT's idea is that when a model knows a fact, several sampled
  answers agree, and when it hallucinates, they diverge. Checking whether one sentence is
  consistent with another sample is again a reading question. Using a small yes/no model for that
  comparison step is a design we have not tested; we mention it because it keeps the
  knowledge-heavy part in the model that has the knowledge.
- **Send it to a person** when the claim is high stakes and none of the above is available.

## Designing the questions so the check is trustworthy

- **Ask whether the source says it, not whether it is true.** "Does the source say the meeting is
  on Friday?" is a reading question. "Is the meeting on Friday?" invites the model to guess.
- **Ask separately whether the source mentions it at all.** A gate question such as "Does the
  source say which day the meeting is?" separates "the source is silent" from "the source says
  otherwise". jevos scored 0.847 on not-stated questions; the pattern is on
  [ask whether the text says it at all](ask-whether-the-text-says-it.md).
- **Set the bar for "supported" above 0.5.** On new kinds of question jevos makes more wrong
  yeses than wrong noes (152 against 91 on our test set). For a hallucination detector, a wrong
  yes is a missed hallucination.

## Limits of this approach

- A grounded check trusts the source. If the source is wrong, a faithful output is wrong too.
- It inherits the claim split. A statement that never became a question is never checked.
- It is English only, with an 8,192-token context. Long sources need to be checked in parts.
- It has not been measured by us on a public hallucination benchmark. Before relying on it, build
  a small labelled set from your own outputs, half with planted errors, and measure.

## Short answers to the questions that lead here

**Can a small LLM detect hallucinations?** Against a source, yes: it is a reading question. Against
the world with no source, no.

**What is a grounded hallucination?** A statement in a generated text that the text's own source
does not support or contradicts, such as a wrong day in a meeting summary.

**How do I catch invented numbers?** Extract them in code and look them up in the source. Only
ask the model about items that may be paraphrased.

**Can I run hallucination checks on every output?** With a local model, yes: a request of about
190 tokens takes about 112 ms on our reference laptop, and no text leaves the machine.

**What should I use for open-domain fact checking?** Retrieval followed by a grounded check, or a
large model with search, with a person for high-stakes claims.

**See also:** [RAG evaluation with yes/no questions](rag-evaluation-with-yes-no-questions.md),
[small language models explained](small-language-models-explained.md) and
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Sources

- Accuracy by kind of question and the yes/no error split: our 999-question test set, run on
  `jevos-q4_k_m`.
- Latency: our measurement on an Intel Core Ultra 7 255H, reported in the
  [jev README](https://github.com/feder-cr/jev).
- Manakul, Liusie and Gales, "SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for
  Generative Large Language Models", [arXiv:2303.08896](https://arxiv.org/abs/2303.08896),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model that answers questions about
the text you send it and has nothing useful to say about texts you do not.*
