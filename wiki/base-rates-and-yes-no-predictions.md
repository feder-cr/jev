---
title: "Base rates: why a 0.9 yes can still be wrong often"
description: "When yes is rare, wrong yeses from the many noes can outnumber the right ones: the arithmetic, the odds adjustment, and why to test on your real mix."
parent: "Probability and thresholds"
nav_order: 11
---

# Base rates: why a 0.9 yes can still be wrong often

**When yes is rare in your traffic, a good model's yeses can still be mostly wrong, because a
small error rate on the many noes produces more false yeses than there are true yeses to find.**
And a probability that was calibrated on a mix where yes was common does not stay calibrated on
a mix where yes is rare: the same 0.9 means less. The fix is not a better model but a better
measurement: check precision, and calibration, on a sample with your real proportion of yes.

This is the most common way a model that "tested at 90 percent" disappoints in production. The
test set was balanced, the traffic is not, and nobody changed anything except the one number the
test did not vary.

This page is the arithmetic with illustrative numbers, why a calibrated 0.9 moves with the base
rate, the false positive paradox, how to measure on your real mix, and what to do when yes is
rare.

## The arithmetic, with illustrative numbers

The numbers here are made up to show the effect; they are not a measurement of jevos. Take a
model that catches 90 percent of real yeses and wrongly says yes to 5 percent of real noes.
Apply it to two streams of 10,000 messages:

| | Balanced stream (50 percent yes) | Rare stream (1 percent yes) |
|---|---|---|
| real yeses | 5,000 | 100 |
| caught (true yes) | 4,500 | 90 |
| real noes | 5,000 | 9,900 |
| wrongly called yes | 250 | 495 |
| precision (share of yeses that are right) | 0.95 | 0.15 |

Same model, same threshold, same recall. On the rare stream, fewer than one yes in six is
right. Nothing about the model got worse; the pool it makes mistakes on got twenty times bigger
than the pool it finds answers in. [Precision and recall at a P(yes) threshold](precision-and-recall-at-a-threshold.md)
shows the same effect from the metric side.

## Why a calibrated 0.9 moves with the base rate

A probability is calibrated relative to the data it was checked on. If the base rate changes
and the texts of each kind otherwise look the same, the correct adjustment is on the odds scale:
multiply the odds by the ratio of new prior odds to old prior odds. Equivalently, add the log of
that ratio to the logit; the scale is explained on
[logits, log-odds and P(yes)](logits-log-odds-and-p-yes.md).

A worked example, again illustrative. Suppose a P(yes) of 0.9 was calibrated on a mix that was
half yes, so the odds are 9 to 1 and the prior odds were 1 to 1:

| New share of yes | New prior odds | Adjusted odds | Adjusted P(yes) |
|---|---|---|---|
| 50 percent | 1 | 9 | 0.90 |
| 10 percent | 0.111 | 1.0 | 0.50 |
| 2 percent | 0.0204 | 0.184 | 0.16 |

At a 2 percent base rate, the answer that looked like "nine in ten" is closer to "one in six".
Two caveats make this a guide rather than a recipe. It assumes only the proportions changed, not
the texts themselves, which is rarely exactly true. And it needs the old base rate, which for a
model you did not calibrate yourself you may not know. This page does not state the share of yes
among the held-out questions behind jevos's calibration figure (ECE 0.009 on 6,397 natural
yes/no questions), so do not apply the formula to it blindly; refit on your own mix instead, for
example with the offset of [Platt scaling](platt-scaling-for-a-yes-no-model.md).

## The false positive paradox

The general pattern has a name. Wikipedia describes the base rate fallacy as the tendency to
ignore the base rate, the general prevalence, in favour of information about the specific case,
and the false positive paradox as the case where false positives outnumber true positives. Its
worked example uses a medical test: in a population where 40 percent are infected, a positive
result means infection with about 93 percent confidence; in one where 2 percent are infected,
the same test gives about 29 percent. The test did not change. The population did.

For text decisions the rare classes are the ones people most want to automate: fraud, abuse,
threats, legal risk, urgent escalations. They are also where this effect bites hardest.

## Measure on your real mix, not only on a balanced test

Balanced test sets are useful. Our own 999-question set has exactly half yes, which makes it
easy to compare kinds of question and to see that errors lean toward yes (152 wrong yeses
against 91 wrong noes). What a balanced set cannot tell you is the precision you will see in a
stream where the answer is yes one time in fifty.

So:

- **Label a random sample of real traffic**, not a curated one, and count how often the answer
  is yes. That number is your base rate.
- **If yes is rare, oversample it for labelling and reweight when you compute precision.**
  Otherwise a few hundred labels contain almost no yeses. The sampling side is on
  [building a yes/no test set](building-a-yes-no-test-set.md).
- **Watch the base rate over time.** A campaign, a new product or a season can change it, and
  precision moves with it even if the model does not.

## What to do when yes is rare

- **Raise the threshold, and expect lower recall.** Where a wrong yes is expensive, this is the
  right trade; see [thresholds when a wrong yes costs more](thresholds-when-a-wrong-yes-costs-more.md).
- **Stack evidence.** Ask several independent-looking questions and require more than one yes,
  or combine the answer with facts from your systems (account age, sender history) in code.
- **Review instead of act.** For rare, expensive classes such as fraud, use the model to order a
  review queue, not to decide; see [fraud case triage](fraud-case-triage-with-a-local-llm.md).
- **Keep the computing out of the question.** On arithmetic and date questions the model's
  errors lean toward yes, which adds false yeses exactly where you can least afford them.

## Short answers to the questions that lead here

**Why is my model's precision so much lower in production?** Most likely because yes is rarer
in production than in your test set. Precision falls with the base rate even when the model is
unchanged.

**Does the base rate affect recall?** No. Recall is computed only on real yeses, so it depends on
the model and the threshold, not on how many noes there are.

**Can I correct P(yes) for a new base rate?** Approximately, by adjusting the odds, if you know
the old base rate and only the proportions changed. Refitting on your own labelled mix is safer.

**What is the false positive paradox?** False positives outnumbering true positives because the
condition is rare, even with an accurate test.

**How rare is too rare to automate?** There is no fixed line. Compute precision on your real mix
at your threshold and ask whether you can live with it.

**See also:** [what P(yes) means](what-p-yes-means.md),
[LLM calibration explained](llm-calibration-explained.md) and
[spam detection with yes/no questions](spam-detection-with-yes-no-questions.md).

## Sources

- Our measurements: the 999-question set (exactly half yes; 152 wrong yeses vs 91 wrong noes),
  `jevos-q4_k_m`; ECE 0.009 on 6,397 natural yes/no held-out questions, `jevos-q8_0`.
- Both tables are illustrative arithmetic, not measurements.
- [Base rate fallacy](https://en.wikipedia.org/wiki/Base_rate_fallacy) on Wikipedia, as a
  secondary pointer for the definition and the 40 vs 2 percent example, fetched 2026-09-29.

---

*From the notes of [jev](https://github.com/feder-cr/jev), whose 999-question test set is
exactly half yes on purpose, which is also why its precision says little about your traffic.*
