---
title: "Snake AI: a local model vs a cloud API"
description: "Our Snake race of 2026-10-09: a local jevos GGUF against the hosted Jev API, same seed, 12 seconds, 61 apples to 3. Why it measures latency, not skill."
parent: "Measurements"
nav_order: 5
---

# Snake AI: a local model vs a cloud API

**In our Snake race of 2026-10-09, a local model ate 61 apples in 12 seconds and a cloud API ate
3, on the same 12x12 board with the same seed, because the local one decided in a median of 21 ms
and the cloud one in 340 ms.** The local side was jevos-v4 as the q4_k_m GGUF file, served by
llama.cpp on a laptop GPU; the cloud side was TypeSafe's Jev (`typesafe/jev-1.13`) through
OpenRouter's decisions endpoint, over the internet. Neither model planned a route: the game code
worked out what each move would do, worded it as a yes/no question, and played the move with the
highest P(yes).

It is a latency measurement in a loop, not a skill contest. Before the race we checked offline
that both models pick the right move in the same situations, and on the six tasks in the jev
README, Jev is the more accurate model. The race shows how many right answers fit in the same
12 seconds when each one has to cross the internet first.

Conflict of interest, in one line: we build jevos; Jev is TypeSafe AI's, and we are not
affiliated.

This page is the setup, how a yes/no model can steer a snake, why the clock decides, the numbers,
what they do not show, and the other games.

## How was the race set up?

Same game, same seed, same 12 seconds of wall-clock time, same questions. Only the model
answering them changed.

| | Local | Cloud |
|---|---|---|
| Model | jevos-v4, `jevos-v4-q4_k_m.gguf` | Jev, `typesafe/jev-1.13` |
| Runtime | llama.cpp on a laptop GPU | OpenRouter's decisions endpoint |
| Internet in the loop | no | yes, both ways |

Unlike the rest of this wiki, the local side is not the `jev` binary from the README, which runs
8-bit weights on a CPU; it is the GGUF file from the same release, on a GPU. So the 21 ms here and
the README's 28 ms for a short request are different measurements, not comparable. The file and
how to fetch it are on
[download a GGUF model from Hugging Face](download-a-gguf-model-from-hugging-face.md).

## How does a yes/no model play Snake?

It never sees the board. The game code takes each move the snake could make, computes what it
would do, and writes that down. The model reads the sentence and answers one question:

```text
Moving up: the snake moves closer to the food. Should the snake move up?
```

The other effects the code can write are "farther from the food", "would eat the food", "would
crash into a wall and die" and "would be cut off, with no free path left to the food". That last
one is pathfinding, done by the code. The move whose question gets the highest P(yes) is played.

It is the split this wiki recommends for any decision: code computes what code can compute, and
the model gets [one condition per question](one-condition-per-question.md). Letting code know the
answer in advance is also how we build test sets, on
[generating test questions with answers computed by code](generating-test-questions-with-code.md).

## Why does latency decide a race against the clock?

Because the snake moves only when an answer arrives, and the clock keeps running while it is on
its way. In the same 12 seconds jevos made
558 moves and Jev 30. As rough arithmetic from the medians, not a separate measurement, 558
decisions at 21 ms come to about 11.7 seconds and 30 at 340 ms to about 10.2: both players spent
nearly all their time waiting for answers.

The offline check is what makes this reading fair. In the same situations both models chose the
right move, so Jev's 3 apples are not a verdict on its judgement; they are what 30 moves buy. Its
time per decision is mostly the network round trip, which no model can shorten. Where that time
goes is on
[why a hosted LLM API cannot answer in 50 ms](why-a-hosted-llm-api-cannot-answer-in-50-ms.md),
and what a given decision time fits is on
[latency budgets: where a 200 ms model fits](latency-budgets-for-llm-decisions.md).

## What were the Snake numbers?

