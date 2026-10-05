---
title: "Sentiment analysis with yes/no questions"
description: "Sentiment analysis with a local LLM: ask positive, negative and mixed as separate yes/no questions, and ask per aspect (delivery, price, quality)."
parent: "Use cases"
nav_order: 8
---

# Sentiment analysis with yes/no questions

**With a yes/no model, sentiment is not one score but a few questions: is the writer pleased,
is the writer unhappy, and, when you care about the why, is the writer unhappy with a specific
aspect such as delivery or price.** Positive and negative are asked separately, so a review
that praises the product and hates the courier can say yes to both, which is the honest answer
and the one a single polarity score hides. Tone was one of the strongest kinds of question on
our test set for the first jevos, 0.938, on a small sample.

Aspect questions are where this approach earns its keep. "Overall negative" tells a product
team that something is wrong. "Unhappy with delivery: 0.8, unhappy with quality: 0.1" tells them
which team to call, and no labelled data is needed to add a new aspect.

This page is the overall questions, aspect questions, how code turns them into labels and
numbers, what to do with uncertain answers, how far to trust the measured tone accuracy, and
when a trained sentiment model is the better tool.

## Why ask positive and negative separately?

A single "is this positive?" forces mixed texts to the middle, where they look like uncertain
neutral ones. Two questions separate the cases:

| pleased | unhappy | reading |
|---|---|---|
| high | low | positive |
| low | high | negative |
| high | high | mixed |
| low | low | neutral or factual |

The fourth row matters as much as the first three. "Order 4411 arrived Tuesday" is neither, and
a model asked only for positivity would give it some middling number that looks like mild
dislike. Asking both is what the independence of yes/no answers is good for.

## Aspect sentiment: one question per aspect

```json
{
  "model": "jev-latest",
  "state": {
    "product": "espresso machine",
    "review": "Coffee is excellent and it heats up fast. Took three weeks to arrive though, and the box was crushed. Pricey for what it is."
  },
  "questions": {
    "pleased":        {"type": "noul", "instructions": "Does the reviewer express satisfaction with anything?"},
    "unhappy":        {"type": "noul", "instructions": "Does the reviewer express dissatisfaction with anything?"},
    "unhappy_quality":  {"type": "noul", "instructions": "Is the reviewer unhappy with how the product works or the results it gives?"},
    "unhappy_delivery": {"type": "noul", "instructions": "Is the reviewer unhappy with the delivery or the packaging?"},
    "unhappy_price":    {"type": "noul", "instructions": "Is the reviewer unhappy with the price or value for money?"}
  }
}
```

Each aspect question names what the aspect covers ("the delivery or the packaging") so the
model has something concrete to check. All five questions share one reading of the review; on
the README's example, three questions on one text took about 66 ms against 49 ms for one
alone on our reference laptop, so aspects are cheap to add.

Phrase aspect questions positively and flip in code if you need the other direction. Negated
wording ("Is the reviewer not unhappy with...") adds a step the model can get wrong; negation
questions scored 0.858 on the same test set (first jevos), and the advice is on
[negation in yes/no questions](negation-in-yes-no-questions.md).

## From probabilities to labels and to a dashboard

```python
def overall(p, hi=0.6, lo=0.4):
    pos, neg = p["pleased"] >= hi, p["unhappy"] >= hi
    if pos and neg:
        return "mixed"
    if pos:
        return "positive"
    if neg:
        return "negative"
    if p["pleased"] < lo and p["unhappy"] < lo:
        return "neutral"
    return "unclear"

def aspect_rates(all_answers, aspects=("quality", "delivery", "price")):
    n = len(all_answers)
    return {a: sum(x["unhappy_" + a] for x in all_answers) / n for a in aspects}
```

For a dashboard, average the probabilities rather than counting thresholded labels. On natural yes/no questions
in a held-out split the first jevos's calibration error was 0.009, so a mean P(unhappy with delivery)
of 0.2 over a month's reviews is a reasonable estimate of the share of unhappy-with-delivery
reviews. On new kinds of text calibration may carry over less well (not measured on jevos-v4), which is why a quarterly
check against a hand-labelled sample is worth the hour; the idea is on
[LLM calibration explained](llm-calibration-explained.md).

## What to do with "unclear"

In sentiment the stakes of a single wrong answer are low, so the review band is not a queue for
every item. Use it two ways instead: exclude "unclear" from the headline numbers and report how
many there were, and read a random sample of them every week. If "unclear" is growing, a new
kind of text is arriving (a new product, a new channel) and your questions may need rewording.
Where a sentiment answer drives an action, such as contacting an unhappy customer, the band is a
real queue; that case is closer to
[detecting cancellation intent in customer messages](cancellation-intent-detection.md).

## How far to trust the 0.938

Being straight about the number: the first jevos scored 0.938 on tone, on 32 questions in a set of 999 we wrote
after it was finished (per-kind numbers for jevos-v4 are not published). Thirty-two is a small sample; the true rate on your data could be noticeably
lower. And the known hard cases are still hard:

- **Sarcasm.** "Great, another week without hot water" reads as pleased to a literal reader.
- **Politeness hiding complaint.** "It's fine, I suppose, for the price" is unhappy in a way
  that depends on culture and context.
- **Complaints about someone else.** "My neighbour's one broke, mine is fine" is positive about
  this product.
- **English only.** Reviews in other languages need translation first or a multilingual model.

## When a trained sentiment classifier is the better tool

If your labels are fixed (positive, negative, neutral) and you have thousands of labelled
examples, a small classifier trained on them will usually be faster per text and more accurate
on that exact task; the comparison is on
[a yes/no LLM vs a fine-tuned BERT classifier](yes-no-llm-vs-fine-tuned-bert.md). The yes/no
approach wins when aspects change every quarter, when you have no labels yet, or when the same
request also asks non-sentiment questions about the text.

Running it locally matters for the backlog: re-scoring two years of reviews with a new aspect
question costs CPU time, not a per-token bill, and customer text stays on your machine.

## Short answers to the questions that lead here

**Can an LLM do sentiment analysis without training data?** Yes: ask yes/no questions such as
"Is the reviewer unhappy with the delivery?" and read the probabilities.

**How do I detect mixed sentiment?** Ask about satisfaction and dissatisfaction separately. High
on both is mixed.

**What is aspect-based sentiment analysis?** Sentiment toward specific parts of an experience,
such as price or delivery. With yes/no questions, each aspect is one question.

**Is it accurate?** On our own test set, the first jevos scored 0.938 on tone questions, on a small sample of 32. Check
on your own labelled texts before relying on it.

**See also:** [review moderation with a local LLM](review-moderation-with-a-local-llm.md),
[yes/no questions about tone and emotion](yes-no-questions-about-tone.md) and
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).

## Sources

- Tone 0.938 (32 questions) and negation 0.858: our 999-question test set, first jevos.
- Calibration error 0.009: our held-out split, 6,397 natural yes/no questions, first jevos.
- Three questions in about 66 ms against 49 ms: the [jev README](https://github.com/feder-cr/jev).

---

*From the notes of [jev](https://github.com/feder-cr/jev). The espresso review on this page is
positive, negative and useful at the same time, which is the case a single score gets wrong.*
