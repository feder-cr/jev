---
title: "A Discord moderation bot with a local LLM"
description: "Architecture sketch of a Discord moderation bot: server rules as yes/no questions to a local LLM, actions on thresholds, moderators on the middle band."
parent: "Use cases"
nav_order: 2
---

# A Discord moderation bot with a local LLM

**A Discord moderation bot can hand each new message to a local LLM as a set of yes/no
questions taken from the server rules, then act on the probabilities: delete and log the clear
breaches, post the doubtful ones to a private moderators' channel, and leave the rest alone.**
The bot is ordinary glue code; the model runs as `jev serve` on the same machine and answers in
tens of milliseconds for a chat-length message, which is fast enough that nobody notices the
check. Moderators keep the final word on everything that is not clear-cut.

The part people get wrong is not the model call. It is everything around it: which messages
the bot can even read, what happens when a raid sends a hundred messages in ten seconds, and
how a moderator overrules the bot without editing code.

This page is an architecture sketch, not a tested bot: the flow, the request per message, a
pseudocode loop, the queue, the moderator side, and the limits.

## The flow, end to end

1. Discord delivers a message event to the bot over the gateway.
2. The bot drops what it should not check: its own messages, messages from moderators,
   channels you exempt.
3. It builds one request: the message text as `state`, plus one question per server rule.
4. It posts the request to `http://127.0.0.1:8017/v1/systemone` and reads one `noul` per rule.
5. Code compares each probability to that rule's thresholds and picks an action.
6. Every decision is written to a log; doubtful ones are also posted to the moderators' channel
   with buttons to confirm or dismiss.

Nothing in steps 3 to 5 leaves the machine. Discord itself still sees every message, of course:
local inference keeps the content away from a third model provider, not away from the platform.

## What the bot can read

A fact about Discord that decides the design: message content is behind a privileged gateway
intent. Discord's developer documentation says that without the `MESSAGE_CONTENT` intent the
content, embeds, attachments, components and poll fields arrive empty, except in messages the
app sends, direct messages with the app, messages that mention the app, and messages where one
of its context menu commands is used. It also says apps that qualify for verification must be
approved to use the intent. A moderation bot that reads every message needs it switched on in
the developer portal, and a large bot needs Discord's approval.

## One request per message

```json
{
  "model": "jev-latest",
  "state": {
    "channel": "general",
    "replying_to": "Did anyone finish the raid last night?",
    "message": "lol you are all useless, uninstall"
  },
  "questions": {
    "insult":   {"type": "noul", "instructions": "Does the message insult or demean other people?"},
    "ad":       {"type": "noul", "instructions": "Does the message advertise another server, a product or a service?"},
    "spoiler":  {"type": "noul", "instructions": "Does the message reveal how the story of a game or show ends?"},
    "self_harm": {"type": "noul", "instructions": "Does the writer say they want to hurt themselves?"}
  }
}
```

Including the message it replies to is cheap and often decisive: "same" means nothing on its
own. Keep `state` short, though. Latency grows with the text read from scratch on our reference
laptop, so a chat line with one parent message is near the 26 ms end, not the 112 ms end. The question shapes come from
[content moderation with a local LLM](content-moderation-with-a-local-llm.md), which covers
turning rules into questions in more depth.

Some rules need no model at all. Invite links, mass mentions and message rate are exact
patterns and counters; check them in code first and skip the request when they already decide.

## The loop, as pseudocode

Sketch only, not tied to any Discord library and not run:

```python
RULES = {...}                      # rule name: question text
DELETE = {"insult": 0.9, "ad": 0.85, "spoiler": 0.9}
REVIEW = 0.5

on message event m:
    if m.author is bot or m.author is moderator or m.channel in EXEMPT:
        return
    body = {"model": "jev-latest",
            "state": {"channel": m.channel.name, "message": m.text},
            "questions": {k: {"type": "noul", "instructions": q} for k, q in RULES.items()}}
    answers = post(JEV_URL, body, timeout=2).answers        # on timeout: log, do nothing
    p = {k: a.noul for k, a in answers.items()}
    if p["self_harm"] >= REVIEW:
        alert moderators with m and p                       # never auto-delete this one
    elif any(p[k] >= DELETE[k] for k in DELETE):
        delete m; log(m, p, "deleted")
    elif any(v >= REVIEW for v in p.values()):
        post m and p to mod channel with confirm/dismiss buttons
    log(m, p)
```

Two choices are deliberate. A timeout does nothing rather than deleting, so the bot fails open
and a stopped server means unmoderated chat, not a silent server. And the self-harm question
never leads to a deletion, only to a person: removing that message is the wrong response.

## Bursts and the queue

`jev serve` on one CPU has a fixed amount of compute, and every request competes for the same
cores. Normal chat is far below what that allows, but a raid may not be. Put an in-process queue between the event handler and the model
call, process it in order, and when the queue is long, apply the cheap exact checks (rate,
links, new accounts) first. The difference between the latency of one answer and the capacity of
the server is the subject of
[throughput vs latency for a decision server](throughput-vs-latency-for-a-decision-server.md).

If the bot and the model are on different machines, set `JEV_API_KEY` and do not expose port
8017 to the internet; [securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md)
has the setup.

## The moderator side

The review channel is where the bot earns trust. Show the message, the rule, the probability and
two buttons. Each click is a label: "confirm" at 0.62 on insult, "dismiss" at 0.71 on ad. After a
few weeks those clicks tell you where each threshold should sit, better than any number on this
page. Store them with the question text, because when you reword a rule the old clicks describe
the old question.

The same architecture on a workplace chat, with events in and actions on thresholds, is on
[a Slack bot that uses local LLM decisions](slack-bot-with-local-llm-decisions.md).

## Where this breaks

- **English only.** jevos reads English. A server that chats in another language needs another
  model or translation first.
- **Slang and in-jokes.** Friendly insults between regulars read as insults. The review band
  catches some of it; exempting trusted roles catches more.
- **Images and voice.** The model reads text. Screenshots, stickers and voice chat are outside it.
- **Measured accuracy.** We have not measured jevos on Discord messages. On our 999 new yes/no
  questions, tone scored 0.938 and intent 0.859, which says insult and advertising questions are
  the model's better kinds, not how your server will go.

## Short answers to the questions that lead here

**Can a Discord bot use a local LLM?** Yes. The bot calls a local HTTP endpoint for each
message and acts on the returned probabilities; the model does not need a GPU.

**Is a local model fast enough for chat?** For a short message and a few rules, a request is in
the tens of milliseconds on our reference laptop. A queue handles bursts.

**Does the bot need the message content intent?** To read ordinary messages in channels, yes;
without it the content arrives empty except in the cases Discord lists.

**Should the bot delete messages on its own?** Only above a high threshold on rules where a
wrong deletion is cheap, and never on messages that suggest someone is at risk.

**See also:** [a Slack bot that uses local LLM decisions](slack-bot-with-local-llm-decisions.md),
[a Python client for local LLM decisions](python-client-for-local-llm-decisions.md) and
[human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md).

## Sources

- Message content intent, affected fields and exceptions, approval for verified apps:
  [Discord developer documentation, Gateway](https://docs.discord.com/developers/events/gateway),
  fetched 2026-09-29.
- Latency (26 ms short, 112 ms long, read from scratch), `JEV_API_KEY`, port 8017:
  the [jev README](https://github.com/feder-cr/jev) and our reference-laptop measurements.
- Accuracy by kind of question: our 999-question test set, `jevos-q4_k_m`.
- The bot design and pseudocode are an untested sketch.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which ships the model and the
server; the Discord bot on this page is a sketch we have not built.*
