---
title: "Review moderation with a local LLM"
description: "Screen product reviews with yes/no questions: off-topic, abusive, personal data, competitor mentions. Why fake reviews are hard to spot from text alone."
parent: "Use cases"
nav_order: 4
---

# Review moderation with a local LLM

**A local LLM can pre-screen product reviews by answering a few yes/no questions about each
one (is it about the product, is it abusive, does it contain someone's personal data, does it
name a competitor) and letting your code publish, hold or reject on the probabilities.** Those
are reading questions, the kind a small model answers well, and a review is short enough to
check in well under a quarter of a second on a laptop CPU. What the text cannot tell you
reliably is whether a review is fake: that needs purchase records and account behaviour, not a
language model.

There is also a line the questions must not cross. Moderating reviews is about whether a review
breaks your publishing rules, never about whether it is negative. If "is the reviewer unhappy?"
ever feeds the publish decision, you are filtering opinions, which misleads buyers and destroys
the reason anyone reads reviews.

This page is the questions, the decision table, the band for a human, fake-review signals and
why they are weak, and what running it locally buys.

## The questions, one per rule

```json
{
  "model": "jev-latest",
  "state": {
    "product": "trail running shoes, model TR-2",
    "rating": 2,
    "review": "Soles wore out in six weeks. The courier was rude too. Honestly RoadPro's are better, call me on 555 0134 and I'll tell you why."
  },
  "questions": {
    "about_product": {"type": "noul", "instructions": "Is the review mainly about the product itself?"},
    "abusive":       {"type": "noul", "instructions": "Does the review insult or threaten a person?"},
    "contact_info":  {"type": "noul", "instructions": "Does the review include a phone number, email address or home address?"},
    "competitor":    {"type": "noul", "instructions": "Does the review recommend a different brand or shop?"},
    "delivery_only": {"type": "noul", "instructions": "Is the review only about delivery and not about the product?"}
  }
}
```

A few choices in there matter:

- **"Mainly about the product"** rather than "about the product". Real reviews mention the
  courier and the packaging on the way. Asking what the review is mainly about lets a mixed
  review pass; the idea is covered on
  [mainly about: questions for messages with several topics](mainly-about-questions-for-mixed-messages.md).
- **The product name goes in `state`.** Without it, the model cannot tell whether "the TR-2" is
  the product or something else.
- **Contact details are a reading question plus a regex.** The model notices that a review
  contains a number someone could call; a pattern finds the exact digits to mask. The split
  between the two is on [checking text for personal data](pii-check-with-yes-no-questions.md).
- **Competitor mentions are a policy choice.** Many shops allow "I prefer brand X" and reject
  "buy from shop Y instead". Word the question to match your rule, not a general idea of
  competition.

## The decision table

Code turns the probabilities into one of three outcomes. The cut-offs are placeholders to be
set from your own labelled reviews.

| Condition | Outcome |
|---|---|
| `abusive` or `contact_info` above 0.8 | hold, mask or reject, tell the author why |
| `about_product` below 0.2, or `delivery_only` above 0.8 | publish under a delivery section, or reject by policy |
| `competitor` above 0.8 | follow your policy: allow, hold or edit |
| any rule between 0.4 and 0.8 | send to a person |
| otherwise | publish |

The rating is never an input to the table. A one-star review that breaks no rule is published.

## Who looks at the middle?

Reviews in the uncertain band go to a person with the review, the rule and the probability on
screen. Two things keep that queue useful. First, keep the band narrow at the start and widen it
only where the model disagrees with your reviewers often; the sizing method is on
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md). Second,
record every human decision against the question text, so that when you reword a question you
know which labels described the old wording.

## Can a model spot fake reviews?

Mostly not from the text, and it is worth being plain about it. A fake review written by a
careful person reads like a real one. The signals that do work are not linguistic: whether the
account bought the product, how many reviews it posted in a day, whether many reviews share an
IP range or arrive in a burst after a launch. Those live in your database, and a rule over them
is exact.

What a yes/no model can add are weak hints to rank a review for a closer look: "Does the review
describe the product only in general terms, with no detail of use?", "Does the review mention
receiving the product for free or in exchange for a review?". The second is a real reading
question and useful for disclosure rules. The first is a soft signal that many honest short
reviews also have. Treat such answers as one input to a score you combine in code, never as a
reason to reject on their own.

## The limits of the text screen

- **We have not measured jevos on reviews.** Our evidence is by kind of question: on 999 yes/no
  questions, facts stated in the text scored 0.954 and tone 0.938 on the first jevos (per-kind
  numbers for jevos-v4 are not published). The
  rules above are those shapes, which is encouraging and not a benchmark.
- **Not-stated cases.** A question such as "Does the reviewer say the product broke?" on a
  review that says nothing about durability should come back low. The first jevos's accuracy on "not
  stated" questions was 0.847; it is covered on
  [ask whether the text says it at all](ask-whether-the-text-says-it.md).
- **Sarcasm** ("great, it lasted a whole week") can read as praise. That matters for sentiment,
  less for the rule questions above.
- **English only.** Reviews in other languages need another model or translation.

## What local inference buys for reviews

Reviews are public once published, so privacy is less of a reason here than for email. The
reasons are cost and control. Screening every review costs nothing per token, a backlog can be
re-checked in a batch with `jev decide` whenever you change a rule, and the same questions run
the same way next month because the model is a file you pinned. Several rules on one review
share one reading of the text: on the README example, three questions take about 66 ms
together against 49 ms for one.

If your reviews are mostly in several languages, or you need standard safety categories, a
larger or dedicated model is the better tool.

## Short answers to the questions that lead here

**Can AI moderate product reviews?** It can check reviews against your publishing rules
(on topic, no abuse, no personal data) and send doubtful ones to a person.

**Can an LLM detect fake reviews?** Not reliably from the text. Purchase records and account
behaviour are the strong signals; text answers are weak hints at best.

**Should negative reviews be filtered?** No. Sentiment must not decide publication; only rule
breaches should.

**How do I handle personal data in reviews?** Ask the model whether the review contains contact
details, and use a pattern match to find and mask them exactly.

**See also:** [content moderation with a local LLM](content-moderation-with-a-local-llm.md),
[sentiment analysis with yes/no questions](sentiment-analysis-with-yes-no-questions.md) and
[batch decisions from files with jev decide](batch-decisions-with-jev-decide.md).

## Sources

- Accuracy by kind of question (fact 0.954, tone 0.938, not stated 0.847): our 999-question test
  set, first jevos.
- Three questions in about 66 ms against 49 ms for one, and `jev decide`: the
  [jev README](https://github.com/feder-cr/jev).
- The decision table thresholds are placeholders, not measured values.

---

*From the notes of [jev](https://github.com/feder-cr/jev). A one-star review that breaks no rule
is a review, and the model's job is to let it through.*
