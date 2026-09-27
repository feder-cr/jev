"""The Jev wire format, as published in its API reference and OpenAPI schema.

Requests reject unknown fields so that a misspelt `criteria` fails loudly instead of being
answered without it. Answers carry exactly the fields Jev documents.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

# Every option is one answer letter in the prompt. Jev accepts 255; beyond 26 the question has
# to be split (a coarse question, then a fine one) until two-stage selection is implemented.
MAX_CHOICE_OPTIONS = 26
MIN_SCORE_LEVELS, MAX_SCORE_LEVELS = 2, 10

Structured = str | dict[str, JsonValue] | list[JsonValue]


class Wire(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoulCriteria(Wire):
    true: Structured | None = None
    false: Structured | None = None


class NoulQuestion(Wire):
    type: Literal["noul"]
    instructions: Structured | None = None
    criteria: NoulCriteria | None = None


class ChoiceQuestion(Wire):
    type: Literal["choice"]
    instructions: Structured | None = None
    criteria: dict[str, Structured | None]

    @model_validator(mode="after")
    def options(self):
        if any(not name.strip() for name in self.criteria):
            raise ValueError("Choice option names must not be blank")
        count = len(self.criteria)
        if count < 2:
            raise ValueError("A choice needs at least two options")
        if count > MAX_CHOICE_OPTIONS:
            raise ValueError(
                f"A choice takes at most {MAX_CHOICE_OPTIONS} options on this server, one answer "
                f"letter each; got {count}. Split it into a coarse question and a fine one."
            )
        return self


class ScoreQuestion(Wire):
    type: Literal["score"]
    instructions: Structured | None = None
    criteria: list[Structured]

    @model_validator(mode="after")
    def levels(self):
        if not MIN_SCORE_LEVELS <= len(self.criteria) <= MAX_SCORE_LEVELS:
            raise ValueError(
                f"A score takes {MIN_SCORE_LEVELS} to {MAX_SCORE_LEVELS} ordered levels; "
                f"got {len(self.criteria)}"
            )
        return self


Question = Annotated[NoulQuestion | ChoiceQuestion | ScoreQuestion, Field(discriminator="type")]


class SystemOneRequest(Wire):
    state: Structured
    model: str = Field(min_length=1)
    questions: dict[str, Question] = Field(min_length=1)


class NoulAnswer(BaseModel):
    type: Literal["noul"] = "noul"
    noul: float


class ChoiceAnswer(BaseModel):
    type: Literal["choice"] = "choice"
    choice: str
    probabilities: dict[str, float]
    confidence: float


class ScoreAnswer(BaseModel):
    type: Literal["score"] = "score"
    score: float
    legend: dict[str, Any]
    probabilities: dict[str, float]
    confidence: float


Answer = Annotated[NoulAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")]


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int = 0


class SystemOneResponse(BaseModel):
    model: str
    answers: dict[str, Answer]
    usage: Usage


class ModelMetadata(BaseModel):
    name: str
    description: str
    release_date: str


class ModelMetadataList(BaseModel):
    models: list[ModelMetadata]
