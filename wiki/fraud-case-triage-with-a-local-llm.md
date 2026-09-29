---
title: "Fraud case triage with a local LLM"
description: "Use a local yes/no LLM to read the free text of claims and disputes and order the fraud review queue, never to block a customer on its own."
parent: "Use cases"
nav_order: 11
---

# Fraud case triage with a local LLM

**A small local LLM can help a fraud team decide which cases to look at first, by reading the
free text of a claim and answering yes/no questions about it: does the story contradict the
order record, does the claimant refuse to give details, does the message push for speed.** It
should not decide that anyone is a fraudster. Use its probabilities to sort and annotate the
review queue, keep the fraud score in code, and let a person make every decision that costs a
customer money or access.

The reason is not only caution. The part of fraud work a yes/no model is good at, reading what
a message says, is different from the part it is bad at, adding up signals against a cut-off.
And the text it reads is written by the person being screened, who can phrase it to pass.

This page is what the model can read in a case, why the score stays in code, a request, how to
turn answers into a queue order, why the model is a first screen and not a security control,
and the rules on automated decisions that apply either way.

## What can a small model read in a fraud case?

Most fraud signals that live in structured data are already handled by the systems that own
that data: velocity checks, device and address matching, chargeback history. What those
systems cannot read is the narrative. A dispute, a warranty claim, an insurance note or a
support chat carries signals that only exist as sentences:

- the claimant describes an item or a date that does not match the order record in the state,
- the story changes between two messages in the same thread,
- the writer declines to provide a photo, a receipt or a serial number when asked,
- the message insists on a refund to a different payment method or account,
- the message presses for speed or threatens to escalate before anything has been checked.

Each of these is a reading question, and reading is where a small model is strongest. On our
999-question test set written after training, stated facts were answered right 0.954 of the
time and intent 0.859. Contradiction between a message and a record is a comparison of two
stated facts, which is the same skill.

## Why does the fraud score itself belong in code?

Many fraud processes end in a points model: three points for a new account, two for a mismatch,
four for a high amount, review above ten. It is tempting to paste that rule into a question and
ask the model whether the case scores above ten. Do not.

On 2,000 yes/no questions about three business policies it had never seen, jevos was right
0.811 of the time against 0.927 for TypeSafe's hosted Jev, and the gap was largest on exactly
this shape: additive point scores, where several signals are summed and compared with a
cut-off. It was the weakest kind of rule in that comparison. On the 999-question set,
arithmetic questions were right 0.584 of the time, close to a coin.

So split the work. Ask the model one question per signal, turn each probability into a flag or
a weight in code, and sum in code. The detail of that split is on
[put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md) and
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

## A request for one case

Put the record and the narrative in the same `state`, so the model can compare them:

```json
{
  "model": "jev-latest",
  "state": {
    "order": {"item": "noise-cancelling headphones", "delivered_to": "billing address"},
    "claim_messages": [
      "The parcel never arrived, I need the money back today.",
      "I already told you, the box was empty when I opened it."
    ]
  },
  "questions": {
    "story_changes":  {"type": "noul", "instructions": "Do the claim messages give two different accounts of what happened?"},
    "pushes_speed":   {"type": "noul", "instructions": "Does the claimant demand that the refund happen immediately?"},
    "other_account":  {"type": "noul", "instructions": "Does the claimant ask for the refund to go to a different account or payment method?"},
    "gives_evidence": {"type": "noul", "instructions": "Does the claimant offer a photo, receipt or other evidence?"}
  }
}
```

Each question comes back as its own `noul`. Note the last one is phrased positively and flipped
in code if you want "no evidence" as the signal, which avoids a negated question.

## From probabilities to a review queue

The output of this step is an order, not a verdict:

1. Turn each probability into a flag with a threshold you chose on labelled past cases.
2. Combine the flags with your structured signals in code, as a weighted sum or with
   [AND, OR and NOT in code](combining-yes-no-answers-and-or-not.md).
3. Sort the queue by the combined value, and show the reviewer which flags fired and their
   probabilities.
4. Cases with no flags go through your normal flow. Nothing is refused because of the text alone.

Because the model leans toward yes on questions it cannot work out (152 wrong yeses against 91
wrong noes on the 999 set), a flag from a single question is weak evidence. Several independent
flags on the same case are stronger. If a wrong flag delays an honest customer, set the flag
threshold above 0.5; the reasoning is on
[thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).

## Being straight about the limit: a first screen, not a security control

A fraud screen reads text written by the adversary. Someone who knows or guesses that a model
reads their claim can write a calm, consistent, evidence-rich story, and the questions above
will answer the way they want. They can also put instructions in the text. OWASP's 2025 entry
on prompt injection describes indirect injection, where content the model processes alters its
behaviour, and says that "it is unclear if there are fool-proof methods of prevention for
prompt injection".

So treat the model as a way to spend reviewer time better on the cases that do reach a person,
not as a gate a fraudster has to get through. The controls that stop fraud stay where they are:
identity and payment checks, limits, holds, and people. OWASP's guidance on overreliance makes
the same point from the other side: it recommends human oversight and fact-checking "especially
for critical or sensitive information". The mechanics of a review band are on
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

## Rules on automated decisions apply either way

If you operate in the UK or the EU, a decision that refuses a customer without a person looking
at it may fall under Article 22 of the GDPR. The ICO's guidance describes it as a restriction on
decisions "based solely on automated processing" with legal or similarly significant effects,
lists exceptions (one of them is authorisation by law, with fraud prevention as an example),
and describes safeguards such as the right to obtain human intervention and to challenge the
decision. This page is not legal advice; the point for design is that a queue-ordering model
with a person deciding is a very different system from one that refuses on its own. More on
[GDPR and automated decision-making](gdpr-and-automated-decision-making.md).

Log what the model was asked and what it answered for every case, so a reviewer or an auditor
can see why a case was ranked high.

## Short answers to the questions that lead here

**Can an LLM detect fraud?** It can read free-text signals that often come with fraud, such as
a changing story or pressure for speed. It cannot tell a careful fraudster from an honest
customer on text alone, so use it to prioritise review.

**Should the model block transactions?** No. Use its answers to order and annotate the review
queue, and keep blocking decisions with your existing controls and people.

**Can I ask the model to compute a fraud score?** Keep sums and cut-offs in code. Additive point
scores were the weakest case against Jev in our 2,000-question comparison.

**Why run it locally?** Claims contain personal and financial details. A local model reads them
on your own machine, on a CPU, with no per-token bill.
**See also:** [prompt injection screening with a small model](prompt-injection-screening-with-a-small-model.md),
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md) and
[refund request triage with a local LLM](refund-request-triage-with-a-local-llm.md).

## Sources

- Our measurements: the 2,000-question policy comparison (jevos 0.811, Jev 0.927, largest gap on
  additive point scores) from the [jev README](https://github.com/feder-cr/jev); accuracy by kind
  and the 152 to 91 error split from our 999-question test set on `jevos-q4_k_m`.
- OWASP GenAI Security Project,
  [LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/),
  fetched 2026-09-29.
- OWASP GenAI Security Project,
  [LLM09:2025 Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/)
  (overreliance and human oversight), fetched 2026-09-29.
- ICO, [rights related to automated decision making including profiling](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/individual-rights/rights-related-to-automated-decision-making-including-profiling/),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The additive-score weakness is ours, measured, and it is why the sum stays in code.*
