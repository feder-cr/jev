---
title: "Spam detection with yes/no questions"
description: "Detect spam by asking a local LLM about promotional intent, unsolicited links and impersonation, then combining P(yes) with sender reputation in code."
parent: "Use cases"
nav_order: 3
---

# Spam detection with yes/no questions

**To use a yes/no model for spam, ask it about the signals only a reader can see (is the
message selling something, does it push a link the reader did not ask for, does it pretend to
come from someone it is not) and combine those probabilities in code with what you already know
about the sender.** The model reads meaning; your data knows the account age, the send rate and
the history. Neither alone is a good spam filter. Tune the result for precision first, because
a real message marked as spam is the mistake users do not forgive.

The trap is treating "is this spam?" as one question. Spam is not a property of the text alone:
a product announcement is spam from a stranger and a welcome email from a shop you signed up
to. The model cannot know which, so do not ask it to.

This page is the signal questions, the code that combines them with sender data, how to pick
thresholds for precision, the quarantine band, the limits, and when local inference is worth
it for spam.

## Which questions actually separate spam?

Ask about observable properties of the text, one per question:

```json
{
  "model": "jev-latest",
  "state": {
    "subject": "Your account needs attention",
    "body": "We noticed unusual activity. Click here to claim your 80% discount on premium before it expires tonight!"
  },
  "questions": {
    "promotional":  {"type": "noul", "instructions": "Is the main purpose of the message to sell something or promote an offer?"},
    "push_link":    {"type": "noul", "instructions": "Does the message urge the reader to click a link?"},
    "impersonates": {"type": "noul", "instructions": "Does the message present itself as coming from the reader's own account provider or bank?"},
    "pressure":     {"type": "noul", "instructions": "Does the message pressure the reader with a deadline or a limited-time offer?"},
    "personal":     {"type": "noul", "instructions": "Does the message refer to a specific earlier conversation with the reader?"}
  }
}
```

The last question points the other way: a message that refers to an earlier exchange is a
point in its favour. Keeping each signal separate lets you weight them, and keeps "promotional"
from being confused with "unwanted", which is not something the text can say.

These are intent and tone questions, the kinds the model reads best. On our 999 yes/no
questions, the first jevos scored 0.859 on intent and 0.938 on tone (per-kind numbers for jevos-v4
are not published). Asking whether a link's
visible text matches its target is not a reading question: parse the HTML and compare in code.

## Combining the text with the sender, in code

```python
def spam_score(p, sender):
    text = max(p["promotional"] * p["push_link"], p["impersonates"], p["pressure"] * p["push_link"])
    if p["personal"] > 0.7:
        text *= 0.5
    if sender["known_contact"] or sender["user_subscribed"]:
        return text * 0.2
    if sender["account_age_days"] < 2 or sender["sent_last_hour"] > 50:
        return min(1.0, text + 0.3)
    return text
```

The weights are illustrative, not tuned values. What the shape shows: products for signals that
must both be present (promotion and a link), a maximum for signals where one is enough
(impersonation), and sender facts applied after the model, in plain code, where they are exact.
The product and maximum rules and their assumptions are explained on
[combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md).

## Why precision comes first

A missed spam costs the reader a second. A real message in the spam folder can cost a customer,
a job offer or a password reset. So pick the threshold where false positives are rare on your
own labelled mail, and accept the recall that comes with it;
[precision and recall at a P(yes) threshold](precision-and-recall-at-a-threshold.md) shows how
moving the cut-off trades one for the other.

Two measured facts push the same way. When the first jevos was wrong on our test set, it was wrong toward
yes more often (152 wrong yeses against 91 wrong noes), and a wrong yes here is a real message
flagged. And spam is often not rare in a mailbox, but on a forum or a sign-up form it can be: a
0.9 on a kind of message that is spam once in a thousand still flags mostly innocent messages.
The arithmetic is on [base rates: why a 0.9 yes can still be wrong often](base-rates-and-yes-no-predictions.md).

## The quarantine band

Between "deliver" and "spam folder", keep a third outcome: hold, or deliver with a warning
banner, or send to a moderator if it is a forum post. The band is where the model is unsure
and where your sender data is thin. Every message a person releases from quarantine is a
labelled false positive, which is exactly the data you need to raise or lower the line.

## Where a text model is the wrong spam filter

Being straight about the limit:

- **Established filters see more than the text.** For email at volume, filters that use
  authentication results, sending infrastructure, reputation across many mailboxes and user
  reports have signals a text model never sees. A yes/no model is a feature to add for your own
  channel (a contact form, a marketplace chat, comments), not a replacement for them.
- **Spammers adapt.** Once a filter is known, messages are rewritten to slip past it. A reading
  model is harder to fool with misspellings than a keyword list, but not immune; keep the
  labelled set fresh.
- **Hidden content.** Text in images, zero-width tricks and HTML that shows something different
  from what it says are for your parser, before the model.
- **English only.** jevos reads English.
- **Not measured on spam.** We have not run jevos on a spam dataset. Measure on your own messages
  before trusting any threshold.

For the specific case of messages that try to steal credentials, see
[phishing email screening with a local LLM](phishing-email-screening-with-a-local-llm.md),
which puts more weight on header checks. For patterns that are exact (a known bad domain, a
banned phrase), [keyword rules and regex](llm-decisions-vs-keyword-rules.md) are faster and
simpler than any model.

## Is running it locally worth it for spam?

For a contact form, a comment section or in-app chat, yes: the messages include your users'
private words, the volume is too high to pay per token for comfortably, and a short message
costs about 28 ms on our reference laptop, with all five questions sharing one reading of the text. For a large
email provider, the question is moot: that is a different system with different data.

## Short answers to the questions that lead here

**Can an LLM detect spam?** It can read signals such as promotional intent, pressure and
impersonation. Combined in code with sender data, those signals make a useful filter for your
own channels.

**Why not ask "is this spam?" directly?** Whether a message is wanted depends on the sender and
the reader, which the text does not show. Ask about properties of the text and decide in code.

**What threshold should a spam filter use?** A high one, chosen on your own labelled messages so
that real messages are rarely flagged, with a quarantine band below it.

**Does it replace my email provider's spam filter?** No. It is a text signal for channels you
run yourself.

**See also:** [intent detection with a local LLM](intent-detection-with-a-local-llm.md),
[content moderation with a local LLM](content-moderation-with-a-local-llm.md) and
[thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md).

## Sources

- Accuracy by kind of question and error direction (152 vs 91): our 999-question test set,
  written after the first jevos was finished, run on the first jevos.
- Short-request latency: our measurement on the reference laptop (Intel Core Ultra 7 255H, 16
  threads), in the [jev README](https://github.com/feder-cr/jev).
- The combining weights in the code are illustrative, not fitted.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a CPU and does not know who sent the message: that part is yours.*
