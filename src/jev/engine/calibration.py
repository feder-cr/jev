# Derived from Rizzo Flow — https://github.com/Rizzo-AI-Academy/rizzo-flow
# Copyright 2026 Simone Rizzo — Rizzo AI Academy. Licensed under the Apache License 2.0.
# Modifications for Jev: Copyright 2026 Loris Salsi. See NOTICE.
"""Temperature fitting on a separate labelled set; never claim validation from the fit loss.

One temperature per question type, plus one per (type, option-count band) where the band has
enough rows: a 2-way question and a 20-way one are not sharpened the same way.
"""

import hashlib
import math
from typing import Annotated, Literal

from pydantic import Field

from .decisions import softmax
from .prompts import canonical
from .schema import Strict

TYPES = ("boolean", "choice", "score")
MIN_ROWS = 10


def band(count: int) -> str:
    """Option-count band a question falls in."""
    if count <= 2:
        return "2"
    if count <= 5:
        return "3-5"
    if count <= 10:
        return "6-10"
    return "11+"


class Calibration(Strict):
    version: Literal[1] = 1
    fingerprint: str
    dataset_sha256: str
    # "choice" for the type-level fit, "choice:3-5" for a band-level one
    temperatures: dict[str, Annotated[float, Field(gt=0, allow_inf_nan=False)]]
    fit_metrics: dict
    status: Literal["fitted_requires_held_out_validation"] = "fitted_requires_held_out_validation"

    @classmethod
    def from_file(cls, path):
        item = cls.model_validate_json(path.read_text(encoding="utf-8"))
        if any(not math.isfinite(t) or t <= 0 for t in item.temperatures.values()):
            raise ValueError("Calibration temperatures must be finite and positive")
        return item

    def temperature_for(self, kind: str, count: int) -> float:
        """The band-level temperature when fitted, else the type-level one, else 1."""
        return self.temperatures.get(
            f"{kind}:{band(count)}", self.temperatures.get(kind, 1.0)
        )


class LabeledLogits(Strict):
    type: Literal["boolean", "choice", "score"]
    logits: list[float] = Field(min_length=2, max_length=26)
    label_index: int = Field(ge=0)


def _fit(group: list[LabeledLogits]) -> tuple[float, dict]:
    def loss(log_temperature):
        t = math.exp(log_temperature)
        total = 0.0
        for row in group:
            values = [x / t for x in row.logits]
            top = max(values)
            total += top + math.log(sum(math.exp(v - top) for v in values)) - values[row.label_index]
        return total / len(group)

    # Positive one-dimensional search including T=1; bounded to avoid singular solutions.
    grid = [math.log(0.05) + i * math.log(400) / 240 for i in range(241)] + [0.0]
    best = min(grid, key=loss)
    return math.exp(best), {
        "rows": len(group),
        "fit_nll_before": loss(0),
        "fit_nll_after": loss(best),
    }


def fit_temperature(rows: list[dict], fingerprint: str) -> Calibration:
    if not rows:
        raise ValueError("Calibration requires labeled rows")
    groups: dict[str, list[LabeledLogits]] = {}
    for raw in rows:
        row = LabeledLogits.model_validate(raw)
        softmax(row.logits)
        if row.label_index >= len(row.logits):
            raise ValueError("Label index is outside the candidate list")
        groups.setdefault(row.type, []).append(row)
        groups.setdefault(f"{row.type}:{band(len(row.logits))}", []).append(row)
    temperatures, metrics = {}, {}
    for key, group in groups.items():
        if ":" not in key and len(group) < MIN_ROWS:
            raise ValueError(f"Provide at least {MIN_ROWS} calibration examples for {key}")
        if len(group) < MIN_ROWS:
            continue  # a band too thin to fit falls back to its type-level temperature
        temperatures[key], metrics[key] = _fit(group)
    return Calibration(
        fingerprint=fingerprint,
        dataset_sha256=hashlib.sha256(canonical(rows).encode()).hexdigest(),
        temperatures=temperatures,
        fit_metrics=metrics,
    )
