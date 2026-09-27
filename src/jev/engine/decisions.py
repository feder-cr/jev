"""Pure, deterministic decoding of option logits into typed answers.

The `confidence` statistics reproduce every numeric example in the public Jev documentation
(see NOTICE). They describe the shape of a distribution, not the probability of being right.
"""

import math
from dataclasses import dataclass

from .schema import BooleanQuestion, ChoiceQuestion, Question, ScoreQuestion


@dataclass(frozen=True)
class Candidate:
    id: str
    description: str
    value: float | None = None


def candidates(question: Question) -> list[Candidate]:
    """The answer slots of a question, in prompt order (letter A first)."""
    if isinstance(question, BooleanQuestion):
        return [
            Candidate("false", question.false_description, 0),
            Candidate("true", question.true_description, 1),
        ]
    if isinstance(question, ChoiceQuestion):
        return [Candidate(o.id, o.description) for o in question.options]
    if isinstance(question, ScoreQuestion):
        return [Candidate(str(i), level, i) for i, level in enumerate(question.levels)]
    raise TypeError("Unsupported question")


def softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("Temperature must be finite and positive")
    if len(logits) < 2 or not all(math.isfinite(x) for x in logits):
        raise ValueError("At least two finite logits are required")
    maximum = max(logits)
    weights = [math.exp((x - maximum) / temperature) for x in logits]
    total = sum(weights)
    return [x / total for x in weights]


def _normalized(probabilities: list[float]) -> list[float]:
    total = math.fsum(probabilities)
    if total <= 0:
        return [1.0 / len(probabilities)] * len(probabilities)
    return [p / total for p in probabilities]


def choice_confidence(probabilities: list[float]) -> float:
    """Peak probability rescaled from uniform (0) to certainty (1): (p_max - 1/n) / (1 - 1/n)."""
    if len(probabilities) == 1:
        return 1.0
    ps = _normalized(probabilities)
    uniform = 1.0 / len(ps)
    return max(0.0, min(1.0, (max(ps) - uniform) / (1.0 - uniform)))


def score_confidence(probabilities: list[float]) -> float:
    """Concentration around the modal level, ordinal-aware: 1 - E|i - mode| / MAD of uniform."""
    if len(probabilities) == 1:
        return 1.0
    ps = _normalized(probabilities)
    n = len(ps)
    mode = max(range(n), key=ps.__getitem__)
    distance = math.fsum(p * abs(i - mode) for i, p in enumerate(ps))
    center = (n - 1) / 2
    uniform_mad = math.fsum(abs(i - center) for i in range(n)) / n
    return max(0.0, min(1.0, 1.0 - distance / uniform_mad))


def decode(question: Question, logits: list[float], temperature: float = 1.0) -> dict:
    """Typed answer from the logits of the answer letters, in candidate order."""
    choices = candidates(question)
    if len(logits) != len(choices):
        raise ValueError("Logit count does not match the declared candidates")
    ps = softmax(logits, temperature)
    winner = choices[max(range(len(ps)), key=ps.__getitem__)]
    result = {
        "type": question.type,
        "probabilities": {c.id: p for c, p in zip(choices, ps, strict=True)},
        "option_logits": {c.id: x for c, x in zip(choices, logits, strict=True)},
        "legend": {c.id: c.description for c in choices},
        "temperature": temperature,
    }
    if question.type == "choice":
        result["choice"] = winner.id
        result["confidence"] = choice_confidence(ps)
    elif question.type == "score":
        result["score"] = math.fsum(c.value * p for c, p in zip(choices, ps, strict=True))
        result["confidence"] = score_confidence(ps)
    else:
        result["value"] = winner.id == "true"
        result["noul"] = ps[1]  # P(true): what the Jev-shaped `noul` answer reports
    return result
