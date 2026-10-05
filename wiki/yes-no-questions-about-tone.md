---
title: "Yes/no questions about tone and emotion"
description: "Asking a local LLM about tone: anger, politeness, frustration and sarcasm as yes/no questions, what we measured, and why tone is not the same as intent."
parent: "Question design"
nav_order: 9
---

# Yes/no questions about tone and emotion

**Ask about one emotion or one quality of tone per question, name whose tone you mean, and
keep tone separate from what the writer wants: "Is the customer angry?" and "Does the customer
threaten to cancel?" are different questions with different uses.** Tone was one of the kinds
of question the first jevos answered best. On our 999-question test set it was right on 0.938 of
the tone questions, and when the correct answer was no, its average P(yes) was 0.16, the lowest
of any kind of question we measured. Per-kind numbers for jevos-v4 are not published (78.9%
overall on the same set).

The catch is that tone is easy to read and easy to misuse. A furious message can ask for
nothing, and a calm one can announce that the customer is leaving. Systems that route on anger
alone end up escalating the loud and missing the quiet, which is why the second half of this
page is about keeping tone and intent apart.

This page is how to phrase tone questions, what the measurement covers, the cases that are
hard for any reader (sarcasm, politeness, mixed tone), and how tone combines with other
questions in a decision.

## How do I phrase a question about tone?

One emotion, one subject, plain words:

```json
{
  "model": "jev-latest",
  "state": {
    "item": "wireless mouse",
    "delivered": "5 days ago",
    "customer_message": "The box arrived empty. This is the second time!"
  },
  "questions": {
    "upset":      {"type": "noul", "instructions": "Is the customer upset?"},
    "angry":      {"type": "noul", "instructions": "Is the customer angry?"},
    "polite":     {"type": "noul", "instructions": "Is the customer's message polite?"}
  }
}
```

"Is the customer upset?" is the README's own tone question, and the README's run answers it
0.83 on this text. Three habits carry over from the general rules on
[how to write yes/no questions an LLM answers well](how-to-write-yes-no-questions-for-an-llm.md):

- **Name the person.** In a thread with a customer and an agent, "Is the tone rude?" is two
  questions. "Is the agent's reply rude?" is one.
- **One emotion per question.** "Is the customer angry or frustrated?" merges two states you may
  want to treat differently. Ask both and take the larger in code if you want either.
- **Plain words over scales.** "Is the customer angry?" is easier to answer than "How negative
  is the sentiment?". If you need strength, ask boundaries ("Is the customer at least
  annoyed?", "Is the customer furious?"), as on
  [scores as yes/no thresholds](scores-as-yes-no-threshold-questions.md).

## What does the 0.938 cover?

The test set: 999 yes/no questions written after the model was finished, over 10 scenarios with
10 texts each of 40 to 150 words (emails, tickets, logs, reviews, forms), exactly half of the
answers yes. 32 of the questions were about tone, and the first jevos (`q4_k_m`) answered 0.938 of them
correctly.

Two honest qualifications. 32 questions is a small group: two or three different answers would
move the number by several points, so read it as "tone is among the strong kinds", next to
stated facts at 0.954, rather than as a precise rate. And the texts were ordinary business
writing. Social media, gaming chat, or texts full of slang and in-jokes were not in the set.

The low mean P(yes) on no-answer questions, 0.16, is the more useful number for design. It
says that when a message is not angry, the model does not tend to call it angry, so a threshold
of 0.5 on a tone question is not fighting a lean toward yes, unlike the arithmetic questions
described on [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

## The hard cases

**Sarcasm.** "Great, the third empty box this month. Fantastic service." Every word is
positive; the tone is not. Sarcasm is hard for people reading text without a voice, and we did
not measure it separately, so we have no number to give. If sarcasm is common in your texts,
ask the direct question ("Is the customer being sarcastic?") alongside the tone question, and
test both on examples from your own data.

**Politeness versus friendliness.** A message can be polite and cold ("Kindly process the
refund at your earliest convenience") or friendly and rude. Decide which one your rule needs
and use that word.

**Mixed tone.** "Thanks for the quick reply, but this is the third time and I am losing
patience." Both "Is the customer grateful?" and "Is the customer frustrated?" are correctly
yes. Two high tone answers are not a contradiction; they are the message.

**Tone of quoted text.** In a forwarded email, the angry part may be someone else. Put the new
message and the quoted one in separate fields of the state, and name the one you mean.

## Tone is not intent

Tone describes how something is said. Intent is what the writer wants to happen. They correlate
and they are not the same:

| Message | Tone | Intent |
|---|---|---|
| "This is ridiculous. Fix it." | angry | wants a fix |
| "Please cancel my plan at the end of the month." | calm | wants to leave |
| "Just letting you know the app crashed, no rush." | calm | reports a problem, no request |
| "I am so happy with this, thank you!" | pleased | no request |

A rule that escalates on anger catches the first row and misses the second, which is often the
one that costs more. Ask both kinds of question and let the decision use each for what it is:
intent decides where a message goes, tone decides how fast or how carefully. The intent side is
on [asking about intent: what does the writer want?](yes-no-questions-about-intent.md), and a
full sentiment setup is on
[sentiment analysis with yes/no questions](sentiment-analysis-with-yes-no-questions.md).

## Tone in a decision

Tone questions are good modifiers and weak triggers. In practice:

- raise priority when a message is angry, and let intent choose the queue,
- ask a person to review an automatic reply when the customer is upset,
- in evaluation, check that a generated answer is polite, one of the criteria on
  [LLM as a judge on a CPU](llm-as-a-judge-on-a-cpu.md).

## Short answers to the questions that lead here

**Can a small LLM detect anger in a message?** On our test set the first jevos answered 0.938 of 32 tone
questions correctly, with an average P(yes) of 0.16 when the answer was no. Test on your own
texts before relying on it.

**Is tone detection the same as sentiment analysis?** Close. Sentiment is usually one axis from
negative to positive; tone questions let you ask about specific emotions such as anger,
frustration or gratitude.

**Can it detect sarcasm?** We have not measured sarcasm separately. Ask about it directly and
test on your own examples.

**Should I route messages on anger?** Use anger to set priority and intent to set the route. An
angry message and an urgent one are not always the same.

**See also:** [urgency detection in customer messages](urgency-detection-in-customer-messages.md),
[review moderation with a local LLM](review-moderation-with-a-local-llm.md) and
[mainly about: questions for messages with several topics](mainly-about-questions-for-mixed-messages.md).

## Sources

- 0.938 on 32 tone questions, 0.954 on stated facts, and the mean P(yes) values on no-answer
  questions: our 999-question test set, first jevos (`jevos-q4_k_m`).
- The "upset" question and its 0.83 answer: the [jev README](https://github.com/feder-cr/jev).

---

*From the notes of [jev](https://github.com/feder-cr/jev). Tone was one of the strongest kinds
of question in our test set, and the smallest group in it, which is why this page says both.*
