---
title: "Stop conditions for AI agents"
description: "When should an agent stop? Hard limits in code, plus yes/no checks in the loop: is the task complete, is the agent looping, does it need the user."
parent: "Agents and routing"
nav_order: 6
---

# Stop conditions for AI agents

**An agent should stop when a hard limit is hit, when the task is complete, when it is making
no progress, or when it needs something only the user can give; the first is code, and the
other three can be yes/no questions a small model answers after each step.** "Is the task in
the goal complete, based on the last result?", "Did the last three steps make no progress?",
"Does the agent need information only the user has?": each returns a probability, and the loop
stops, continues or hands over depending on the answers.

The reason to ask these as separate questions, instead of letting the agent's own model decide
when it is done, is that the working model has every incentive to keep going. It sees one more
thing to try. A separate reader with a narrow question, run on every step, is a cheap second
opinion on whether the loop should continue.

This page is the hard limits that come first, the three questions one by one, the loop that
ties them together, and where a small model should not be the judge.

## Hard limits come first

Before any model check, the loop needs limits that do not depend on a model at all:

- **A maximum number of steps.** Anthropic's guide to building effective agents notes that it is
  common to include stopping conditions such as a maximum number of iterations to maintain
  control.
- **A budget.** Tokens spent, money spent, or wall-clock time.
- **Repeated identical actions.** If the agent issues the same tool call with the same arguments
  twice in a row, code can see that without a model: hash the call and compare.

These are exact, cheap and not open to argument. The model checks below handle what code cannot
see: whether the goal is met, and whether different-looking steps are going nowhere.

## Is the task complete?

This is the question agents get wrong in both directions: they stop with half the work done, or
keep polishing a finished result. Asking it well means giving the checker the goal and the
evidence, not the agent's own claim.

```json
{
  "model": "jev-latest",
  "state": {
    "goal": "Find the customer's last invoice and email them a copy.",
    "steps_done": ["looked up customer 881", "found invoice INV-2291", "drafted email with INV-2291 attached"],
    "last_result": "Draft saved. Not sent."
  },
  "questions": {
    "found":    {"type": "noul", "instructions": "Do the steps show that the customer's last invoice was found?"},
    "sent":     {"type": "noul", "instructions": "Does last_result say the email was sent?"},
    "claims_done": {"type": "noul", "instructions": "Does last_result claim the whole goal is finished?"}
  }
}
```

Two habits carry the design. **Split the goal into its parts**, one question each, and stop only
when every part is a clear yes; "Is the task complete?" as one question hides which part is
missing, the problem described on [one condition per question](one-condition-per-question.md).
**Ask what the evidence says, not whether the goal is met in general**: "Does last_result say the
email was sent?" is a reading question. On our 999-question test set, the first jevos answered stated facts
right 0.954 of the time (per-kind numbers for jevos-v4 are not published).

## Is the agent looping?

Exact repetition is code. The harder case is the agent that rephrases the same search five
times, or alternates between two tools. For that, give the checker the last few steps and ask:

- "Do the last three steps try the same thing in different words?"
- "Did the last three results add any information not in earlier results?"

Stop, or change strategy, when the first is high or the second is low. Keep the window short:
latency grows with the text (on our reference laptop, 28 ms for a 30-token request and 130 ms
for a 191-token one read from scratch), so three steps summarised in a line each cost far less
than the full transcript.

## Does it need the user?

An agent that guesses a missing fact instead of asking produces confident wrong work. After each
step, ask:

- "Does the goal depend on information that is not in the steps or results so far?"
- "Is the agent about to choose between options the user did not specify?"

A high answer pauses the loop with a question to the user. The same guide from Anthropic
describes agents pausing for human feedback at checkpoints or when they meet blockers; the
yes/no check is one way to decide when that moment has come. Missing information has its own
question shape, covered on [ask whether the text says it at all](ask-whether-the-text-says-it.md),
where the first jevos scored 0.847 on "not stated" questions in our test.

## The loop

```python
def run(goal, max_steps=20):
    steps = []
    for n in range(max_steps):                     # hard limit: code
        action = planner(goal, steps)
        if steps and action == steps[-1]["action"]:
            return "stopped: repeated action"      # exact repeat: code
        result = execute(action)
        steps.append({"action": action, "result": result})
        p = ask_checks(goal, steps[-3:])           # one POST, several questions
        if p["needs_user"] > 0.7:
            return "paused: ask the user"
        if all(p[k] > 0.8 for k in GOAL_PARTS):
            return "done"
        if p["same_thing"] > 0.8:
            return "stopped: no progress"
    return "stopped: step limit"
```

`planner`, `execute` and `ask_checks` stand for your own code; `ask_checks` sends one request to
`/v1/systemone` with the questions above (one per goal part, plus `same_thing` for looping and
`needs_user` for missing information) and returns the probabilities by name. It is a sketch,
not tested code. The order is a
choice: asking the user comes before declaring success, so an agent that "finished" on a guess
is caught.

A check on every step costs 28 to 130 ms on our reference laptop, usually a small fraction of
the step it follows.

## Where a small model should not be the judge

- **"Is the answer correct?"** when correctness needs reasoning or knowledge outside the text,
  such as whether code works. Run the tests instead; a test result is a fact the checker can
  read.
- **Numeric goals.** "Are there at least 50 results?" is a count. Count in code.
- **Goals in other languages.** jevos reads English only.
- **The final say on irreversible work.** A stop check can end a loop; it should not be the only
  thing between the agent and a send or a delete. That is the job of
  [a tool-call gate](gating-ai-agent-tool-calls.md) and, for high-impact actions, a person.

## Short answers to the questions that lead here

**How do I stop an AI agent from looping forever?** A step limit and a budget in code, a hash
check for repeated actions, and a model check for steps that repeat in different words.

**Can the agent decide itself when it is done?** It can, and it is biased toward continuing or
toward claiming success. A separate check on the evidence is more reliable.

**What should "done" mean?** Every part of the goal confirmed by a result, each part asked as its
own question.

**When should the agent ask the user?** When the goal depends on information that is not in
anything the agent has seen, or on a choice the user did not make.

**Is a model check on every step too slow?** On a laptop CPU it adds 28 to 130 ms per step,
which is usually small next to the step itself.

**See also:** [AI agent guardrails with yes/no questions](ai-agent-guardrails-with-yes-no-questions.md),
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md) and
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## Sources

- Anthropic, [Building effective agents](https://www.anthropic.com/research/building-effective-agents),
  on stopping conditions and pausing for human feedback, fetched 2026-09-29.
- Our measurements: latency on the reference laptop from the
  [jev README](https://github.com/feder-cr/jev); accuracy on fact and "not stated" questions from
  our 999-question set (first jevos).

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. A stop check is one more yes/no question in the loop, asked about the agent
instead of the user's text.*
