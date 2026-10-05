---
title: "Lead qualification with yes/no questions"
description: "Qualify inbound leads with yes/no questions on budget, timeline, decision maker and fit, compare numbers in code, and leave the call to a person."
parent: "Use cases"
nav_order: 10
---

# Lead qualification with yes/no questions

**A yes/no model can read an inbound lead (a contact form, a first email, call notes) and answer
the qualification questions a salesperson would ask first: is a budget mentioned, is there a
timeline, is the writer the one who decides, does the need match what you sell.** Code then
compares any amounts and dates against your own criteria, and a person makes the call on who
gets a meeting. The model saves the reading, not the judgment.

The trap in lead scoring is asking the model for the score. A lead score is usually points
added up across several signals and compared with a cut-off. On the fraud-points task, where
a score is added up from six rules, jevos-v4 got 0.50 right against 0.69 for the hosted Jev.
Ask the model for each signal, and add the points in code.

This page is the questions, why "not stated" is the most common answer, where numbers go, how
code turns signals into a queue, why a person decides, and what local changes for sales data.

## The questions a first read answers

```json
{
  "model": "jev-latest",
  "state": {
    "source": "contact form",
    "company_size_field": "51-200",
    "message": "We're replacing our ticketing tool before our contract ends in March. I lead support ops and will make the recommendation to our CFO. We have roughly 40k budgeted. Need SSO and an EU data location."
  },
  "questions": {
    "budget_mentioned":   {"type": "noul", "instructions": "Does the writer mention a budget or an amount they expect to spend?"},
    "timeline_mentioned": {"type": "noul", "instructions": "Does the writer mention when they need to buy or start?"},
    "decides":            {"type": "noul", "instructions": "Does the writer say they make the buying decision themselves?"},
    "influences":         {"type": "noul", "instructions": "Does the writer say they recommend or evaluate, while someone else approves?"},
    "replacing":          {"type": "noul", "instructions": "Does the writer say they are replacing a tool they already use?"},
    "needs_sso":          {"type": "noul", "instructions": "Does the writer say they need single sign-on?"},
    "student_or_job":     {"type": "noul", "instructions": "Is the writer asking for a job, an internship or help with coursework?"}
  }
}
```

Every question asks what the writer says. "Is this a good lead?" is not in the list, and neither
is "is the budget big enough", because both are decisions that belong to your sales team.
Separating "decides" from "influences" is deliberate: the example writer recommends and a CFO
approves, which is useful to know and would be lost in one "is this a decision maker?"
question. Fit questions are one per requirement you can or cannot meet, so a lead that needs
something you do not offer is visible at once.

## Most of the time the answer is "not stated"

Real inbound messages are short. "Hi, can we get a demo?" states no budget, no timeline and no
role. A good qualification pass must say no to all of those, not guess. Questions of the form
"does the text say X at all" scored 0.847 on the first jevos's 999 new yes/no questions (per-kind
numbers for jevos-v4 are not published). The design of such gate questions is on
[ask whether the text says it at all](ask-whether-the-text-says-it.md).

"Not stated" is information, not a failure. It tells the salesperson which questions to ask on
the first call.

## Numbers go to code

"Roughly 40k budgeted" is a number. Whether 40k clears your minimum deal size, whether March is
within your sales cycle, and whether 51 to 200 employees is in your target segment are
comparisons. On the first jevos's test set, number-against-threshold questions scored 0.654 and
arithmetic 0.584, with a lean toward yes when the model cannot work it out (per-kind numbers for
jevos-v4 are not published); the measurement is on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

So the model answers "is a budget mentioned?" and your code extracts the amount with a pattern,
or the form asks for it in a field. The company size already arrives as a field; pass it to code
directly and only put it in `state` if the model needs it as context.

## From signals to a queue, in code

```python
POINTS = {"budget_mentioned": 2, "timeline_mentioned": 2, "decides": 3, "influences": 1,
          "replacing": 1}

def qualify(p, lead):
    if p["student_or_job"] > 0.8:
        return "not a sales lead", 0
    score = sum(w for k, w in POINTS.items() if p[k] > 0.6)
    if lead.get("budget") is not None and lead["budget"] < MIN_DEAL:
        score -= 3
    if lead["company_size_field"] in TARGET_SIZES:
        score += 2
    missing = [k for k in ("needs_sso",) if p[k] > 0.6 and not WE_OFFER[k]]
    if missing:
        return "review: needs something we lack", score
    return ("sales call" if score >= 6 else "nurture"), score
```

The points are illustrative. What matters is where each part lives: the model's probabilities
become yes or no per signal, the points and the comparison with `MIN_DEAL` are code, and a lead
that needs something you lack goes to a person rather than being silently dropped. When you want
to change the scoring, you change a dictionary, not a prompt, and you can re-run last quarter's
leads to see what the change would have done.

## A person decides

The output of this page is a sorted queue with reasons, not an accept or reject. Three reasons
to keep it that way:

- **The model reads; it does not know your market.** A lead with no budget stated can be the
  biggest deal of the year.
- **Errors lean toward yes.** On the first jevos's 999-question set, wrong yeses outnumbered
  wrong noes 152 to 91. A wrong "decides: yes" sends a salesperson after someone who cannot sign.
- **Decisions about people.** Filtering people out automatically may have legal rules attached
  where you operate. The design pattern of a human review step is discussed on
  [GDPR and automated decision-making with an LLM](gdpr-and-automated-decision-making.md);
  ask someone qualified what applies to you.

The middle of the queue ("nurture", "review") is the review band. It is where a salesperson's
five minutes are worth the most, and sizing it is covered on
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

## What local changes for sales data

Lead messages contain names, companies, budgets and plans that the writer shared with you, not
with a model provider. A local model reads them where they already are, costs nothing per lead,
and a message of this length is answered in a fraction of a second on our reference laptop
(28 ms for a short request, 130 ms for a long one). Seven questions share one reading of the
message.

What local does not fix: jevos reads English only, it has not been measured on sales leads, and
it will not know that "our CFO" means a longer cycle at that company. Those are for the person
reading the queue.

## Short answers to the questions that lead here

**Can AI qualify sales leads?** It can read inbound messages and answer qualification questions
(budget, timeline, role, fit). The scoring and the decision should stay with your code and your
team.

**Should the model give a lead score?** No. Ask for each signal and add the points in code;
summed scores were the model's weakest shape (0.50 vs 0.69 for the hosted Jev on fraud points).

**How does it handle leads that say almost nothing?** It should answer no to "is a budget
mentioned?" and similar questions. That tells the salesperson what to ask.

**Can it compare the budget with our minimum deal size?** Extract the amount and compare it in
code. Number comparisons are unreliable in a small model.

**See also:** [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md),
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md)
and [intent detection with a local LLM](intent-detection-with-a-local-llm.md).

## Sources

- The six-task comparison (fraud points 0.50 vs 0.69; five of the six sets helped choose the
  released checkpoint) and latency 28 and 130 ms (measured with jevos-v3, same size and speed as
  jevos-v4): the [jev README](https://github.com/feder-cr/jev).
- Not stated 0.847, number 0.654, arithmetic 0.584, error direction 152 vs 91: our 999-question
  test set, measured on the first jevos.
- Points and thresholds in the code are illustrative.

---

*From the notes of [jev](https://github.com/feder-cr/jev). The model's best answer on a lead
form is often "not stated", which is the salesperson's first question.*
