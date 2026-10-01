---
title: "When a small model is enough, and when it is not"
description: "A checklist for choosing a small local model or a large one: language, yes/no shape, reading vs computing, hard rules, latency and privacy."
parent: "Local and private AI"
nav_order: 9
---

# When a small model is enough, and when it is not

**A small model is enough when the input is English, the decision can be written as yes/no
questions, the answers are read from the text rather than computed, and speed, cost or privacy
matter more than the last few points of accuracy.** It is not enough when the decision depends
on applying a complex rule, doing arithmetic or date math, reading another language, or
producing anything other than yes/no or one option from a list. Most real systems have both kinds of decision, and the
useful answer is to split them: the small model reads, code computes, and a large model or a
person takes what is left.

The trap is choosing one model for a whole application. The same product has "is this email a
newsletter?", which a 1B model reads well, and "is this claim within the policy limits?",
which it does not. Deciding per question is what makes a small model usable.

This page is the checklist, then one section per question on it, with the measurements behind
each answer, and what to do when the answer is "sometimes".

## The checklist

| Question | Small model is fine | Use a large model, or code |
|---|---|---|
| What language is the text? | English | anything else |
| What shape is the answer? | yes/no, or one yes/no per option | free text, a list, a summary |
| Is the answer read or computed? | read from the text | sums, dates, counts, comparisons |
| Is it a hard written rule? | the rule is simple and in the question | many conditions, points, exceptions |
| What does a wrong answer cost? | a correction, a review | money, safety, a person's rights, alone |
| Does it need to be local or fast? | yes | no constraint |

One row in the right column is not a verdict against the small model. It usually means that
part of the decision belongs somewhere else.

## Is the text English, and can the decision be a yes/no question?

jevos reads English only. If your texts arrive in several languages, you can translate first,
which adds a step, a cost and possibly a third party; keep the questions in English; or use a
multilingual model. We have no measurements of jevos on other languages, and would not guess
at them. The options are laid out on
[using an English-only LLM with other languages](using-an-english-only-model-with-other-languages.md).

The yes/no shape fits more often than it seems. A label from a list becomes one question per
label; a level such as low, medium or high becomes "is it at least medium?" and "is it high?". jevos answers
`noul`, `choice` and `score` questions, the last two as one yes/no question per option or level;
scores are early (the most probable level is right 54% of the time on 2,350 held-out questions,
within one level 82%) and weak where the level is a sum of points. If the output has to be text, a summary, a reply, an extracted list, a small
yes/no model is the wrong tool, and a generative model is the right one.

## Is the answer read or computed?

This is the most important row. On 999 questions written after the model was finished:

- read from the text: stated facts 0.954, tone 0.938, intent 0.859, negation 0.858, not stated
  0.847;
- computed: numbers against thresholds 0.654, dates 0.598, arithmetic 0.584.

The computed kinds also carry a lean toward yes, 152 wrong yeses against 91 wrong noes in
total. The fix we recommend is a different split rather than a bigger model: extract the dates and amounts, and
compare them in code, as shown on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md). A
question such as "Does the customer say the parcel arrived late?" is a reading question; "Was
the parcel late?" may need a subtraction.

## Is it a hard written rule?

Rules sit in between. On the 999-question set, applying a rule was right 0.721 of the time. On
2,000 yes/no questions about three business policies none of the models was tuned on, jevos
was right 0.810 of the time and the hosted Jev 0.927, with the widest gap on additive point
scores. A rule with one condition written into the question works; a policy with points,
exceptions and cut-offs belongs in code, with the model answering only the factual questions
the code needs. The method is on
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

## What does a wrong answer cost?

A small model's mistakes are acceptable where they are cheap to correct: a ticket in the wrong
queue, a tag a person removes. Where a wrong yes pays out money, blocks a user or affects a
person's rights, the model can still be the first reader, but not the only decider. Use a
threshold above 0.5 for acting on yes, send the middle band to a person, and log what was
decided. [Human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md)
covers the pattern; a larger model does not remove the need for it either.

## Do latency, cost or privacy require a local model?

If they do, the small model is often the only option, and the job becomes shaping the questions
so it can answer them. On the reference laptop, an Intel Core Ultra 7 255H with 16 threads,
jevos answered a short request in 26 ms and a 190-token one in 112 ms; the hosted Jev took 344
and 345 ms from Europe on the same requests, network included. There is no per-token cost, and
the text stays on the machine. If none of these constraints applies, a hosted large model is a
reasonable default for the hard questions, and the trade-off is on
[local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md).

## When the answer is "sometimes"

Then use both. Ask the small model first; act when the probability is confidently high or low;
send the middle band to a large model or a person. Because jevos speaks the same wire format as
TypeSafe's Jev for yes/no, `choice` and `score` questions, the escalation can be the same request sent to a different
base URL. How to size the band and what it saves is on
[a model cascade: small model first, large model on doubt](model-cascade-small-model-first.md).
Measure the split on your own labelled cases, split by kind of question, before trusting it.

## Short answers to the questions that lead here

**When should I use a small language model?** For English yes/no decisions read from the text,
especially where latency, cost or privacy rule out a hosted API.

**When is a small model not enough?** When the decision needs arithmetic, dates, a complex
rule, another language, or a generated answer.

**Is a bigger model always more accurate?** On our 2,000 policy questions the hosted Jev was
ahead, 0.927 against 0.810. We have not compared the two on pure reading questions, so measure
on yours.

**Can I mix small and large models?** Yes. A cascade that escalates only the uncertain middle
keeps most calls local.

**How do I know for my own data?** Label a hundred or so real cases by kind of question and
measure. [Building a yes/no test set](building-a-yes-no-test-set.md) explains how.

**See also:** [small language models explained](small-language-models-explained.md),
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md)
and [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- Accuracy by kind of question and error direction: our 999-question set, `jevos-q4_k_m`.
- The 2,000-question policy comparison and latency on the two requests: our measurements,
  reported in the [jev README](https://github.com/feder-cr/jev).
- Supported question types and the score accuracy: the README.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a small model whose README lists
what it cannot do next to what it can.*
