---
title: "AI decision making with probabilities and thresholds"
description: "Where a model should decide and where code should: the model returns probabilities, code owns thresholds, sums and audit, people get low confidence."
parent: "Guides"
nav_order: 6
---

# AI decision making with probabilities and thresholds

**AI decision making holds up best when the model does not make the decision: it reads the text
and returns probabilities, P(yes) for a yes/no question or one per option, and your code turns
them into an action with thresholds you chose.** Code also owns everything exact: dates, sums,
money, limits and the record of what happened. When the model says it cannot place an answer, or
the probability lands between your thresholds, the case goes to a person.

The split is about which mistakes you can see and fix. A threshold in code is a number someone
chose on labelled cases and can defend; a policy hidden in a prompt is a sentence whose effect
nobody measured.

This page is the division of labour, what a decision model hands back, one README request taken
to an action, when a person takes over, who answers for the outcome, and where the approach stops.

## Which part of a decision should the model make?

The reading, and only the reading: whether a message reports a missing item, sounds upset or asks
for money back, however it is worded. Everything after that belongs to code.

| Job | Owner |
|---|---|
| Read what the text says | the model |
| Turn a probability into yes or no | code, with a threshold you chose |
| Dates, sums, amounts, limits | code |
| Moving money, closing accounts | code, often with a person |
| The record of what happened | code |
| Answers the model cannot place | a person |

The arithmetic row is measured. On the README's six tasks, jevos-v4 scores 0.50 on Fraud points,
where risk signals add up to a level, against 0.69 for TypeSafe's hosted Jev (five of the six sets
helped choose the released checkpoint, so jevos's figures may be slightly optimistic). An earlier
test on jevos-v2, a fraud score from six rules, found 34% right, barely above always picking the
most common level, and confidently wrong. Hence the README's advice: compute sums in code and ask
the parts as yes/no questions, as on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

## What does a decision model hand back?

A number per allowed answer, never a sentence. jevos answers in TypeSafe Jev's wire format with
`output_tokens` 0, so there is nothing to parse:

- **`noul`** (yes/no): P(yes), from 0 to 1, compared with a threshold.
- **`choice`**: the most probable option, a probability per option and a `confidence`.
- **`score`**: the expected level `score`, the `legend`, a probability per level and a
  `confidence`. The README marks scores as early.

The README's score example shows why the confidence matters. Asked "How angry is the customer?" on
calm, annoyed, angry and furious, jevos returns a score of 1.25 with probabilities 0.32, 0.27, 0.25
and 0.16, and `confidence` 0.0; asked "Is the customer angry?" as yes/no, it gives 0.28. The 1.25
is not "slightly annoyed"; it is a spread with no peak, and a job for a person. How this kind of
model differs from a chat model is on [what is a decision model in AI?](what-is-a-decision-model.md).

## How does one request become a decision?

The README's refund request: a wireless mouse delivered 5 days ago, and the message "The box
arrived empty. This is the second time!"

```json
{
  "model": "jev-latest",
  "state": {"item": "wireless mouse", "delivered": "5 days ago",
            "customer_message": "The box arrived empty. This is the second time!"},
  "questions": {
    "refund": {"type": "noul", "instructions": "Our policy refunds items reported missing within 30 days of delivery. Should this customer get a refund?"},
    "upset": {"type": "noul", "instructions": "Is the customer upset?"},
    "wrong_item": {"type": "noul", "instructions": "Does the customer say they received the wrong item?"}
  }
}
```

The README's answers are 0.93, 0.83 and 0.04, and they play three different roles:

1. **`refund` at 0.93 is a candidate verdict.** The question carries the 30-day rule, so the model
   also did the date check. Fine for a demo; once money moves, keep the window in code and ask
   only whether the customer says the item was missing.
2. **`upset` at 0.83 never changes eligibility.** It changes priority, or who replies.
3. **`wrong_item` at 0.04 is information too.** A confident no rules out an exchange.

Then code acts and records who made each call:

