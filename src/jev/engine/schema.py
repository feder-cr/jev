"""Strict request contract of the native engine. Model outputs never supply JSON or field names."""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]
MAX_SLOTS = 26  # every candidate is one uppercase answer letter
MAX_STATE_BYTES = 256_000


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class BaseQuestion(Strict):
    instructions: Text


class BooleanQuestion(BaseQuestion):
    type: Literal["boolean"]
    true_description: Text = "Yes. The evidence supports an affirmative answer to the question."
    false_description: Text = "No. The evidence supports a negative answer to the question."


class Option(Strict):
    id: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")]
    description: Text


class ChoiceQuestion(BaseQuestion):
    type: Literal["choice"]
    options: list[Option] = Field(min_length=2, max_length=MAX_SLOTS)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({o.id for o in self.options}) != len(self.options):
            raise ValueError("Option IDs must be unique")
        return self


class ScoreQuestion(BaseQuestion):
    type: Literal["score"]
    levels: list[Text] = Field(min_length=2, max_length=MAX_SLOTS)

    @model_validator(mode="after")
    def distinct_levels(self):
        if len(set(self.levels)) != len(self.levels):
            raise ValueError("Levels must have distinct descriptions")
        return self


Question = Annotated[
    BooleanQuestion | ChoiceQuestion | ScoreQuestion,
    Field(discriminator="type"),
]


class Request(Strict):
    state: str | dict[str, JsonValue] | list[JsonValue]
    # Questions branch from one shared state, so many of them are cheap; the bound only keeps a
    # single request from monopolising the engine.
    questions: dict[str, Question] = Field(min_length=1, max_length=1024)
    mode: Literal["shared", "direct"] = "shared"

    @model_validator(mode="after")
    def valid_state(self):
        if not self.state or (isinstance(self.state, str) and not self.state.strip()):
            raise ValueError("State must not be empty")
        rendered = json.dumps(self.state, ensure_ascii=False, allow_nan=False)
        if len(rendered.encode()) > MAX_STATE_BYTES:
            raise ValueError("State exceeds 256 KB; no silent truncation")
        if any(not key.strip() or len(key) > 128 for key in self.questions):
            raise ValueError("Question IDs must have 1–128 nonblank characters")
        return self
