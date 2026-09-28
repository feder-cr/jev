---
title: "Mainly about: questions for messages with several topics"
description: "Real messages touch several topics. How 'mainly', 'primarily' and 'asks for' change a yes/no question, and when to allow several labels instead of one."
parent: "Question design"
nav_order: 8
---

# Mainly about: questions for messages with several topics

**When a message can touch several topics, decide first whether you want the one it is mainly
about or every topic it contains, and write the question for that: "Is this message mainly
about a payment?" for routing, "Does this message mention a payment?" for tagging.** The two
questions have different correct answers on the same text. "Mainly" gives the model a reason
to say no to the secondary topics; "mention" asks it to say yes to all of them. Neither is
wrong, but mixing them in one set of labels makes the probabilities impossible to compare.

The reason it matters is that yes/no questions per label are answered independently. Nothing
stops two of them from both coming back high, and on a mixed message that is the right
behaviour for a tagging question and a nuisance for a routing one. The wording is how you tell
the model which of the two jobs it is doing.

This page is the three qualifiers that change the job ("mainly", "primarily", "asks for"),
a request for each, how to handle two high answers, and when the one-label assumption is
itself the mistake.

## A message about two things

```json
{
  "model": "jev-latest",
  "state": "My card was charged twice for order 5521, and the tracking page has not updated in a week. Where is my parcel?",
  "questions": {
    "billing_main":   {"type": "noul", "instructions": "Is this message mainly about a payment, a charge or a refund?"},
    "shipping_main":  {"type": "noul", "instructions": "Is this message mainly about delivery or tracking of a parcel?"},
    "billing_any":    {"type": "noul", "instructions": "Does this message mention a problem with a payment or a charge?"},
    "shipping_any":   {"type": "noul", "instructions": "Does this message mention a problem with delivery or tracking?"}
  }
}
```

The correct answers to the last two are both yes: the message mentions both problems. The
correct answers to the first two are a judgment. The charge comes first; the question at the
end is about the parcel. A person might route it either way, and that is information too: a
message that is honestly about two things is one where "mainly" questions should both land
in the middle, not one at 0.9 and the other at 0.1.

## Which qualifier does what?

| Qualifier | What it asks | Use it for |
|---|---|---|
| mentions / refers to | is the topic present at all | tagging, search, compliance flags |
| mainly / primarily | is it the dominant topic | routing to one queue |
| asks for / requests | does the writer want something done about it | deciding what action to take |

"Asks for" is often the one you actually want. A message can mention billing ("I was charged
correctly, thanks") without needing anything from the billing team. "Does the customer ask for
a change to a payment or a refund?" separates the topic from the request. That is a question
about intent, and it has its own page:
[asking about intent: what does the writer want?](yes-no-questions-about-intent.md).

"Mainly" and "primarily" behave the same in practice; pick one and use it in every label
question. The parallel form is what makes the probabilities comparable, which is the fifth rule
on [how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md).

## Two high answers: pick, keep both, or ask a person

When two "mainly" questions both come back high, three reasonable responses:

- **Pick the larger and log the pair.** Fine for routing where a wrong queue costs a transfer.
- **Keep both.** If your queues can share a ticket, or a human reads the ticket anyway, send it
  to both or tag it with both.
- **Send it to triage.** If the two are close, say within 0.1 of each other and both above 0.5,
  the message is genuinely mixed, and a person decides faster than a rule.

```python
p = {k: a["noul"] for k, a in answers.items()}
main = {k: v for k, v in p.items() if k.endswith("_main")}
ranked = sorted(main, key=main.get, reverse=True)
first, second = ranked[0], ranked[1]

if main[first] < 0.5:
    route = "other"
elif main[second] > 0.5 and main[first] - main[second] < 0.1:
    route = "triage"
else:
    route = first
```

The first branch is the "nothing fits" case, the other failure of picking the largest
probability, covered with its own code on
[zero-shot text classification with yes/no questions](zero-shot-text-classification-yes-no-questions.md).

## When one label is the wrong model of the problem

Machine learning has a name for the case where one text can carry several labels at once:
multi-label classification, and the simplest method for it, binary relevance, is one yes/no
classifier per label, each answered independently. That is exactly what a set of yes/no
questions already is. If your downstream system can accept several labels, "mentions"
questions and a threshold per label are the natural design, and you do not need "mainly" at
all.

Signs you are in that case:

- the same message regularly needs two teams,
- your reports count topics, not tickets,
- people keep arguing about which single label a message "really" has.

Signs you really need one label: a single queue owns each ticket, a single SLA applies, or the
label drives an automatic action that cannot be done twice.

## Where this is measured, and where it is not

Topic questions are reading questions, which is where jevos is strongest: on our 999-question
test set, questions about facts stated in the text scored 0.954 and questions about intent
0.859. We have not measured "mainly" questions on mixed messages as their own group, so we have
no number for how often jevos picks the same dominant topic a person would. On your own data,
this is easy to test: label 30 mixed messages by hand and compare, as described on
[building a yes/no test set for your own data](building-a-yes-no-test-set.md). For the routing
system around the questions, see
[support ticket routing with yes/no questions](support-ticket-routing-with-yes-no-questions.md).

## Short answers to the questions that lead here

**How do I classify a message that is about two things?** Decide whether you want its main
topic or all its topics. Ask "Is this mainly about X?" for the first and "Does this mention X?"
for the second.

**What does "mainly" do in a yes/no question?** It asks whether the topic is the dominant one,
which gives the model a reason to say no to secondary topics.

**Can a text have more than one label?** Yes. That is multi-label classification, and one
yes/no question per label with its own threshold handles it directly.

**What if two labels both score high?** Pick the larger for routing and log both, keep both for
tagging, or send close pairs to a person.

**See also:** [email triage with a local LLM](email-triage-with-a-local-llm.md),
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md) and
[one condition per question](one-condition-per-question.md).

## Sources

- 0.954 on stated facts and 0.859 on intent: our 999-question test set, `jevos-q4_k_m`.
- Definition of multi-label classification and binary relevance:
  [Multi-label classification on Wikipedia](https://en.wikipedia.org/wiki/Multi-label_classification),
  fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which answers each label's question
on its own, so the choice between one label and several stays in your code.*
