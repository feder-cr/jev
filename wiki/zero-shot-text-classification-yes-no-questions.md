---
title: "Zero-shot text classification with yes/no questions"
description: "Classify text with no training data: ask a local LLM one yes/no question per label, on a CPU, and pick the label from the probabilities. Code and pitfalls."
parent: "Guides"
nav_order: 2
---

# Zero-shot text classification with yes/no questions

**You can classify text into labels with no training data by asking one yes/no question per
label and taking the label with the highest P(yes).** "Is this a billing problem?", "Is this a
shipping problem?", "Is this an account problem?": three questions about the same ticket, sent
in one request, give three probabilities, and the classification is the largest of them. On a
CPU with jevos, the text is read once for all the questions, so three labels cost much less
than three separate calls.

That is zero-shot classification in the literal sense: the labels are written in plain English
at request time, and changing them is editing a string, not retraining a model.

This page is the request, the code that turns probabilities into a label, the two cases a
naive argmax gets wrong, what to do with ordered levels, and where the approach stops working.

## Why yes/no questions instead of a list of labels

The usual zero-shot setups hand the model the list of labels and ask it to pick one. A chat
model does this by generating the label name, which you then have to match against your list;
an entailment model does it by scoring "This text is about billing" against the text, one label
at a time.

Asking a yes/no question per label is the second idea with a model built for it. Each question
is answered on its own, so a label can be described as precisely as you need ("Is the customer
asking for money back, not just complaining?") without the other labels getting in the way, and
you can add a label without touching the rest. How this compares with the entailment approach is
on [jevos vs bart-large-mnli](jevos-vs-bart-large-mnli.md), and with a few labelled examples per
class on [jevos vs SetFit](jevos-vs-setfit.md).

The cost is that the probabilities are independent. They do not sum to 1, and two of them can
both be high. The code below deals with that explicitly.

## The request

```json
{
  "model": "jev-latest",
  "state": "Hi, my card was charged but the order page still says payment pending, and now I can't log in to check it.",
  "questions": {
    "billing":  {"type": "noul", "instructions": "Is this message mainly about a payment, a charge or a refund?"},
    "shipping": {"type": "noul", "instructions": "Is this message mainly about delivery or tracking of a parcel?"},
    "account":  {"type": "noul", "instructions": "Is this message mainly about logging in or account access?"}
  }
}
```

Three habits in those instructions matter more than the model:

- **"Mainly".** Real messages touch several topics. Asking whether a topic is the main one gives
  the model a reason to say no to the secondary ones.
- **Say what the label covers.** "A payment, a charge or a refund" is a better label than
  "billing", because it is what the model can check against the text.
- **Keep them parallel.** Questions with the same structure produce probabilities you can
  compare with each other.

Each question comes back as its own `noul`, the probability that the answer is yes.

## Turning probabilities into a label

```python
import requests

LABELS = {
    "billing":  "Is this message mainly about a payment, a charge or a refund?",
    "shipping": "Is this message mainly about delivery or tracking of a parcel?",
    "account":  "Is this message mainly about logging in or account access?",
}

def classify(text, threshold=0.5):
    body = {"model": "jev-latest", "state": text,
            "questions": {k: {"type": "noul", "instructions": q} for k, q in LABELS.items()}}
    answers = requests.post("http://127.0.0.1:8017/v1/systemone", json=body).json()["answers"]
    p = {k: a["noul"] for k, a in answers.items()}
    best = max(p, key=p.get)
    if p[best] < threshold:
        return "other", p            # no label fits
    return best, p
```

`max` picks the label; the threshold decides whether any label fits at all.

## The two cases an argmax gets wrong

**Nothing fits.** If every probability is low, the message belongs to none of your labels, and
the largest of three small numbers is still a small number. Returning `"other"` below a
threshold, as above, is the fix. A separate "other" label written as a question ("Is this about
none of: payments, deliveries, accounts?") is the weaker design, because a negative definition
gives the model nothing in the text to point at.

**Two fit.** The example message above really is about a charge and about logging in. Two high
probabilities are information, not noise. For routing, pick the larger and log the pair; for
tagging, return every label above the threshold instead of only the best one.

## Ordered levels: ask thresholds, not levels

For a scale such as low, medium, high, critical, do not ask "Is the priority medium?". Ask one
question per boundary:

```json
"questions": {
  "at_least_medium":   {"type": "noul", "instructions": "Is the urgency of this message at least medium?"},
  "at_least_high":     {"type": "noul", "instructions": "Is the urgency of this message at least high?"},
  "at_least_critical": {"type": "noul", "instructions": "Is the urgency of this message critical?"}
}
```

The level is the highest boundary answered yes. Boundary questions have one clear answer each,
where "is it medium?" has two ways to be wrong, and a scale of n levels needs only n minus 1
questions.

## How much it costs

On the README's three-question example, three questions about one text take about 165 ms
together, against 103 ms for one alone, on an Intel Core Ultra 7 255H with 16 threads. The text
is the expensive part and it is read once; each extra label adds a fraction of that. So ten
labels on one ticket are one request, not ten. A deep taxonomy asked level by level is on
[product categorization with yes/no questions](product-categorization-with-yes-no-questions.md).

The limit is context, 8,192 tokens for the text and all the questions together, which leaves
room for long documents and many labels before it matters.

## Where it works and where it does not

On 999 yes/no questions written after training, the question kinds a classifier needs are the
model's strongest: 0.954 on facts stated in the text, 0.938 on tone, 0.893 on paraphrases and
0.859 on intent. Topic routing, sentiment, urgency and "does this message ask for X" all live
there.

It is weaker when the label depends on a computation: a total over a limit, a date inside a
window, a count. Those questions scored 0.58 to 0.65 on the same set, and they are better
answered by extracting the number and comparing it in code. The measurement is on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md).

And it reads English only.

## Short answers to the questions that lead here

**What is zero-shot text classification?** Classifying text into labels the model was not
trained on, described in words at request time, with no labelled examples.

**Can a small local LLM do zero-shot classification?** Yes, if each label is asked as its own
yes/no question. jevos answers each in one pass on a CPU.

**Why do the probabilities not sum to 1?** Each question is answered independently. Use a
threshold for "no label fits" and allow several labels when more than one is high.

**How many labels can I use?** As many as fit in 8,192 tokens with the text. They share one
reading of the text, so cost grows slowly.

**Is it better than fine-tuning a classifier?** It is better when labels change or you have no
data. With thousands of labelled examples and fixed labels, a fine-tuned classifier will usually
win on accuracy.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md) and
[why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## Sources

- Timing for several questions about one text, and the 8,192-token context: the
  [jev README](https://github.com/feder-cr/jev).
- Accuracy by question kind: our 999-question test set, written after training and never used
  for tuning, run on `jevos-q4_k_m`.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. Of the code on this page, the threshold for "other" is the line that matters
most.*
