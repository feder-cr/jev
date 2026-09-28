---
title: "A model cascade: small model first, large model on doubt"
description: "Answer yes/no decisions locally when the probability is clear and send only the uncertain middle band to a large model. Bands, cost and latency theory."
parent: "Agents and routing"
nav_order: 2
---

# A model cascade: small model first, large model on doubt

**A model cascade asks the small model first, keeps its answer when the probability is clearly
high or clearly low, and sends only the uncertain middle to a larger model.** With a local
yes/no model the first stage costs 50 to 220 ms on a laptop CPU and nothing per token, so the
large model is paid only for the cases that need it. Because jevos speaks the same wire format as
TypeSafe's hosted Jev, the escalation can be the same request body sent to a different base URL.

A cascade differs from a router in one way: a router decides where a request goes before any
model answers, and a cascade lets the cheap model try and uses its own confidence to decide
whether to stop. That makes the cascade only as good as the small model's probabilities, and
this page is honest about where they are and are not a good signal.

This page is the shape of a cascade, the escalation step, the cost and latency arithmetic, the
case where confidence misleads, and how to set the band from your own labelled cases.

## Three bands, two models

For each yes/no question, the local answer lands in one of three bands:

| P(yes) from the small model | What the cascade does |
|---|---|
| at or above the high bar | act on yes, done |
| at or below the low bar | act on no, done |
| in between | ask the large model, act on its answer |

The bars are yours to set, per question. A symmetric band such as 0.2 to 0.8 is a place to
start, not a recommendation. Where a wrong yes is the expensive mistake, move the high bar up;
the reasoning is on [how to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md).

The idea is not new. FrugalGPT, a 2023 paper by Chen, Zaharia and Zou, describes LLM cascades
that learn which combination of models to query for each input, and reports matching the
performance of the strongest model it tested with up to 98% cost reduction on its benchmarks.
Those are their numbers on their tasks, not a prediction for yours.

## The escalation is a URL change

jevos accepts TypeSafe Jev's request format: `model`, `state`, and named `noul` questions. Code
written for Jev's SDK works unchanged for yes/no questions. So the second stage does not need a
second integration:

```python
import requests

LOCAL = "http://127.0.0.1:8017/v1/systemone"

def decide(body, hosted_url, low=0.2, high=0.8):
    local = requests.post(LOCAL, json=body, timeout=2).json()["answers"]
    unsure = {k: q for k, q in body["questions"].items()
              if low < local[k]["noul"] < high}
    if not unsure:
        return {k: v["noul"] for k, v in local.items()}, "local"
    second = requests.post(hosted_url, json={**body, "questions": unsure}, timeout=10).json()["answers"]
    merged = {k: v["noul"] for k, v in local.items()}
    merged.update({k: v["noul"] for k, v in second.items()})
    return merged, "escalated"
```

Only the uncertain questions are sent on. Authentication for the hosted service is left out of
the sketch. Two limits apply: jevos answers only `noul` questions (`choice` and `score` are
refused with a 422), and the large model does not have to be Jev. Any model you trust more can
be the second stage; the shared wire format only makes Jev the one with no extra code.

## Cost and latency, as arithmetic

Let f be the fraction of questions that land in the middle band. Then, per request:

- expected latency is about the local time, plus f times the hosted time;
- expected paid calls are f times what you paid before, since the confident ends cost nothing
  per token.

With our measured numbers for a short request, 54 ms locally and 344 ms for the hosted Jev
from Europe with the network included, the arithmetic looks like this. The escalation fractions
are **illustrative**, not measurements:

| Escalated fraction f (illustrative) | Mean latency | Paid calls, relative to all-hosted |
|---|---|---|
| 0.1 | 54 + 34 = about 88 ms | 0.1 |
| 0.3 | 54 + 103 = about 157 ms | 0.3 |
| 0.6 | 54 + 206 = about 260 ms | 0.6 |

Past a certain f the cascade is slower than asking the large model directly, because every
escalated case pays both. The tail matters too: the slowest requests are the escalated ones,
so the p90 of a cascade can be worse than its mean suggests. Measure f on your own traffic
before deciding.

## Where confidence misleads

A cascade assumes that a wrong answer comes with a middling probability. That holds where the
model is calibrated. On the natural yes/no questions of our held-out split, the calibration
error was 0.009, which means confident answers there are right about as often as they claim.

It does not hold everywhere. On 999 questions written after training, the model made 152
mistakes by saying yes when the answer was no, against 91 the other way, and the lean sat on
arithmetic and dates. On arithmetic questions whose answer was no, the mean P(yes) was 0.59. A
confident wrong answer does not land in the middle band, so the cascade never escalates it.
The measurement is on [why a small LLM says yes when the answer is no](why-a-small-llm-says-yes.md).

Two fixes, both in design rather than in thresholds:

- **Route by kind of question as well as by confidence.** A question that needs a computation
  should not go to the small model at all. Compute it in code, or send it straight to the large
  model.
- **Keep the yes bar higher than the no bar.** On our sets the small model's no was the more
  reliable answer.

## Setting the band from labelled cases

1. Collect a hundred or more real cases per question, labelled by hand.
2. Run the small model on all of them and record P(yes).
3. For each candidate band, count how many cases fall outside it (answered locally) and how
   many of those are wrong.
4. Pick the narrowest band whose local error rate you can accept, and read f off the same table.

This is the same exercise as sizing a
[human review band](human-in-the-loop-ai-with-a-review-band.md), with a large model in the
place of the person. The two can be stacked: small model, then large model, then a person for
what is still unclear.

## When a cascade is not worth it

- **The large model is needed for most cases.** If f is high, you pay two latencies for little
  saving. Ask the large model directly.
- **The task is not yes/no.** Extraction, summaries and replies are generated text; the local
  stage has nothing to offer them.
- **The data may not leave the machine.** Then the second stage has to be local too, or a person.

## Short answers to the questions that lead here

**What is a model cascade?** A chain of models where a cheap one answers first and a more
expensive one is asked only when the first is unsure.

**How is it different from a router?** A router picks the model before anyone answers. A
cascade uses the first model's own confidence to decide whether to go on.

**Does it make every request faster?** No. Confident cases are faster; escalated ones pay both
latencies.

**Can I escalate from jevos to Jev without new code?** For yes/no questions, the request body is
the same, so the escalation is a second POST to another base URL.

**What goes wrong with cascades?** Confidently wrong answers are never escalated. On our tests
those cluster on arithmetic and dates.

**See also:** [an LLM router with yes/no questions](llm-router-with-yes-no-questions.md),
[local vs hosted LLM decisions](local-vs-hosted-llm-decisions.md) and
[reducing LLM cost with local yes/no decisions](reducing-llm-cost-with-yes-no-decisions.md).

## Sources

- Our measurements: 54 ms local and 344 ms hosted on the same short request, the 0.009
  calibration error on the held-out split, and the error direction and mean P(yes) on the
  999-question set. Latency figures are in the [jev README](https://github.com/feder-cr/jev).
- Wire format compatibility and the 422 on `choice` and `score`: the jev README.
- FrugalGPT: Chen, Zaharia and Zou, [FrugalGPT: How to Use Large Language Models While Reducing
  Cost and Improving Performance](https://arxiv.org/abs/2305.05176), arXiv 2305.05176, fetched
  2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), which answers the easy end of a
cascade. The hard part of a cascade is the case it never escalates, so we measured that first.*