| Snake, 12x12 board | jevos-v4, local GGUF | Jev, cloud |
|---|---|---|
| Apples in 12 seconds | 61 | 3 |
| Moves in 12 seconds | 558 | 30 |
| Median time per decision | 21 ms | 340 ms |
| Apples in 60 seconds | 254 | 20 |

One race of each length, on one laptop, one connection and one day: one case of one measurement,
not a benchmark. From a client closer to the API, or on another GPU, the numbers would differ.

## What does the race not show?

Being straight about the limits:

- **That jevos is the better model.** On the README's six tasks Jev scores higher on every one,
  for example 1.00 against 0.95 on admission rules and 0.88 against 0.76 on ShARC. The table is
  on [jevos vs Jev vs Laya](jevos-vs-jev-vs-laya.md).
- **Game skill.** The hard part of Snake, finding a path, was code. If you want a Snake AI that
  plays well, you need no model: play the move the pathfinding already prefers. A model earns its
  place when the facts arrive as text that code cannot read, which a 12x12 grid is not.
- **A CPU result.** The `jev` binary's CPU latencies are on
  [the fastest AI model for yes/no decisions](fastest-ai-model-for-yes-no-decisions.md).
- **Anything about the cloud in general.** One hosted model, one route, one location. A
  turn-based game that waits for every answer would hide most of the round trip.

## How did the other games go?

Same setup; 12 seconds unless stated.

| Game | jevos-v4, local GGUF | Jev, cloud | Median per decision |
|---|---|---|---|
| Pong, head to head on one field | 11 points | 0 points | about 31 vs 348 ms |
| Breakout, same wall | 20 bricks, 1 ball lost | 2 bricks, 10 balls lost | about 17 vs 306 ms |
| Whac-A-Mole, same moles and bombs | 60 moles | 17 moles | about 13 vs 332 ms |
| Knife Hit, logs cleared | 11 | 0 | about 18 vs 320 ms |
| Rubik's cube, same 20-move scramble | solved in 1.32 s | solved in 7.26 s | 42 vs about 350 ms |

Over the full 15-second Knife Hit run it was 14 logs to 0, with 0 crashes against 8. In
Whac-A-Mole, Jev also swung at holes already empty and hit one bomb. Pac-Man ended 288 dots to 33,
2048 at a biggest tile of 1024 to 32, Tetris 145 lines to 8.

Two caveats. Tetris is the exception to the offline check: Jev also misreads some placements, so
that gap is not only latency. And the cube trial measures speed, not solving: the code knows the
scramble and words each of the 12 possible turns as one move closer to or farther from solved;
both made 20 turns, none wrong.

## Short answers to the questions that lead here

**Can an LLM play Snake?** A small one can, if code turns the board into one sentence per
possible move and asks a yes/no question about each. In our race it made 558 moves in 12 seconds.

**Why did the cloud API lose?** Time per decision: a median of 340 ms, mostly network round trip,
against 21 ms locally. Offline, both models picked the right moves.

**Is jevos more accurate than Jev?** No. On the six tasks in the jev README, Jev scores higher on
each. The race measures latency in a loop.

**Can I run the same model file?** Yes. `jevos-v4-q4_k_m.gguf` is in the jevos-v4 release and on
Hugging Face as feder-cr/jev, for llama.cpp and tools built on it.

**See also:** [an LLM on a laptop: what it can do in real time](an-llm-on-a-laptop.md),
[local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md) and
[CPU or GPU for a small LLM](cpu-or-gpu-for-a-small-llm.md).

## Sources

- The game races of 2026-10-09 and the offline check of the moves before them: our own
  measurement, with the setup above.
- The six-task accuracy and the CPU latencies of `jev`: our own measurements, in the
  [jev README](https://github.com/feder-cr/jev); the model file is on the
  [jevos-v4 release](https://github.com/feder-cr/jev/releases/tag/jevos-v4).
- No outside source is used on this page; every number on it is ours.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which files the Snake race under
latency, because the game code knew where the food was before either model answered.*
