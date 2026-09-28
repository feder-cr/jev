---
title: "An LLM router with yes/no questions"
description: "Route each request to a small or a large model by asking a local LLM yes/no questions about it, with thresholds, a safe default and fallbacks."
parent: "Agents and routing"
nav_order: 1
---

# An LLM router with yes/no questions

**An LLM router can be a handful of yes/no questions about the incoming request, answered by a
small local model, with the route chosen in code from the probabilities.** "Does the user ask
for code?", "Does the message ask for a calculation?", "Is it only a greeting?": each comes back
as its own P(yes), and a few lines of code turn them into "small model", "large model" or "a
person". The router adds 50 to 220 ms on a laptop CPU and sends nothing off the machine.

The non-obvious part is which questions to ask. "Does this request need a large model?" sounds
like the right question and is the weakest one, because it asks the small model to judge the
limits of models it has never seen. Questions about observable properties of the request are
reading questions, and reading is what a small model does well.

This page covers what a router decides, how to phrase routing questions, the code that picks
the route, what misrouting costs in each direction, the fallbacks, and when a different kind of
router is the better tool.

## What does a router actually decide?

A router takes a request and picks where it goes: a cheap model, an expensive model, a
specialised pipeline, a tool, or a human. The point is cost and latency. Most traffic in a
typical assistant is easy, and paying the large model's price for "thanks, that worked" is
waste.

Published routers are usually learned. RouteLLM, for example, trains routers on human
preference data to choose between a stronger and a weaker model, and its authors report cost
reductions of over 2 times in some cases without a loss in response quality. A learned router is
the right tool when you have that preference data. A yes/no router is what you can build on day
one without it: the routing logic is written as questions you can read, change and test.

## Which questions route well?

Route on properties you can point to in the text, then map properties to models in code.

| Instead of | Ask |
|---|---|
| Is this request hard? | Does the user ask for code to be written or fixed? |
| Does it need reasoning? | Does the message ask for a number to be calculated? |
| Is it simple? | Is the message only a greeting, a thanks or small talk? |
| Is it risky? | Does the message mention a payment, a refund or an account change? |

The left column asks for a judgement about models. The right column asks what the text says,
and each answer is a fact you can label by hand when you build a test set. That matters,
because on our set of 999 questions written after training, stated facts were answered right
0.954 of the time and questions that need arithmetic 0.584. A router built from reading
questions sits at the top of that range. The general advice is on
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## The router in code

All questions go in one request, so the message is read once and each extra question costs
less than the first.

```python
import requests

QUESTIONS = {
    "code": {"type": "noul", "instructions": "Does the user ask for code to be written or fixed?"},
    "calc": {"type": "noul", "instructions": "Does the user ask for a number to be calculated?"},
    "chat": {"type": "noul", "instructions": "Is the message only a greeting, a thanks or small talk?"},
}

def route(message):
    try:
        r = requests.post("http://127.0.0.1:8017/v1/systemone", timeout=2, json={
            "model": "jev-latest", "state": message, "questions": QUESTIONS})
        r.raise_for_status()
        p = {k: v["noul"] for k, v in r.json()["answers"].items()}
    except requests.RequestException:
        return "large"                      # router down: take the safe route
    if p["code"] > 0.5 or p["calc"] > 0.5:
        return "large"
    if p["chat"] > 0.8:
        return "small"
    return "large"                          # doubt goes to the capable model
```

Three choices are carried by that code. The precedence is explicit: a request that asks for code
goes to the large model even if it also says thanks. The bar for "small" is higher than 0.5,
because sending a hard request to the small model is the worse mistake. And every path that is
not clearly easy, including a router error, ends at the large model.

## What does misrouting cost?

The two mistakes are not equal, and the thresholds should say so.

- **Easy request sent to the large model.** You pay more and wait longer for an answer that is
  still correct. The user notices nothing.
- **Hard request sent to the small model.** The answer is worse, and the user notices. In an
  agent, a wrong answer early can send every later step the wrong way.

So a router should be tuned to be wrong in the cheap direction. Our measurements add a reason:
when a small model is wrong on yes/no questions, it is wrong toward yes more often (152 wrong
yeses against 91 wrong noes on the 999-question set). If "yes" means "easy, send it to the
small model", that lean pushes traffic in the expensive direction. Phrase the question so that
a wrong yes sends the request to the capable model, or raise the yes bar, as described on
[thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md).

## Fallbacks for when the router is wrong

A router that is right nine times in ten still misroutes a tenth of the traffic. Plan for it:

- **A default route.** When no rule fires, or the router times out, the request goes to the
  capable model. The code above does this.
- **Escalation after the fact.** If the small model's answer fails a check, retry on the large
  one. This turns a router into a cascade, covered on
  [a model cascade: small model first, large model on doubt](model-cascade-small-model-first.md).
- **A log of every routing decision.** Keep the message hash, the probabilities and the route,
  so you can find misroutes later and turn them into test cases.
- **A test set from your own traffic.** A hundred real requests, labelled by hand with the route
  they should have taken, tells you whether the thresholds are right. Re-run it when the
  traffic changes.

## When a yes/no router is the wrong tool

- **Many routes with many examples each.** Fifty intents, each with a list of typical phrasings,
  is the case embedding similarity is built for. The trade-off is on
  [semantic routing vs yes/no questions](semantic-routing-vs-yes-no-questions.md).
- **Preference data at scale.** If you have logs of which model's answer users preferred, a
  learned router can use them; questions written by hand cannot.
- **Other languages.** jevos reads English only. A router for multilingual traffic needs a
  multilingual model, or a translation step first.
- **Routing on numbers.** "Is the order over 500 euros?" is a comparison. Extract the number and
  compare in code.

## Short answers to the questions that lead here

**What is an LLM router?** A component that picks which model, tool or person handles each
request, usually to save cost and latency on easy requests.

**Can a small model decide whether a request needs a large model?** Not well if you ask it that
directly. Ask about observable properties of the request instead, and map those to models in
code.

**How fast is a yes/no router?** On a laptop CPU, 54 ms for a short request and 220 ms for a
long one, measured on an Intel Core Ultra 7 255H with 16 threads.

**What if the router is down?** Send the request to the capable model. A router should fail
toward the expensive, correct route.

**Can I add a route without retraining?** Yes. A new route is a new question and a line of code.

**See also:** [model cascade](model-cascade-small-model-first.md),
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md)
and [logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

## Sources

- Our measurements: latency on the reference laptop and accuracy by kind of question and error
  direction on the 999-question set, from the
  [jev README](https://github.com/feder-cr/jev) and our own test runs.
- RouteLLM: Ong et al., [RouteLLM: Learning to Route LLMs with Preference Data](https://arxiv.org/abs/2406.18665),
  arXiv 2406.18665, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The router in this page is three questions and a default; most of the work is
choosing the default.*
