---
title: "jevos vs Llama Guard for content safety checks"
description: "Llama Guard classifies prompts and responses against a fixed hazard taxonomy; jevos answers your own yes/no policy questions. Which to use, and when both."
parent: "Comparisons"
nav_order: 8
---

# jevos vs Llama Guard for content safety checks

**For the standard safety categories, violent crime, self-harm, child exploitation, hate and the
rest of a published hazard list, a dedicated safety model such as Meta's Llama Guard is the
specialist, and it is the tool to use.** jevos does something different: it answers yes/no
questions you write, so it fits the rules that are yours, such as "is this post off-topic for a
cooking forum?", "does this reply promise a refund?" or "does the message mention a competitor?".
Llama Guard 3 covers eight languages; jevos reads English only. Many systems need both: a safety
classifier for the hazards everyone shares, and questions for the policies only you have.

Conflict of interest, in one line: we build jevos; the Llama Guard facts come from Meta's model
card on Hugging Face, fetched 2026-09-29.

The confusion comes from both being "a model that says whether content is acceptable". The
question that separates them is who wrote the definition of acceptable: a published taxonomy, or
you.

This page is what Llama Guard is built for, what jevos does instead, where the specialist wins,
where your own questions fit, how to use both, and the limits they share.

## What Llama Guard is built for

Meta's card describes Llama Guard 3 as "a Llama-3.1-8B pretrained model, fine-tuned for content
safety classification." It can classify both sides of a conversation: "LLM inputs (prompt
classification)" and "LLM responses (response classification)." Its output is generated text,
saying whether the content is safe or unsafe and, when unsafe, listing the violated categories.

The categories are fixed. The card lists 14, based on the MLCommons taxonomy of 13 hazards plus
one for code interpreter abuse:

S1 violent crimes, S2 non-violent crimes, S3 sex-related crimes, S4 child sexual exploitation,
S5 defamation, S6 specialized advice, S7 privacy, S8 intellectual property, S9 indiscriminate
weapons, S10 hate, S11 suicide and self-harm, S12 sexual content, S13 elections, S14 code
interpreter abuse.

For a score instead of a label, the card says: "We look at the probability for the first token,
and use that as the 'unsafe' class probability. We can then apply score thresholding to make
binary decisions." It is 8B parameters in bfloat16, with an INT8 version listed, under the Llama
3.1 Community License.

## What jevos does instead

jevos has no taxonomy. You send a text as `state` and any number of named yes/no questions, and
each comes back as its own `noul`, P(yes):

```json
{
  "model": "jev-latest",
  "state": "Check out my channel for better recipes than this one, link in bio",
  "questions": {
    "off_topic":   {"type": "noul", "instructions": "Is this comment unrelated to the recipe it was posted under?"},
    "self_promo":  {"type": "noul", "instructions": "Does the comment promote the writer's own channel or product?"},
    "insulting":   {"type": "noul", "instructions": "Does the comment insult another person?"}
  }
}
```

None of those three is a safety hazard in a published taxonomy, and all three are the kind of
rule a community actually enforces. That is the space jevos is for. It is a 1B-class model on a
CPU: 54 to 220 ms per request on our reference laptop, with the text read once for every
question in the request.

## Where the specialist wins

Say it plainly: for the categories in its taxonomy, use a safety model trained for them.

- **Coverage of hard categories.** Child exploitation, weapons, self-harm: these need a model
  built and evaluated for them, not a general yes/no reader asked a question on the fly.
- **Languages.** The card lists English, French, German, Hindi, Italian, Portuguese, Spanish and
  Thai. jevos is English only.
- **Conversation roles.** Llama Guard is built to classify prompts and responses in a chat.
- **A shared vocabulary.** Categories with codes make reporting and audits comparable across
  systems.

Asking jevos "is this content sexual exploitation of a minor?" is the wrong design. The right one
is a specialist model plus the legal and reporting process that category requires.

## Where your own questions fit

Most moderation work is not in the hazard list. It is forum rules, brand rules, product rules:
off-topic posts, self-promotion, personal data in public reviews, a reply that promises what
support cannot give, a message asking to cancel. These change often, differ per community, and
are easy to state as a question. jevos' measured strengths match them: 0.938 on tone, 0.859 on
intent and 0.954 on facts stated in the text, in our 999-question test.

The operating pattern is on [content moderation with a local LLM](content-moderation-with-a-local-llm.md):
act on the confident ends, and send the middle band to a moderator.

## Using both

A layered setup is straightforward:

1. Run the safety classifier on every item. Anything it flags follows your safety process.
2. Ask your own yes/no questions on the rest: the community and product rules.
3. Route uncertain answers from either to a person, and log both the scores and the decision.

Keep the two apart in logs and in code. A "safe" verdict from a safety model does not mean the
post follows your rules, and a low P(yes) on your questions does not mean the post is safe.

## Limits both share

Meta's card is candid about Llama Guard's limits: some categories "may require factual, up-to-date
knowledge to be evaluated", naming defamation, intellectual property and elections, and the model
is susceptible to adversarial and prompt injection attacks. jevos has the same exposure to
adversarial text, and a smaller model has less knowledge to draw on. Neither is a security
boundary on its own; see [prompt injection screening with a small model](prompt-injection-screening-with-a-small-model.md)
for how far a screen goes.

## Short answers to the questions that lead here

**What is Llama Guard?** Meta's content safety classifier: Llama Guard 3 is an 8B model that
labels prompts and responses safe or unsafe against 14 hazard categories.

**Can jevos replace Llama Guard?** No, not for the hazards in its taxonomy. Use a safety model
there, and jevos for your own policy questions.

**Can Llama Guard give a probability?** The card describes using the first token's probability as
the unsafe score and thresholding it.

**Which languages?** Llama Guard 3 lists eight; jevos reads English only.

**Is either a security control?** No. Both can be fooled by adversarial input and belong in a
layered design.

**See also:** [AI agent guardrails with yes/no questions](ai-agent-guardrails-with-yes-no-questions.md),
[review moderation with a local LLM](review-moderation-with-a-local-llm.md) and
[jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).

## Sources

- Everything about Llama Guard 3 (base model, size, categories, languages, first-token
  probability, limits, licence, INT8 version): Meta's
  [model card on Hugging Face](https://huggingface.co/meta-llama/Llama-Guard-3-8B), fetched
  2026-09-29.
- jevos latency and accuracy by kind: our own measurements, see the
  [jev README](https://github.com/feder-cr/jev) and our 999-question test set on `jevos-q4_k_m`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which leaves the hazard list to the
models built for it.*
