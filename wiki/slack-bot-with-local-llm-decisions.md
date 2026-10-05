---
title: "A Slack bot that uses local LLM decisions"
description: "How a Slack bot asks a local yes/no LLM about each message: Socket Mode, Bolt for Python, thresholds, a triage channel, and what stays local."
parent: "Integrations"
nav_order: 4
---

# A Slack bot that uses local LLM decisions

**A Slack bot that uses local decisions receives message events from Slack, sends each message
text with a few yes/no questions to a `jev serve` process on the same machine, and acts only
when a probability crosses a threshold, for example by posting the message to a triage
channel.** With Slack's Socket Mode the bot needs no public URL: it opens an outbound WebSocket
to Slack, and the decision server stays on `127.0.0.1`. The message text is in Slack anyway; what
stays local is the analysis, and no third-party model provider sees your workspace's messages.

The part people underestimate is not the model call but the event plumbing: filtering the bot's
own posts, deciding which channels to listen to, and keeping the handler fast enough that Slack
does not retry.

This page is the architecture, a short Bolt for Python sketch, the questions and thresholds,
and the limits. The code is a minimal sketch to adapt, not a tested bot; Slack facts are from
Slack's developer docs, fetched 2026-09-29.

## The architecture in four boxes

1. **Slack** delivers events. The Events API supports two delivery methods: HTTP to a public
   Request URL, or Socket Mode, which "allows your app to use the Events API and interactive
   features, without exposing a public HTTP Request URL". Slack's docs name the case this fits:
   developers "working behind a corporate firewall".
2. **The bot process** (Bolt for Python here) receives a `message` event with the channel, the
   user, the text and a timestamp.
3. **jevos** answers the questions about that text: one HTTP call to
   `http://127.0.0.1:8017/v1/systemone`, one probability per question.
4. **The bot acts** on the thresholds: post to a triage channel, add a reaction, or do nothing.

Socket Mode needs an app-level token (`xapp-...`) in addition to the bot token. For public
channel messages the event is `message.channels`, which requires the `channels:history` scope.

## The sketch

```python
import os, requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token=os.environ["SLACK_BOT_TOKEN"])
jev = requests.Session()
TRIAGE = os.environ["TRIAGE_CHANNEL_ID"]
QUESTIONS = {
    "outage": "Does the writer report that a service or tool is down or broken?",
    "help": "Is the writer asking someone for help?",
}

def decide(text):
    body = {"model": "jev-latest", "state": text,
            "questions": {k: {"type": "noul", "instructions": q} for k, q in QUESTIONS.items()}}
    r = jev.post("http://127.0.0.1:8017/v1/systemone", json=body, timeout=(3.05, 10))
    r.raise_for_status()
    return {k: a["noul"] for k, a in r.json()["answers"].items()}

@app.event("message")
def on_message(event, say):
    if event.get("subtype") or not event.get("text"):
        return                      # skip bot_message and other subtypes
    p = decide(event["text"])
    if p["outage"] >= 0.8:
        say(text=f"Possible outage report in <#{event['channel']}>", channel=TRIAGE)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
```

The Bolt parts follow Slack's own examples: `App(token=...)`, `@app.event(...)` with a handler
that takes `event` and `say`, `say(text=..., channel=...)`, and `SocketModeHandler(...).start()`.
Skipping events that carry a `subtype` matters: Slack's docs list `bot_message` among the message
subtypes, and a bot that reacts to its own posts in the triage channel loops. Both questions go
in one request because the text is read once; on the reference laptop three questions on one
text take about 66 ms against 49 ms for one.

## Fast enough for Slack's clock

For HTTP delivery, Slack expects "an HTTP 2xx within three seconds" and retries otherwise, up to
three times, with `x-slack-retry-num` and `x-slack-retry-reason` headers. In Socket Mode the app
acknowledges each envelope by its `envelope_id`. Either way the rule is the same: do not let slow
work sit between receiving an event and acknowledging it.

A local decision is not the slow part. On an Intel Core Ultra 7 255H it takes 28 ms for a short
message and 130 ms for a 191-token one. Two things can still make it slow: a burst of messages,
since each request still takes tens of milliseconds, and very long messages. If your workspace is
busy, put decisions on a small work queue in the bot so the event handler returns at once.

## Which questions, and what to do with the answers

Good bot questions are about what the message says, not what you would have to compute: "Does
the writer report that something is broken?", "Is the writer asking for help?", "Does the
message contain what looks like a password or an access token?" For the last one, a regular
expression for known token formats is the exact tool, and the model is the backstop for the
wording around it; [checking text for personal data with yes/no questions](pii-check-with-yes-no-questions.md)
explains the split.

The action should match the confidence and the cost of a mistake:

- **Reversible and cheap** (a reaction, a post in a triage channel): act at a moderate
  threshold.
- **Visible to the writer** (a reply, a reminder of the rules): require a higher one.
- **Anything punitive** (deleting, muting): do not automate it on one probability. Put the
  middle band in front of a person, as described on
  [human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

The 0.8 in the sketch is a placeholder. Log the probabilities for a week without acting, label a
hundred of them by hand, and choose the threshold from that; the method is on
[how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).

## What stays local and what does not

The model and its answers stay on your machine. The message itself does not "stay local" in any
useful sense: it is in Slack already, and anything the bot posts goes back to Slack. The benefit
is narrower and real: no additional provider receives the text for analysis, and there is no
per-token bill for reading every message. If you log decisions, the log contains message text;
treat it like any other copy of workspace data.

## Where the bot needs a person or a bigger model

jevos reads English only and answers yes/no, multiple-choice and (early) score questions only. It does not write replies; a bot that
answers questions in threads needs a generative model. Sarcasm, in-jokes and channel context it
cannot see are where a small model is weakest; on our 999-question set the first jevos got tone questions right
0.938 of the time (per-kind numbers for jevos-v4 are not published), which is good and still means mistakes at chat volume. For moderation of a
public community the design is closer to
[a Discord moderation bot with a local LLM](discord-moderation-bot-with-a-local-llm.md).

## Short answers to the questions that lead here

**Can a Slack bot use a local LLM?** Yes. The bot calls a server on its own machine; with Socket
Mode it needs no public endpoint either.

**Do I need a public URL?** Not with Socket Mode, which uses an outbound WebSocket and an
app-level token.

**Is it fast enough for Slack's 3-second limit?** One decision takes 28 to 130 ms on the
reference laptop. Queue work if message volume is high.

**Which scope reads channel messages?** For public channels, the `message.channels` event and
the `channels:history` scope.

**Can it reply to users?** It can post fixed messages. Writing a reply needs a generative model.

**See also:** [a Python client for local LLM decisions](python-client-for-local-llm-decisions.md),
[content moderation with a local LLM](content-moderation-with-a-local-llm.md) and
[Local LLM yes/no decisions in n8n](n8n-local-llm-yes-no-decisions.md).

## Sources

- Endpoint and request shape: [jev](https://github.com/feder-cr/jev). Latencies:
  the README.
  Tone accuracy: our 999-question test set, first jevos.
- [Slack Events API](https://docs.slack.dev/apis/events-api/) and
  [Using Socket Mode](https://docs.slack.dev/apis/events-api/using-socket-mode), fetched
  2026-09-29.
- [message.channels event](https://docs.slack.dev/reference/events/message.channels), fetched
  2026-09-29.
- Bolt for Python: [Socket Mode](https://docs.slack.dev/tools/bolt-python/concepts/socket-mode),
  [listening to events](https://docs.slack.dev/tools/bolt-python/concepts/event-listening), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The bot's own posts are the first thing a message listener has to learn to ignore.*
