---
title: "LLM judge bias and how to control it"
description: "Position, length, yes-lean, self-preference and wording biases in LLM judges, and the controls that catch them: swaps and known-answer sets."
parent: "Evaluation"
nav_order: 7
---

# LLM judge bias and how to control it

**LLM judges have systematic biases: they favour an answer because of its position, because it
is longer, because the question invites a yes, or because it is written in their own style, and
their verdict moves when the criterion is reworded.** None of these shows up in a single
verdict, and all of them show up in a set of cases whose right answers you know. The controls are
correspondingly simple: swap the order, compare equal-length outputs, measure the judge on a
labelled set per criterion, and look at the direction of its errors, not only their number.

The bias that matters most for a yes/no judge is the one people least expect: a lean toward yes.
It is invisible in accuracy and calibration measured on familiar data, and it inflates every
pass rate you compute.

This page is a map of the biases with a detection test for each, what we measured on jevos, the
known-answer set that catches most of them, and what a judge bias does to the numbers you report.

## Which biases, and how do I detect each one?

| Bias | What it looks like | Detection test | Control |
|---|---|---|---|
| position | prefers the first (or second) of two answers | ask both orders; count verdicts that follow the position | swap and average; ties when orders disagree |
| length | prefers the longer answer | pairs that differ only by padding or repetition | compare similar lengths; add "repeats itself?" |
| yes-lean | says yes when unsure | mean P(yes) on cases whose answer is no | higher bar for yes; keep computing out of the judge |
| self-preference | prefers text in its own style | compare verdicts on outputs from different generators with the same labels | use a judge from another family; check with labels |
| wording | verdict moves with the phrasing | two phrasings of one criterion on the same cases | pick the stable phrasing; freeze it |

Zheng and colleagues, in "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", name position,
verbosity and self-enhancement biases, together with limited reasoning ability, as the main
limitations of LLM judges. The yes-lean and the wording effect are the two we add for yes/no
judges in particular.

## Position and length

Position bias only exists when the judge sees two outputs at once, and the fix is procedural: ask
in both orders. The formula and the tie rule are on
[pairwise comparison with a yes/no judge](pairwise-comparison-with-a-yes-no-judge.md).

Length bias survives the swap, because the longer answer is longer in both orders. In Zheng and
colleagues' test, where answers were made longer by repeating content, Claude-v1 and GPT-3.5
each failed 91.3% of the attacks and GPT-4 failed 8.7%. For a yes/no judge,
the practical controls are to compare outputs of similar length, to ask pointwise questions
("Does the reply answer the question in its first two sentences?") rather than "which is better",
and to add a negative criterion for padding.

## The lean toward yes: the one we measured

On 999 hand-written yes/no questions, exactly half with the answer yes, the first jevos made 152
mistakes by saying yes when the answer was no and 91 the other way. Accuracy (0.757) says nothing
about the direction; the error split does. These numbers are from the first jevos; jevos-v4
scores 78.9% on the same 999 questions, but its error split and per-kind numbers are not
published.

The better diagnostic is the mean P(yes) on questions whose right answer is no. For an ideal
judge it is 0. For the first jevos it ranged from 0.16 on tone questions to 0.59 on arithmetic. So the lean
is not a general optimism: it appears where the judge cannot work the answer out and the question
reads like a yes. The full breakdown, and why recalibrating did not remove it, is on
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

For evaluation the consequence is direct: a judge that leans toward yes reports inflated pass
rates, most of all on the criteria it is worst at. Two controls:

- **Keep computing out of the judge.** Criteria about sums, dates and thresholds go to code.
- **Raise the pass bar** on criteria where a false pass is costly. How far to raise it is a cost
  question, covered on
  [thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md).

## Self-preference

A judge from the same family as the generator may rate that generator's style higher; Zheng and
colleagues call this self-enhancement bias. jevos generates no text, so it is never judging its own
writing. That is not the same as having no style preference: a judge can still favour outputs that
resemble text it saw often. The only way to know is the known-answer test below, run separately on
outputs from each generator you compare.

## Wording

The same criterion phrased two ways can give different pass rates on the same outputs. This is
less a bias of the judge than a sign that the criterion is ambiguous, and it is cheap to test: run
two or three phrasings on a labelled sample and keep the one that agrees best with the labels.
The method is on [why wording changes an LLM's answer](why-wording-changes-the-answer.md).

## The control that catches most of them: a known-answer set

Every bias above is detectable with the same tool: a set of cases where you know the right answer
for each criterion.

1. Take 50 to 100 real outputs, labelled by people, per criterion. Include outputs from each
   generator you plan to compare, and pairs of similar and different lengths.
2. Run the judge on them in both orders where there are pairs.
3. Report, per criterion: accuracy, the split between wrong yes and wrong no, mean P(yes) on the
   no cases, and for pairs the share of order-dependent verdicts.
4. Re-run it whenever the judge, the rubric or the generator changes.

A criterion whose wrong answers are mostly in one direction needs a different threshold. A
criterion where the judge is near chance needs to leave the rubric. How to assemble the set, and
keep it clean, is on [building a yes/no test set](building-a-yes-no-test-set.md).

## What a biased judge does to your reported numbers

A judge's error does not average out when you compare systems. If it leans toward yes on a
criterion, both systems get inflated pass rates on it, and the difference between them can still
be real. But when one system produces the kind of output the judge is biased toward (longer,
first, in a familiar style), the bias becomes part of the measured difference. So report per
criterion, state the judge's own accuracy and error direction next to the results, and treat any
difference smaller than the judge's disagreement with your labels as noise.

## Short answers to the questions that lead here

**What is LLM judge bias?** A systematic preference of an LLM judge that is not about the quality
being judged: position, length, a lean toward yes, its own style, or the wording of the criterion.

**Does a yes/no judge have a bias toward yes?** The first jevos did on questions it could not work
out: 152 wrong yeses against 91 wrong noes on a balanced 999-question set (not published for
jevos-v4).

**How do I detect bias in my judge?** Run it on cases with known answers and look at the direction
of its errors per criterion, not only its accuracy.

**Does calibration remove bias?** Not a directional one. On the first jevos, a temperature and
bias fitted on our development split moved accuracy from 0.757 to 0.759.

**Is a judge from a different model family unbiased?** No, only free of self-preference toward the
generator. It still has position, length and yes-lean effects to check.

**See also:** [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md),
[LLM calibration explained with yes/no answers](llm-calibration-explained.md) and
[evaluation metrics for yes/no classifiers](evaluation-metrics-for-yes-no-classifiers.md).

## Sources

- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena",
  [arXiv:2306.05685](https://arxiv.org/abs/2306.05685) and
  [HTML version](https://arxiv.org/html/2306.05685v4), fetched 2026-09-29: the named biases, the
  repetitive-list attack and its failure rates.
- Error split, mean P(yes) on no-answer questions and the recalibration result: our 999-question
  test set, measured on the first jevos.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no model whose largest measured
bias is toward yes, published so you can set your bars with it in mind.*
