---
title: "Probability and thresholds"
description: "What P(yes) means, calibration, ECE, temperature and Platt scaling, and how to pick thresholds and review bands for real decisions."
nav_order: 5
has_children: true
---

# Probability and thresholds

jevos returns a probability, not a word, and a probability is only as useful as the threshold you put on it. These pages cover what the number means, how to check that it is calibrated on your data, and how to turn it into decisions whose mistakes cost what you expect.

- [What P(yes) means, and what it does not](what-p-yes-means.md)
- [LLM calibration explained with yes/no answers](llm-calibration-explained.md)
- [Expected calibration error (ECE), explained](expected-calibration-error-explained.md)
- [Temperature scaling for LLM probabilities](temperature-scaling-for-llm-probabilities.md)
- [Platt scaling for a yes/no model](platt-scaling-for-a-yes-no-model.md)
- [Reading a reliability diagram](reading-a-reliability-diagram.md)
- [How to choose a threshold for P(yes)](how-to-choose-a-threshold-for-p-yes.md)
- [Thresholds when a wrong yes costs more than a wrong no](thresholds-when-a-wrong-yes-costs-more.md)
- [Human in the loop AI with a review band](human-in-the-loop-ai-with-a-review-band.md)
- [Precision and recall at a P(yes) threshold](precision-and-recall-at-a-threshold.md)
- [Base rates: why a 0.9 yes can still be wrong often](base-rates-and-yes-no-predictions.md)
- [Combining yes/no answers with AND, OR and NOT](combining-yes-no-answers-and-or-not.md)
- [Logits, log-odds and P(yes)](logits-log-odds-and-p-yes.md)
- [LLM confidence scores: probabilities vs self-reports](llm-confidence-score-probability-vs-self-report.md)
