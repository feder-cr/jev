---
title: "An LLM plays a Dino game on the CPU"
description: "How the jevos demo works: a Dino-style game asks a local LLM two yes/no questions per step on a CPU and jumps or ducks on P(yes). The loop, explained."
parent: "Guides"
nav_order: 5
---

# An LLM plays a Dino game on the CPU

**In the jevos demo, a Chrome Dino-style game is played by a language model that answers two
yes/no questions per step: "Should the dinosaur jump now?" and "Should the dinosaur duck
now?".** The game describes what is ahead as a small JSON object, sends it with the two
questions to the local server, and jumps or ducks when the answer's probability is above 0.5.
Everything runs on the CPU, and the model never sees a pixel.

It is a toy, and a useful one, because the loop inside it is the loop of any program that asks
a model what to do next: describe the situation, ask a decision as a yes/no question, act on
a threshold. This page walks through that loop in the demo's own code, and what it shows about
using a model as a controller.

## Run it

Start the server as in the [README](https://github.com/feder-cr/jev), then open
<http://127.0.0.1:8017/dino>. The page is served by the same server and calls the same
`/v1/systemone` endpoint as any other client. The recording in the README is at 2x speed.

## What the model is told

The game does not send an image. Every few frames it builds a description of the next obstacle:

```js
function sense() {
  const next = game.obs.find(o => o.x + o.w > DINO_X);
  if (!next) return {next_obstacle: "nothing in sight", distance: "-"};
  const dist = next.x - (DINO_X + DINO_W);
  const close = dist >= 0 && dist <= CLOSE_K * speed();
  return {next_obstacle: next.kind === "bird" ? "a flying bird" : next.name,
          distance: close ? "close ahead" : "far ahead"};
}
```

So the state looks like `{"next_obstacle": "a tall cactus", "distance": "close ahead"}`. Two
details carry the design:

- **"Close" is computed by the game, in pixels scaled by the current speed.** The model is never
  asked to judge a distance, which is arithmetic; it is told the result in words.
- **The obstacle has a name the questions can refer to**: "a small cactus", "three cacti in a
  row", "a flying bird".

That is the split recommended on [LLM policy decisions](llm-policy-decisions-put-the-rule-in-the-question.md):
code computes, the model reads.

## What the model is asked

```js
const QUESTIONS = {
  jump: {type: "noul", instructions: "A cactus close ahead must be jumped over. Should the dinosaur jump now?"},
  duck: {type: "noul", instructions: "A flying bird close ahead must be ducked under. Should the dinosaur duck now?"},
};
```

Each question carries its own rule ("a cactus close ahead must be jumped over") and then asks
the decision. The model has no idea what a Dino game is; the rule in the question is the whole
of its knowledge about the game, and it is enough.

Both questions go in one request, so the state is read once and the second answer costs less
than the first.

## What the game does with the answers

```js
if (jump > 0.5 && onGround()) { g.vy = JUMP_V; }
else if (duck > 0.5 && onGround()) { g.duck = DUCK_FRAMES; }
```

A threshold at 0.5, jump checked before duck, and no action in the air. The game waits while the
model answers and shows the time per decision on the page, so what you watch is the model's
decisions and not a race between the model and the frame rate.

## What the toy shows about models as controllers

**A decision is a yes/no question plus a threshold.** "Should I jump?" is the same shape as
"Should this ticket go to billing?" or "Should this agent call the refund tool?". The action is
code; the model only answers. The same pattern guards an agent's actions on
[gating AI agent tool calls](gating-ai-agent-tool-calls.md).

**Perception belongs to code when code can do it.** The game could have sent raw coordinates and
asked "Is the obstacle within 90 pixels?". That would be a comparison, the model's weakest kind
of question at 0.654 on our test set. Sending "close ahead" turns it into reading, the strongest.

**Two questions are better than one three-way question.** "Jump, duck, or nothing?" would need a
choice. Two independent yes/no questions plus an order of precedence in code do the same job and
each one is easy.

**Latency is the budget.** At 50 to 220 ms per decision on a laptop CPU, a model can sit inside
a loop that runs a few times a second. That is too slow for a real-time game, which is why the
demo waits, and fast enough for most software that makes decisions about messages, events or
records.

## Short answers to the questions that lead here

**Can an LLM play the Chrome Dino game?** This demo's model does, by answering two yes/no
questions about a text description of the next obstacle. It does not see the screen.

**Does it run on a GPU?** No, on the CPU, through llama.cpp.

**Is it real time?** No. The game pauses while the model answers and shows the time per
decision.

**Is this the real Chrome Dino?** No, a Chrome Dino-style game written for the demo.

**Can I use the same loop for my own agent?** Yes. Describe the state in JSON, ask each possible
action as a yes/no question with its rule, and act on a threshold in code.

**See also:** [ask a local LLM a yes/no question](ask-a-local-llm-yes-no-questions.md),
[LLM policy decisions: put the rule in the question](llm-policy-decisions-put-the-rule-in-the-question.md)
and [small LLMs and arithmetic](small-llm-arithmetic-yes-no-questions.md).

## Sources

- The game code quoted here is `src/jev/api/dino.html` in the
  [jev repository](https://github.com/feder-cr/jev).
- Latency and the demo recording: the jev README; the comparison accuracy is from our
  999-question test set.

---

*From the notes of [jev](https://github.com/feder-cr/jev), a yes/no decision model that runs on
a laptop CPU. The whole game is about 150 lines of JavaScript around two questions, which is
the point of it.*
