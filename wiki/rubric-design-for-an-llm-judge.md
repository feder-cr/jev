---
title: "Rubric design for an LLM judge"
description: "How to write evaluation criteria an LLM judge can score: observable properties, one per question, positive and negative criteria, gates and weights."
parent: "Evaluation"
nav_order: 5
---

# Rubric design for an LLM judge

**A good rubric for an LLM judge is a list of observable properties, each one a yes/no question
that someone could answer by pointing at the text: "Does the reply give the return deadline?",
not "Is the reply helpful?".** Each criterion tests one thing, says which direction is good,
carries its own standard inside the question, and is either a gate (must pass) or a weight
(counts toward a score). A rubric built this way can be scored by a small local judge, and its
results say which property failed, not only that something did.

The part people skip is testing the rubric itself. Two people reading "Is the tone
professional?" will disagree on some of your outputs, and a judge will disagree with both.
A criterion that humans cannot agree on is not a criterion yet, whatever model scores it.

This page is how to turn vague criteria into observable ones, why each rubric needs criteria in
both directions, gates versus weights, what to leave out of a rubric, and how to check a rubric
before you trust its numbers.

## From vague to observable

A vague criterion asks the judge for an opinion. An observable one asks it to find something.

| Vague | Observable rewrite |
|---|---|
| Is the answer helpful? | Does the reply tell the customer what to do next? |
| Is it accurate? | Is every claim in the reply supported by the policy text? |
| Is it concise? | Does the reply answer the question in its first two sentences? |
| Is the tone good? | Is the reply polite? / Does the reply blame the customer? |
| Does it follow the policy? | Does the reply offer a refund for an item reported missing? |
| Is it complete? | Does the reply mention the return deadline? / the return address? |

Three rules produce most of these rewrites:

1. **Name the thing to look for.** "Mentions the return deadline" can be checked; "complete"
   cannot.
2. **One property per criterion.** "Polite and accurate" is two criteria. Joined criteria fail for
   either reason and you cannot tell which; the general case is on
   [one condition per question](one-condition-per-question.md).
3. **Say it as a question about the text.** "Does the reply say..." keeps the judge reading
   instead of reasoning about the world.

The same habits make any yes/no question easier for a model; the full list is on
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## Criteria in both directions

A rubric with only positive criteria rewards outputs that say everything. A reply that promises a
refund, a replacement and a discount passes "offers a solution" three times over. Add the
properties that must be absent:

- positive: "Does the reply tell the customer what happens next?"
- negative: "Does the reply promise something the policy does not allow?"
- negative: "Does the reply ask for information the customer already gave?"

Phrase negative criteria as the presence of a bad thing, not the absence of a good one, and flip
them in code (use 1 minus P(yes)) when you add them to a score. "Does the reply fail to mention
the deadline?" is a negated question, and negation is harder to read: jevos scored 0.858 on
negation questions against 0.954 on stated facts in our 999-question test set. "Does the reply
mention the deadline?", flipped in code, asks the same thing in the easier form.

## Put the standard inside the criterion

A criterion like "Does the reply follow the refund policy?" depends on a policy the judge has
never seen. Write the rule into the question:

```json
{
  "model": "jev-latest",
  "state": {
    "customer_message": "The box arrived empty. I want my money back.",
    "reply": "I'm sorry. Since the item was reported missing within 30 days, I've issued a full refund."
  },
  "questions": {
    "policy_ok": {"type": "noul", "instructions": "Our policy refunds items reported missing within 30 days of delivery. Does the reply offer a refund that this policy allows?"},
    "next_step": {"type": "noul", "instructions": "Does the reply tell the customer what happens next?"},
    "blames":    {"type": "noul", "instructions": "Does the reply blame the customer for the problem?"}
  }
}
```

If you are moving a rubric from TypeSafe's Jev, note that on a yes/no question jevos accepts
Jev's optional `criteria` field but does not read it: the standard has to be in `instructions`. Why the rule belongs in the
question, and how far a small model can apply one, is on
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

## Gates and weights

Not every criterion should count the same, and averaging all of them hides the one that matters.

- **Gates** are criteria where one failure makes the output unacceptable: contradicts the source,
  promises something forbidden, leaks personal data. An output that fails a gate fails, whatever
  its other scores.
- **Weights** are criteria that make an output better or worse: tells the next step, answers
  first, polite. Combine them as a weighted mean of the probabilities.

Keep weights simple and few. Once you have more than three or four levels of importance, nobody
can explain why an output scored 0.71 rather than 0.74. Report the per-criterion pass rates next to
the combined score; the combined score is for ranking, the per-criterion rates are for fixing.
Doing the AND of several gates in code, instead of one compound question, is covered on
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## What to leave out of a rubric

- **Criteria that need computing.** "Is the refund amount correct?" is arithmetic, and jevos scored
  0.584 on arithmetic questions. Check amounts, dates and counts in code.
- **Criteria that need outside knowledge.** "Is the medical advice sound?" asks about the world.
  A small judge reads the text; it does not know medicine. Use a large model or an expert.
- **Style preferences you cannot state.** If you cannot write two example outputs, one passing
  and one failing, the criterion is not ready.
- **Scores from 1 to 10.** jevos answers `score` questions with 2 to 10 levels, early (54% on
  held-out score questions), and with any judge a scale mixes several properties. If you need levels, write them as threshold
  questions; see [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).

## Test the rubric before trusting it

1. **Write two examples per criterion**, one that clearly passes and one that clearly fails. If
   the judge gets either wrong, rephrase before scaling up.
2. **Label 50 to 100 real outputs by hand** on every criterion, ideally with two people. Where the
   two people disagree often, the criterion is ambiguous: sharpen it.
3. **Compare the judge with the labels per criterion**, not overall. A rubric can be excellent on
   tone and useless on policy, and one average will hide that.
4. **Try two phrasings of each criterion.** If the pass rate moves a lot between them, the
   criterion is sensitive to wording, and the results depend on your phrasing more than on the
   outputs.
5. **Freeze it.** Once a rubric is used to compare systems, changing a criterion's wording breaks
   the comparison. Version the rubric like code.

## Short answers to the questions that lead here

**What is a rubric for an LLM judge?** A list of criteria the judge scores for each output. The
most reliable criteria are yes/no questions about observable properties of the text.

**How many criteria should a rubric have?** As many as there are properties you would act on,
often five to ten. Each should be separately worth reporting.

**Should I use a 1 to 10 scale?** Prefer separate yes/no criteria. A scale mixes properties, and
the judge's numbers cluster on a few favourites.

**How do I write negative criteria?** As the presence of a bad thing ("Does the reply blame the
customer?"), then flip the probability in code.

**How do I know my rubric is good?** Label a sample by hand, compare the judge per criterion, and
rewrite the criteria that people or the judge disagree on.

**See also:** [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md),
[pairwise comparison with a yes/no judge](pairwise-comparison-with-a-yes-no-judge.md) and
[why wording changes an LLM's answer](why-wording-changes-the-answer.md).

## Sources

- Accuracy on negation, stated-fact and arithmetic questions: our 999-question test set, run on
  `jevos-q4_k_m`.
- The `criteria` field, `instructions`, and the `score` answers and their accuracy: the
  [jev README](https://github.com/feder-cr/jev).

---

*From the notes of [jev](https://github.com/feder-cr/jev), which accepts a yes/no rubric's
`criteria` field and ignores it, so the standard always has to live in the question.*
