"""Thread-safe long-lived model service with deterministic postprocessing."""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from .decisions import candidates, decode
from .prompts import BINARY_PROMPT_VERSION, compile_request
from .schema import Request


class Engine:
    def __init__(self, backend, ctx=8192, calibration=None, binary=False):
        if ctx < 1:
            raise ValueError("ctx must be positive")
        self.backend = backend
        self.ctx = ctx
        self.calibration = calibration
        # binary=True: a model trained on yes/no questions only (0/1 answers); nothing else is accepted.
        # The prompt version comes from the GGUF (`jev.prompt_version`), else the default.
        self.binary = binary
        self.binary_version = backend.metadata.get("binary_prompt_version") or BINARY_PROMPT_VERSION
        if calibration and calibration.fingerprint != backend.metadata["fingerprint"]:
            raise ValueError(
                "Calibration was fitted for a different model/runtime/prompt configuration"
            )
        self._lock = Lock()
        # All model work runs on one thread that lives as long as the process: some compute
        # backends abort when a thread that ran computations exits.
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jev-inference")

    def decide(self, request: Request | dict) -> dict:
        # Re-validate a serialized snapshot, also protecting mutable Pydantic objects.
        request = Request.model_validate(
            request.model_dump() if isinstance(request, Request) else request
        )
        started = time.perf_counter()
        if self.binary:
            return self._decide_binary(request, started)
        with self._lock:
            acquired = time.perf_counter()
            prefix, jobs = compile_request(self.backend.tokenizer, request, self.ctx)
            encoded = time.perf_counter()
            logits, timing = self._worker.submit(
                self.backend.score, prefix, jobs, request.mode
            ).result()
            answers = {}
            for job in jobs:
                question = request.questions[job.id]
                temperature = (
                    self.calibration.temperature_for(question.type, len(candidates(question)))
                    if self.calibration
                    else 1.0
                )
                answers[job.id] = decode(question, logits[job.id], temperature)
                answers[job.id]["prompt_sha256"] = job.prompt_sha256
                answers[job.id]["input_tokens"] = len(job.tokens)
        return {
            "model": self.backend.metadata,
            "mode": request.mode,
            # Tokens of the state that every question starts with: counted once in `usage`.
            "prefix_tokens": len(prefix),
            "answers": answers,
            "calibration": self.calibration.model_dump() if self.calibration else None,
            "timing": {
                **timing,
                "queue_seconds": acquired - started,
                "compile_seconds": encoded - acquired,
                "total_seconds": time.perf_counter() - started,
            },
        }

    def _decide_binary(self, request: Request, started: float) -> dict:
        """A binary model answers yes/no questions only, on the binary prompt (0/1 tokens).

        There is no choice and no score: a request with any other question type is refused.
        """
        others = [qid for qid, q in request.questions.items() if q.type != "boolean"]
        if others:
            raise ValueError(
                f"Binary model: only yes/no (noul) questions are answered; not {', '.join(others)}"
            )
        with self._lock:
            acquired = time.perf_counter()
            prefix, jobs = compile_request(self.backend.tokenizer, request, self.ctx, binary=self.binary_version)
            encoded = time.perf_counter()
            logits, timing = self._worker.submit(self.backend.score, prefix, jobs, request.mode).result()
            answers = {}
            for job in jobs:
                question = request.questions[job.id]
                temperature = self.calibration.temperature_for("boolean", 2) if self.calibration else 1.0
                answers[job.id] = decode(question, logits[job.id], temperature)
                answers[job.id]["prompt_sha256"] = job.prompt_sha256
                answers[job.id]["input_tokens"] = len(job.tokens)
        return {
            "model": self.backend.metadata | {"prompt_version": self.binary_version},
            "mode": request.mode,
            "prefix_tokens": len(prefix),
            "answers": answers,
            "calibration": self.calibration.model_dump() if self.calibration else None,
            "timing": {
                **timing,
                "queue_seconds": acquired - started,
                "compile_seconds": encoded - acquired,
                "total_seconds": time.perf_counter() - started,
            },
        }
