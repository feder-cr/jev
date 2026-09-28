---
title: "Home Assistant automations with local LLM decisions"
description: "Call a local yes/no LLM from Home Assistant with rest_command: payload templates, response_variable, a threshold, and when conditions are better."
parent: "Integrations"
nav_order: 5
---

# Home Assistant automations with local LLM decisions

**Home Assistant can ask a local yes/no LLM about a piece of text with its RESTful Command
integration: a `rest_command` that POSTs the text and a question to `jev serve`, called from an
automation with `response_variable`, and an `if` that compares the returned `noul` with a
threshold.** The response content is parsed as JSON, so the probability is
`response['content']['answers'][<name>]['noul']`. Everything stays in the house: Home Assistant
and the decision server can run on the same machine with no cloud service involved.

The important word is text. Most automations decide on states and numbers, and Home Assistant
already does that exactly with its own conditions. The model earns its place only where the
input is free text that a condition cannot read: a notification message, an alert description,
the subject of an email that some integration exposes as a sensor.

This page is the `rest_command` definition, an automation that uses it, which questions make
sense in a home, and the networking and security notes. The YAML is a minimal sketch to adapt;
Home Assistant facts are from its documentation, fetched 2026-09-29.

## The REST command

The integration's options, per the Home Assistant docs: `url` (required, templates allowed),
`method` (default GET, so set POST), `headers`, `payload` ("a string/template to send with
request"), `content_type`, `timeout` (default 10 seconds) and `verify_ssl`. Values passed as
`data` when the action is called become template variables in the payload, as in the docs'
example.

```yaml
rest_command:
  jev_decide:
    url: http://127.0.0.1:8017/v1/systemone
    method: POST
    headers:
      authorization: !secret jev_authorization
    content_type: "application/json"
    payload: >
      {"model": "jev-latest", "state": {{ text | to_json }},
       "questions": {"q": {"type": "noul", "instructions": {{ question | to_json }}}}}
```

Two details. The `to_json` filter, which "serializes a value to a JSON-formatted string", is
what keeps a message with quotes or line breaks from producing invalid JSON; building the body by
pasting `"{{ text }}"` between quotes breaks on the first quotation mark. And the secret holds
the whole header value, `Bearer <key>`, which is needed only if the server was started with
`JEV_API_KEY` (every call except `/health` then requires it). Leave the header out otherwise.

## The automation

```yaml
automation:
  - alias: "Tell me only about notifications that need me"
    triggers:
      - ...
    actions:
      - action: rest_command.jev_decide
        data:
          text: "{{ states('sensor.last_notification_text') }}"
          question: "Does the message say that someone is waiting at the door?"
        response_variable: jev
      - if: "{{ jev['status'] == 200 and jev['content']['answers']['q']['noul'] > 0.8 }}"
        then:
          - action: notify.send_message
            target:
              entity_id: notify.my_device
            data:
              message: "{{ states('sensor.last_notification_text') }}"
```

`sensor.last_notification_text` stands for whatever entity carries the text in your setup, and
the trigger is yours to choose. The response dictionary has `status`, `content` and `headers`,
as the docs describe; checking `status` first means a `422` or a `401` does not look like a
"no". A `422` comes back when the request is something the server does not answer, such as an
unknown field or a text longer than its context.

The threshold of 0.8 is a placeholder. For a notification filter a missed alert is usually worse
than an extra one, so you may want the threshold lower, not higher; the trade-off is worked
through on [thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md).

## Questions that make sense in a home

Good ones are about what a text says:

- "Does the message say that someone is waiting at the door?"
- "Is this alert about severe weather such as a storm or flooding?"
- "Does the email ask me to do something today?"
- "Does the message say that the delivery has already arrived?"

Poor ones are questions Home Assistant can answer itself. "Is the temperature above 25
degrees?" is a numeric state condition; asking a model to compare numbers is slower and less
reliable. On our 999-question test set a small model was right 0.954 of the time on facts stated
in a text and 0.654 on number-against-threshold questions, and the reason is on
[small LLMs and arithmetic in yes/no questions](small-llm-arithmetic-yes-no-questions.md). Keep
every question to one condition; "Is someone at the door and is it after dark?" is two questions,
and the second one belongs to a time condition, as
[one condition per question](one-condition-per-question.md) explains.

## Where the server runs, and who can reach it

`jev serve` listens on `127.0.0.1:8017` by default and uses about 1.2 GB of memory with the model
loaded, CPU only. If Home Assistant runs directly on the same machine, the URL above works as it
is. If Home Assistant runs in a container or on a separate appliance, `127.0.0.1` from its point
of view is not the machine running jevos. Then start `jev serve` with `--host` set to an address
Home Assistant can reach, set `JEV_API_KEY`, and keep the port off the internet;
[securing a local LLM server with an API key](securing-a-local-llm-server-with-an-api-key.md)
has the checklist.

Speed is not a concern for a home. On an Intel Core Ultra 7 255H a short request takes about
54 ms; a small home server may well be slower, and we have not measured one, but the budget that
matters is the 10-second default timeout of `rest_command`, which is a very different order of
size.

## Where a home automation hub and this model do not fit

jevos reads English only. If your notifications arrive in another language, the options are on
[using an English-only LLM with other languages](using-an-english-only-model-with-other-languages.md).
It does not generate text, so it cannot summarise a notification or write the message you get;
it can only decide whether to send it. And it should not gate anything safety-related on its own:
a smoke alarm, a leak sensor or a lock event must reach you through plain conditions whatever a
model thinks of the text.

## Short answers to the questions that lead here

**Can Home Assistant use a local LLM without the cloud?** Yes. A `rest_command` pointed at a
server on your network is enough; no cloud account is involved.

**How do I read the JSON response in an automation?** Call the action with `response_variable`;
the result's `content` is parsed JSON, so `jev['content']['answers']['q']['noul']` is the number.

**Why does my payload fail with a quote in the message?** Build it with `to_json` instead of
putting the text between quotes by hand.

**Should I use it for sensor values?** No. Numbers and states are what Home Assistant's own
conditions do exactly.

**Does it need a GPU?** No. It runs on the CPU.

**See also:** [Local LLM yes/no decisions in n8n](n8n-local-llm-yes-no-decisions.md),
[offline AI for decisions: no network needed](offline-ai-for-decisions.md) and
[edge AI decisions on a CPU](edge-ai-decisions-on-a-cpu.md).

## Sources

- Server defaults, memory, `JEV_API_KEY` and `422`: the [jev README](https://github.com/feder-cr/jev)
  and `src/jev/api/app.py`. Latency: the README (Intel Core Ultra 7 255H, 16 threads). Accuracy by
  kind: our 999-question test set.
- [Home Assistant RESTful Command](https://www.home-assistant.io/integrations/rest_command/),
  fetched 2026-09-29.
- [Home Assistant template functions](https://www.home-assistant.io/template-functions/)
  (`states`, `to_json`) and [script syntax](https://www.home-assistant.io/docs/scripts/), fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. In a home the model reads the message; the thermostat is still a number.*
