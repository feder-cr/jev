---
title: "Semantic routing vs yes/no questions"
description: "Embedding-similarity routes match a message to example phrases; yes/no questions ask what it says. When each routes better, and how to combine them."
parent: "Agents and routing"
nav_order: 3
---

# Semantic routing vs yes/no questions

**Semantic routing picks a route by comparing the message's embedding with example phrases
written for each route; yes/no routing asks a model an explicit question per route and reads a
probability.** Similarity is the better tool when you have many routes, each with plenty of
typical phrasings, and want the lowest possible cost per message. Explicit questions are better
when a route depends on a condition, a negation or a rule that similar-sounding messages do not
share. The two combine well: similarity to shortlist, questions to confirm.

A conflict of interest first: we build jevos, which is the yes/no side of this page. The point of
the comparison is not that one wins. It is that they fail in different places, and knowing
where tells you which to put first.

This page is how each approach decides, what you author for each, where each one breaks, how
to combine them, and how to test the choice on your own traffic.

## How does each approach decide?

In a semantic router, such as the open-source Semantic Router library, you define `Route`
objects, each with a name and a list of utterances typical of that route. The message and the
utterances are turned into vectors by an encoder, and the router returns the route whose
utterances are closest in meaning, or `None` if nothing is close enough. Its README positions it
as a decision layer that avoids asking an LLM to choose the route.

In a yes/no router, each route is a question: "Does the customer ask to cancel their
subscription?". The model reads the message with the question and returns P(yes), and code picks
the route from the probabilities.

| | Semantic routing | Yes/no questions |
|---|---|---|
| You write | example utterances per route | one question per route |
| The model computes | a vector per message | a probability per question |
| Decision | nearest route above a similarity cut-off | thresholds and precedence in code |
| Adding a route | write a list of examples | write a question |
| Output | a route name, or none | one probability per route |

## Where similarity routes better

- **Many routes.** Comparing one vector against hundreds of stored ones is cheap and does not
  grow much with the number of routes. A yes/no request grows with every question you add, even
  though extra questions on the same text cost less than the first (on our reference laptop, three
  questions took about 165 ms against 103 ms for one).
- **Routes defined by examples, not by rules.** If you have real messages for each intent and no
  clean way to describe the intent in a sentence, examples are the natural thing to write.
- **Languages.** An embedding router is as multilingual as its encoder. jevos reads English only;
  see [using an English-only LLM with other languages](using-an-english-only-model-with-other-languages.md).
- **Lowest cost per message.** Where every millisecond counts across millions of messages, a
  vector lookup is hard to beat.

## Where explicit questions route better

- **Negation and near-misses.** "I want to cancel" and "I do not want to cancel, I just want to
  pause" share most of their words and topic. Similarity measures closeness of meaning overall;
  a question asks about one condition. Test these pairs on your own router before trusting
  either approach. The question-side advice is on
  [negation in yes/no questions](negation-in-yes-no-questions.md), where jevos scored 0.858 on
  negation questions in our 999-question test.
- **Routes that depend on a rule.** "Is this a refund request for an item delivered within 30
  days?" is not a topic, and no set of example utterances captures it. Put the rule in the
  question, and the computation of the 30 days in code.
- **Several routes at once.** A message can be both a billing problem and a complaint. Each
  question is answered independently, so both can be yes.
- **No examples yet.** A new route on day one is a sentence. There is nothing to collect first.
- **A readable decision.** A log that says "cancel: 0.91, pause: 0.12" explains itself to a
  reviewer in a way that a similarity score against a list of phrases does not.

## Combining them

The usual combination puts the cheap step first and the precise step second:

1. **Shortlist by similarity.** The embedding router proposes the two or three closest routes, or
   none.
2. **Confirm with questions.** Ask one yes/no question per shortlisted route, with the route's
   condition written into it.
3. **Decide in code.** Take the route whose question clears its threshold; if none does, send the
   message to a default queue or a person.

A second pattern keeps the similarity router in charge and adds a single yes/no gate for the
routes where a wrong match is expensive: before a message is routed to "cancel subscription",
ask whether the customer actually asks to cancel. The gate runs only on that fraction of
traffic, so its cost is small.

Both patterns keep the question count low, which is where yes/no routing gets expensive, and use
questions where similarity is weakest. The general router design, with fallbacks and defaults,
is on [an LLM router with yes/no questions](llm-router-with-yes-no-questions.md).

## Where both approaches run out

- **We did not benchmark the two on the same set.** Nothing on this page is a measured
  comparison of routing accuracy. The only jevos numbers here are latency on our reference laptop
  and accuracy by kind of question on our own test set.
- **A yes/no router is not free at scale.** At 54 ms for a short request on a laptop CPU, a single
  server answers a limited number of messages per second. For very high volume, similarity first
  is the cheaper design.
- **Similarity cut-offs and probability thresholds both need tuning.** Neither is right out of
  the box. Both are set by looking at labelled cases.

## How to choose for your own traffic

Take a few hundred real messages from your history and label the route each one should have
taken. Include the hard pairs on purpose: negations, messages that mention a route's topic
without asking for it, messages that belong to two routes. Then run both routers and compare
per route, not only overall. A router that is right on average and wrong on "cancel" is wrong
where it matters. The method is on [building a yes/no test set](building-a-yes-no-test-set.md).

## Short answers to the questions that lead here

**What is semantic routing?** Routing a message by the similarity of its embedding to example
phrases stored for each route.

**Is semantic routing faster than asking an LLM?** A vector comparison is usually cheaper than a
model reading the message with a question. How much cheaper depends on your encoder and
hardware; we have not measured it.

**Does semantic routing handle negation?** Messages with opposite meanings can have similar
wording. Test negated pairs on your own data before relying on it.

**Can I use both?** Yes. Shortlist by similarity, confirm with one question per candidate route.

**Which is easier to maintain?** Questions are shorter to write; example lists capture phrasing
you could not describe. Past a few dozen routes, the combination is often the practical answer.

**See also:** [intent detection with a local LLM](intent-detection-with-a-local-llm.md),
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md)
and [LLM decisions vs keyword rules and regex](llm-decisions-vs-keyword-rules.md).

## Sources

- Semantic Router: the [aurelio-labs/semantic-router README](https://github.com/aurelio-labs/semantic-router)
  on GitHub, for `Route` objects, utterances, encoders and the `None` result, fetched 2026-09-29.
- Our measurements: the three-question timing and the 54 ms short-request latency from the
  [jev README](https://github.com/feder-cr/jev); the 0.858 on negation from our 999-question set.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. It is the question side of this page; nothing here measured the other side.*
