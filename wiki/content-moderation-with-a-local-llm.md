---
title: "Content moderation with a local LLM"
description: "Write your community rules as yes/no questions, act on P(yes) with a review band, log every decision, and keep user posts on your own server."
parent: "Use cases"
nav_order: 1
---

# Content moderation with a local LLM

**A local LLM can moderate content by answering one yes/no question per community rule about
each post, while your code acts on the probabilities: remove the clear cases, queue the
uncertain ones for a moderator, publish the rest.** With jevos every rule is a question in the
same request, the post is read once, and each rule comes back as its own P(yes). Posts never
leave your server. What the model does not do is decide what your rules are, or take over the
legal duties a platform may have: it is a first reader that sorts the queue.

The non-obvious point is that the unit of moderation is the rule, not the post. A single "is
this post acceptable?" score tells a moderator nothing and cannot be tuned. One probability per
rule tells you which rule a post broke, lets you set a stricter bar where a wrong removal hurts,
and gives the user something specific to appeal.

This page is how to write rules as questions, what the code does with each probability, the
review band and appeals, what to log, where the model is the wrong tool, and what running it
locally changes.

## How do community rules become questions?

Rewrite each rule as a question about the post that a careful reader could answer from the text
alone. One condition per question, with the definition inside the question, because the model
reads only what you send.

```json
{
  "model": "jev-latest",
  "state": {
    "channel": "product help",
    "post": "Anyone else getting the sync error since the update? Also DM me if you want cheap accounts, best prices."
  },
  "questions": {
    "insult":        {"type": "noul", "instructions": "Does the post insult or demean another person?"},
    "selling":       {"type": "noul", "instructions": "Does the post offer to sell something or ask people to buy something?"},
    "off_topic":     {"type": "noul", "instructions": "Is the post mainly about something other than using the product?"},
    "personal_data": {"type": "noul", "instructions": "Does the post share someone's phone number, home address or email address?"}
  }
}
```

The example is mostly a real help question with a sales pitch attached, which is why "mainly"
sits in the off-topic question and why selling is its own rule. Splitting compound rules is
covered on [one condition per question](one-condition-per-question.md): "no harassment or spam"
is two questions, not one.

Rules that depend on who wrote the post (a new account, a repeat offender) or on how often
(five posts in a minute) are not questions for the model. Those facts are in your database;
check them in code and combine the results there.

## What does the code do with each probability?

Each rule gets two cut-offs, and the post gets the most severe outcome across its rules.

```python
ACT = {"insult": 0.85, "selling": 0.8, "off_topic": 0.95, "personal_data": 0.7}
REVIEW = 0.5

def moderate(answers):
    outcome = ("publish", None)
    for rule, a in answers.items():
        p = a["noul"]
        if p >= ACT[rule]:
            return ("remove", rule)
        if p >= REVIEW:
            outcome = ("review", rule)
    return outcome
```

The thresholds are placeholders, not recommendations. Two things shape the real ones. First,
what a wrong yes costs on that rule: removing an innocent post as off-topic annoys a user,
missing a leaked phone number harms someone, so personal data gets the lower bar. Second, the
model's own lean. When it is wrong, it is more often wrong toward yes: 152 wrong yeses against
91 wrong noes on our 999-question test set. That is a reason to ask for clearly more than 0.5
before an automatic removal, and the reasoning is worked through on
[thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).

## The review band, and appeals

Everything between the review line and the act line goes to a person. The band is the design,
not a leftover: the model handles the posts where it is confident, and moderators spend their
time on the ones that need judgment. Its width decides how much work lands on them. To size it,
replay a few hundred past posts with known outcomes and count how many fall inside;
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md) covers
the sizing in detail.

Appeals come almost for free once you keep the per-rule answer. A user whose post was removed
under "selling" can be told which rule, and the moderator handling the appeal sees the
probability that triggered it. Appeals that overturn a removal are also your best labelled
data: each one is a case where the threshold for that rule was too low or its question was
worded badly.

## What should a moderation log keep?

For every post: a hash of the text, the questions as sent, each probability, the thresholds in
force, the outcome, and the model file's hash reported by `/health`. When a moderator asks why a
post was removed last Tuesday, that record answers it, and when you change a question or a
threshold you can tell which decisions were made under which version. The full list is on
[logging LLM decisions for audit](logging-llm-decisions-for-audit.md).

Product reviews have rules of their own (off topic, abusive, personal data, about the product at
all), covered on [review moderation with a local LLM](review-moderation-with-a-local-llm.md).

## Where a small yes/no model is the wrong tool

- **Standard safety categories.** For well-known hazard classes, a model built for content
  safety with a fixed taxonomy is the specialist; the comparison is on
  [jevos vs Llama Guard](jevos-vs-llama-guard.md). jevos fits the rules that are yours: "no
  selling", "stay on topic", "no spoilers in this channel".
- **Known illegal material.** Matching against lists of known images or links is a job for
  dedicated matching tools and for the reporting processes that apply to you. A text model
  reading a caption is not that.
- **Legal obligations.** Laws in many places put duties on platforms about notices, response
  times and transparency. A classifier does not meet them for you; ask someone qualified what
  applies to your service.
- **Other languages.** jevos reads English only. A community that posts in several languages
  needs a multilingual model, or translation first.
- **Context outside the post.** A quote of someone else's insult, a joke between friends, a
  reply whose meaning depends on the previous message. Send the parent message in `state` when
  it matters; the model cannot see what you do not send.

Being straight about the limit: we have not measured jevos on a moderation dataset. Our accuracy
by kind of question (tone 0.938 on 32 questions, intent 0.859 on 71) tells you which rule
shapes are likely to work, not how well your rules will. Measure on your own posts.

## What running it locally changes

User posts, including the ones you remove, stay on your machine. There is no extra processor
for this step and no per-token bill that grows with your community. A short post costs about
54 ms on our reference laptop (Intel Core Ultra 7 255H, 16 threads), and several rules on one
post cost much less than several calls, because the post is read once. For a small community,
moderation can run on the same box as the forum.

What it does not change: access control on the logs, how long you keep removed content, and who
may read the review queue. Those are yours either way, and
[a private LLM for text classification](private-llm-for-text-classification.md) goes through
what "local" does and does not solve.

## Short answers to the questions that lead here

**Can a local LLM moderate content?** It can sort posts against your own rules, one yes/no
question per rule, and send the uncertain ones to a moderator. It should not be the only
decision-maker for removals.

**How do I choose thresholds for automatic removal?** Replay past posts with known outcomes,
pick a threshold per rule from them, and set the bar higher where a wrong removal is costly.

**Does it work for hate speech and other standard categories?** A dedicated safety model is the
better choice for standard hazard categories. Use yes/no questions for your community's own
rules.

**Does it need a GPU?** No. jevos runs on the CPU and adds about 1.2 GB of memory.

**What about posts in other languages?** jevos reads English only; translate first or use a
multilingual model.

**See also:** [a Discord moderation bot with a local LLM](discord-moderation-bot-with-a-local-llm.md),
[review moderation with a local LLM](review-moderation-with-a-local-llm.md) and
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## Sources

- Short-request latency, memory, English only, `/health` fields: the
  [jev README](https://github.com/feder-cr/jev) and our measurements on the reference laptop.
- Error direction (152 vs 91) and accuracy by kind of question: our 999-question test set,
  written after training, run on `jevos-q4_k_m`.
- The per-rule thresholds, review band and appeal loop are a design pattern described here, not
  a measured result.

---

*From the notes of [jev](https://github.com/feder-cr/jev), where the moderation example is a
sketch of a design: we have not run jevos on a moderation benchmark.*
