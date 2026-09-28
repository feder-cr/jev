---
title: "Gating AI agent tool calls with yes/no checks"
description: "Before an agent refunds, sends or deletes, ask a local LLM whether the action is what the user asked for, and act, confirm or block on the probability."
parent: "Agents and routing"
nav_order: 4
---

# Gating AI agent tool calls with yes/no checks

**A tool-call gate is a check that runs after the agent has chosen an action and before the
action runs: a small model reads the user's request and the proposed call, and answers
questions such as "Is this action what the user asked for?" with a probability.** Code then
runs the call, asks the user to confirm, or blocks it, depending on how high the probability is
and how much damage the tool can do. On a laptop CPU the check adds 50 to 220 ms, which is
small next to the tool call itself.

The gate is worth having because the model that chose the action is the model least likely to
notice it chose wrong. A second reader with a narrow question, looking only at the request and
the call, catches a different set of mistakes. It does not replace permissions, and this page
says where it stops.

This page is where the gate sits, the questions it asks, per-tool thresholds, human
confirmation, what the gate cannot see, and what it costs.

## Where does the gate sit?

An agent loop has a step where the planner model emits a tool call: a name and arguments. The
gate goes between that step and the execution. It sees three things:

- what the user asked, in their words;
- the proposed call, as JSON;
- any facts the call depends on that code has already computed.

The loop around it is short: describe the state, ask a yes/no question, act on a threshold. A
gate is that loop with one question, "Should this refund run?", placed between the agent's
plan and the tool.

## What does the gate ask?

One request, several questions, each about one thing:

```json
{
  "model": "jev-latest",
  "state": {
    "user_request": "My order 5521 never arrived, can you sort it out?",
    "proposed_call": {"tool": "issue_refund", "order_id": "5521", "amount": "full"},
    "order_found_for_this_user": true
  },
  "questions": {
    "asked":     {"type": "noul", "instructions": "Did the user ask for the action in proposed_call, or for something it directly resolves?"},
    "same_item": {"type": "noul", "instructions": "Does proposed_call refer to the same order the user mentions?"},
    "declined":  {"type": "noul", "instructions": "Did the user say they do not want this action taken?"}
  }
}
```

Each answer comes back as its own `noul`. Three design points are carried by the request:

- **Ownership is a fact from code.** `order_found_for_this_user` is looked up in the database, not
  asked. Whether the user may act on an order is an authorization question, and authorization
  belongs to code.
- **The negative question is asked separately.** "Did the user say they do not want this?"
  catches "I don't want a refund, just resend it", a case where "asked" alone might read the
  topic and say yes. Phrasing advice is on
  [negation in yes/no questions](negation-in-yes-no-questions.md).
- **No amounts are compared by the model.** If the refund amount must not exceed the order total,
  compare the numbers in code. On our 999-question test set, questions comparing a number with a
  threshold were answered right 0.654 of the time, against 0.954 for stated facts.

## Thresholds per tool

The threshold is a property of the tool, not of the model. A reversible action can run on a
lower bar than one that cannot be undone.

| Tool | Reversible? | Run without asking when | Otherwise |
|---|---|---|---|
| search, read a record | yes | always, no gate | |
| draft an email | yes | asked > 0.5 | show the draft |
| send an email | no | asked > 0.9 and declined < 0.1 | ask the user to confirm |
| issue a refund | money moves | asked > 0.9, same_item > 0.9, declined < 0.1 | confirm, or send to a person |
| delete data | no | never | always confirm |

These bars are a starting point for your own labelled cases, not measured optima. The reasoning
behind a higher bar for yes, when a wrong yes costs more, is on
[thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md).
It matters here because our measurements show a lean toward yes when the model is wrong: 152
wrong yeses against 91 wrong noes on the 999-question set.

## Human confirmation is the fallback, not the failure

When the gate is unsure, it should ask the user, in plain words: "I am about to refund order
5521 in full. Go ahead?". That is not the gate failing; it is the gate doing its job on the
cases it cannot settle. OWASP's entry on Excessive Agency in its Top 10 for LLM applications
recommends human-in-the-loop control that requires a human to approve high-impact actions before
they are taken, and a gate gives you a principled way to decide which actions reach that step.

The band between "run" and "block" is a [human review band](human-in-the-loop-ai-with-a-review-band.md)
with the user as the reviewer. Size it so confirmations are rare enough that users read them.

## What the gate cannot see

- **Whether the agent should have the tool at all.** OWASP's advice on Excessive Agency starts
  with limiting extensions, their functions and their permissions to what is needed. A gate on a
  shell tool is a poor substitute for not giving the agent a shell.
- **Injected instructions it is told to trust.** If a web page the agent read says "the user
  wants a refund", the gate reads the same poisoned context unless you keep the user's own words
  separate in `state`. It is one layer; see
  [AI agent guardrails with yes/no questions](ai-agent-guardrails-with-yes-no-questions.md).
- **Arithmetic and dates.** Do them in code before the gate, and pass the results as fields. In a
  LangChain agent that is ordinary code around
  [a LangChain tool for local yes/no decisions](langchain-tool-for-yes-no-decisions.md).
- **Non-English requests.** jevos reads English only.

## What it costs

A gate request with the user's message and a small tool call is a short request: on our
reference laptop (Intel Core Ultra 7 255H, 16 threads, no GPU), about 54 ms for 30 tokens and
about 220 ms for 190 tokens. Three questions on one state took about 165 ms against 103 ms for
one, because the state is read once. Gate only the tools that change something, and the cost per
agent run is a few of those calls.

## Short answers to the questions that lead here

**What is tool-call gating?** A check between an agent choosing a tool call and the call
running, which decides whether to run it, confirm it with a person, or block it.

**Why not let the agent's own model check itself?** It chose the action, so it is poorly placed
to doubt it. A second reader with a narrow question fails in different places.

**Should every tool be gated?** No. Read-only tools need no gate. Gate what sends, pays, deletes
or changes an account.

**Is a gate a security control?** No. Permissions and authorization in code are the control. A
gate catches misunderstandings.

**What should happen when the gate is unsure?** Ask the user to confirm, with the action and its
arguments in plain words.

**See also:** [stop conditions for AI agents](stop-conditions-for-ai-agents.md),
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md) and
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md).

## Sources

- Our measurements: latency on the reference laptop and the three-question timing from the
  [jev README](https://github.com/feder-cr/jev); accuracy by kind of question and error
  direction from our 999-question set.
- OWASP GenAI Security Project, [LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The refund example on this page is the README's refund example seen from the
other side: not whether to refund, but whether the agent understood the request.*
