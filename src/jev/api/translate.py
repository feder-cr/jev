"""Between the Jev wire format and the native engine request and answers."""

from pathlib import Path

from ..engine.prompts import canonical
from ..engine.schema import Request
from . import wire

# `jev-latest`, `jev-preview` and pinned `jev-x.y.z` names are accepted so that clients written
# for the hosted API work unchanged; the response always names the model that answered.
ALIAS_PREFIX = "jev-"
# Used when a question arrives without instructions, which the published schema allows.
DEFAULT_INSTRUCTIONS = {
    "noul": "Does the evidence support a yes?",
    "choice": "Which option fits the evidence best?",
    "score": "Which level fits the evidence best?",
}


class WireError(ValueError):
    """A request the engine cannot answer, reported as a 422 at `loc`."""

    def __init__(self, loc: list, message: str):
        super().__init__(message)
        self.loc = loc


def text(value) -> str:
    """Instructions and criteria may be strings, objects or arrays; the prompt takes text."""
    return value.strip() if isinstance(value, str) else canonical(value)


def native_question(definition: dict) -> tuple[dict, list[str]]:
    """Native question from a Jev question; returns it with the answer keys in slot order.

    Choice options get positional ids, since Jev option names are free-form strings; the name
    and its description both reach the prompt, as in Jev.
    """
    kind = definition["type"]
    instructions = text(definition.get("instructions") or "") or DEFAULT_INSTRUCTIONS.get(kind, "")
    criteria = definition.get("criteria")
    if kind == "choice":
        keys = list(criteria)
        return {
            "type": "choice",
            "instructions": instructions,
            "options": [
                {
                    "id": f"o{index}",
                    "description": key if detail in (None, "") else f"{key}: {text(detail)}",
                }
                for index, (key, detail) in enumerate(criteria.items())
            ],
        }, keys
    if kind == "score":
        return {
            "type": "score",
            "instructions": instructions,
            "levels": [text(level) for level in criteria],
        }, [str(index) for index in range(len(criteria))]
    if kind == "noul":
        question = {"type": "boolean", "instructions": instructions}
        criteria = criteria or {}
        if criteria.get("true") not in (None, ""):
            question["true_description"] = "Yes. " + text(criteria["true"])
        if criteria.get("false") not in (None, ""):
            question["false_description"] = "No. " + text(criteria["false"])
        return question, ["false", "true"]
    raise ValueError(f"Unknown question type {kind}")


def to_native(request: wire.SystemOneRequest) -> tuple[Request, dict[str, list[str]]]:
    questions, keys = {}, {}
    for qid, question in request.questions.items():
        questions[qid], keys[qid] = native_question(question.model_dump())
    return Request.model_validate({"state": request.state, "questions": questions}), keys


def to_wire(
    request: wire.SystemOneRequest, response: dict, keys: dict[str, list[str]], served: str
) -> dict:
    answers = {}
    for qid, question in request.questions.items():
        native = response["answers"][qid]
        ps = native["probabilities"]
        if question.type == "noul":
            answers[qid] = {"type": "noul", "noul": ps["true"]}
        elif question.type == "choice":
            named = {name: ps[f"o{index}"] for index, name in enumerate(keys[qid])}
            answers[qid] = {
                "type": "choice",
                "choice": max(named, key=named.get),
                "probabilities": named,
                "confidence": native["confidence"],
            }
        else:
            answers[qid] = {
                "type": "score",
                "score": native["score"],
                "legend": {str(index): level for index, level in enumerate(question.criteria)},
                "probabilities": {key: ps[key] for key in keys[qid]},
                "confidence": native["confidence"],
            }
    # The state is read once however many questions branch from it; nothing is generated.
    prefix = response.get("prefix_tokens", 0)
    compiled = sum(answer["input_tokens"] for answer in response["answers"].values())
    return {
        "model": served,
        "answers": answers,
        "usage": {
            "input_tokens": compiled - prefix * (len(answers) - 1),
            "output_tokens": 0,
        },
    }


def served_name(metadata: dict) -> str:
    """The id this server answers as: registry model and quantization, else the file name."""
    if metadata.get("model") and metadata.get("precision"):
        return f"{metadata['model']}-{metadata['precision']}"
    files = metadata.get("source_files") or {}
    return Path(next(iter(files), "local")).stem.lower() or "local"


def resolve_model(requested: str, served: str) -> str:
    if requested == served or requested.startswith(ALIAS_PREFIX):
        return served
    raise WireError(
        ["body", "model"],
        f"Unknown model {requested!r}: this server answers as {served!r} and accepts any "
        f"'{ALIAS_PREFIX}*' alias",
    )
