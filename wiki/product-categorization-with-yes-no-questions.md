---
title: "Product categorization with yes/no questions"
description: "Categorize products with a local LLM by walking your taxonomy coarse to fine, one yes/no question per candidate. Cost per product and at scale."
parent: "Use cases"
nav_order: 17
---

# Product categorization with yes/no questions

**To categorize products with a yes/no model, walk the taxonomy from the top: ask one question
per top-level category, keep the best, then ask only about that category's children, and stop
when no child is clearly right.** A product never meets more than a few dozen questions, even in
a taxonomy with thousands of leaves, and each question is a plain reading question about a
title and a description. Attributes such as size, voltage or colour are not categories: extract
them with rules or read them from your feed, and keep the model on "what kind of thing is this".

Level by level is also what makes the cost predictable. Asking every leaf at once would mean
thousands of questions per product; walking the tree means a handful per level, and the
questions at each level are about categories that are genuinely different from each other.

This page is the walk through the tree, the request at each level, what it costs per product
and per catalog, when the model should stop and hand over, and when a trained classifier is the
better tool.

## Walking a taxonomy level by level

Most product taxonomies are trees. Google's product taxonomy for Merchant Center is a common
example: its documentation describes categories organised from broad to specific, written as a
path such as `Electronics > Communications > Telephony > Mobile Phones`, with a numeric ID for
each category as an alternative to the path. Your own taxonomy probably looks similar.

The walk:

1. **Level 1.** Ask one question per top-level category. Keep the highest if it is above a
   threshold; if none is, send the product to a person.
2. **Level 2 and below.** Ask only about the children of the category you kept. Same rule.
3. **Stop** when the best child is below the threshold, or when two children are close. Assign
   the deepest category you are confident in. A product filed correctly at level 2 is more
   useful than one filed wrongly at level 4.

Stopping early is a feature. The failure that hurts a catalog is a confident wrong leaf, which
puts a product in front of shoppers who were looking for something else.

## The request at one level

Send the product's own text as the state, and one question per candidate:

```json
{
  "model": "jev-latest",
  "state": {
    "title": "USB-C charging cable, braided, 2 m",
    "description": "Fast charging cable for phones and tablets with USB-C ports."
  },
  "questions": {
    "phones":       {"type": "noul", "instructions": "Is this product a mobile phone?"},
    "phone_access": {"type": "noul", "instructions": "Is this product an accessory used with a phone, rather than a phone itself?"},
    "computers":    {"type": "noul", "instructions": "Is this product a computer or a computer component?"},
    "audio":        {"type": "noul", "instructions": "Is this product a device for listening to or recording sound?"}
  }
}
```

The phrasing matters at the boundaries. "An accessory used with a phone, rather than a phone
itself" exists because a cable for phones is exactly where "Is this about phones?" would say yes
to the wrong node. Parallel wording across siblings, one condition per question, and the
distinguishing feature in the question are the rules from
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## What does it cost per product and per catalog?

All questions in one request share the product text, which is read once, and extra questions
are cheaper than extra requests. On the README's measured example, one question (68 tokens in
all) took 49 ms and three (95 tokens) took about 66 ms on our reference laptop (Intel Core Ultra 7
255H, 16 threads, no GPU). The mechanism is on
[many questions about one text](many-questions-about-one-text.md).

From those two points you can make a rough estimate, clearly not a measurement: each extra
question on that text cost under 10 ms, so a level with eight candidates would be in the order
of 100 ms and a three-level walk about a third of a second per product. At that rate, 100,000
products are less than half a day of sequential work on one laptop. The real figure depends on your text length and
branching, and should be measured on your catalog; how to do that honestly is on
[measuring LLM latency: median, p90 and warm-up](measuring-llm-latency-median-and-p90.md).

Two ways to bring it down:

- **Trim the state.** Title and the first sentence of the description usually decide the
  category. Marketing copy adds tokens, not signal.
- **Only categorize what changed.** New products and edited titles, not the whole catalog every
  night.

## When should the model stop and hand over?

- **Close siblings.** When the top two candidates at a level are both high and near each other,
  the product may genuinely belong in either, or the taxonomy has an overlap. Record both and
  let a person or a rule decide.
- **Nothing fits.** No candidate above the threshold at level 1 often means a product type the
  taxonomy does not have yet.
- **The deciding fact is a number.** "Is this laptop's screen at least 15 inches?" is a
  comparison, and number-against-threshold questions were right only 0.654 of the time on our
  999-question test set, against 0.954 for stated facts. Extract the number and compare in code.
- **Not English.** jevos reads English only.

For taxonomy levels that are ordered (budget, mid-range, premium), ask threshold questions
rather than one per level, as on
[scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).

## When is a trained classifier the better tool?

When you have a large catalog that is already categorized, a stable taxonomy, and years of
corrections by your merchandising team, a classifier trained on those labels will usually beat
zero-shot questions on accuracy and cost per product. The zero-shot approach wins when the
taxonomy changes often, when a new branch has no labelled products yet, or when you are
categorizing a new catalog from scratch. The trade-off is laid out on
[a yes/no LLM vs a fine-tuned BERT classifier](yes-no-llm-vs-fine-tuned-bert.md).

A common split: the trained classifier for the established branches, the yes/no walk for new
branches and for products the classifier is unsure about, and people for what neither handles.

## Short answers to the questions that lead here

**Can an LLM categorize products into my taxonomy?** Yes, if you walk the tree level by level and
ask one yes/no question per candidate at each level. We have not measured accuracy on a product
catalog, so measure on a few hundred of your categorized products first.

**Why not ask for the category path directly?** A model that returns a probability generates no
text, so there is nothing to parse and no invented category names. Walking the tree also keeps
the number of questions small.

**How many questions per product?** The number of siblings at each level you visit, summed over
the levels. Usually a few dozen at most.

**What about attributes like size or colour?** Read them from your data or extract them with
rules. They are not categories, and numbers are a weak spot for a small model.

**What if two categories both fit?** Record both, stop at the parent, or let a rule decide. Do
not force a leaf.

**See also:** [zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md),
[document classification with a local LLM](document-classification-with-a-local-llm.md) and
[throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).

## Sources

- Our measurements: the 49 ms and 66 ms timings of the README example and the reference laptop
  from the [jev README](https://github.com/feder-cr/jev); accuracy by kind of question from our
  999-question test set on `jevos-q4_k_m`. The per-product and per-catalog figures are estimates
  derived from those two timings, not measurements.
- Google Merchant Center Help,
  [Google product category](https://support.google.com/merchants/answer/6324436), structure of
  the taxonomy, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The charging cable is the example because it sits right on the line between two
branches of almost every product tree.*