```python
POLICY = {"version": "2026-10-12", "owner": "support lead", "yes": 0.9, "no": 0.2}  # placeholders

def decide(ans, order):
    p = ans["refund"]["noul"]
    rec = {"p": {k: v["noul"] for k, v in ans.items()}, "policy": POLICY["version"]}
    if order["days_since_delivery"] > 30:
        rec.update(action="propose_decline", decided_by="person")
    elif p >= POLICY["yes"]:
        rec.update(action="refund", decided_by="code threshold")
    elif p <= POLICY["no"]:
        rec.update(action="ask_for_details", decided_by="code threshold")
    else:
        rec.update(action="review", decided_by="person")
    rec["priority"] = "high" if ans["upset"]["noul"] > 0.5 else "normal"
    return rec
```

Choosing the values from your own labelled cases is on
[how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md), and the full
pipeline is on [refund request triage with a local LLM](refund-request-triage-with-a-local-llm.md).
What the sketch adds is `decided_by`: every record says whether a threshold or a person made the
call, and no refusal happens without a person.

## When should a person take over?

When the model says it cannot place the answer, when the probability falls between your two
thresholds, and when the outcome is adverse for someone, whatever the number says.

The first is measured. On choice questions, jevos-v2 was right on 95% of the answers with
confidence 0.75 or more, which covered 46% of the questions, and on 47% of those below 0.25. The
low end is where a person adds most. For yes/no questions a middle band does the same job, sized
as on [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

Confidence also flags missing facts, but not always. On four sets, jevos-v4's confidence told
answerable questions from ones missing a needed fact with an AUROC of 0.81 to 0.95 (0.5 means it
cannot tell), yet it still answered 0 to 42% of the fact-missing questions with 75% or more
confidence. When a fact must be there, ask for it directly, as on
[does an LLM know when a fact is missing?](does-an-llm-know-when-a-fact-is-missing.md).

## Who is accountable when an automated decision is wrong?

Whoever owns the threshold and the rule. The model returns a number; acting at 0.9 rather than 0.8
was a person's choice, on some date, on some cases. Make that visible:

- each threshold has an owner, a date, a case count and the model fingerprint `GET /health`
  reported when it was chosen;
- each decision record keeps a hash of the state, the questions, the probabilities, the policy
  version and who decided, as on [logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

Microsoft's documentation for its hosted Microsoft-Decision-1 draws the same line: for
consequential decisions about people, "use the model for decision support with meaningful human
review. Don't use it as the sole decision-maker." For the EU, our engineer's reading of GDPR
Article 22, not legal advice, is on
[GDPR and automated decision-making with an LLM](gdpr-and-automated-decision-making.md). A local
model changes who sees the text, not who is accountable.

## When is this approach the wrong one?

- **Every input is already a field.** Write the rule in code or an engine, as on
  [decision engine vs decision model](decision-engine-vs-decision-model.md).
- **The output must be text.** A reply or a summary needs a generative model.
- **The text is not English, or longer than the 8,192-token context.**
- **You need the most accurate answer and can send the text out.** On the README's six tasks
  TypeSafe's hosted Jev scores higher than jevos-v4 on every one.
- **You have no labelled cases.** Without a few hundred of your own, a threshold is a guess.

## Short answers to the questions that lead here

**What is AI decision making?** Using a model's output to choose an action. Here, the model returns
probabilities, and code with thresholds, plus a person for unclear cases, chooses the action.

**Should the AI make the final decision?** For routine, reversible actions code can act on the
probability. For adverse or consequential ones a person decides, with the model's answers as input.

**What does confidence 0 mean?** On a choice or a score, that the model cannot place the answer.
Route it to a person or ask a different question.

**Can the model check dates and add up points?** Do both in code. On a fraud score from six rules,
jevos-v2 was right 34% of the time, and confidently wrong.

**See also:** [what P(yes) means](what-p-yes-means.md),
[thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md)
and [combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## Sources

- Our measurements, published in the [jev README](https://github.com/feder-cr/jev): the six-task
  comparison, the missing-fact AUROC and confidence figures for jevos-v4, and the jevos-v2 fraud
  score and choice confidence figures. The refund and anger examples and their answers, the
  question types and `/health` are from the same README.
- Microsoft Learn, [Deploy and use Microsoft-Decision-1 in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision),
  fetched 2026-10-12: the quoted guidance. We have not measured jevos against Microsoft-Decision-1.
- The values in the code are placeholders.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a model that returns 0.93 for a refund
and leaves the decision to pay it to your code.*
