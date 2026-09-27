# Derived from Rizzo Flow — https://github.com/Rizzo-AI-Academy/rizzo-flow
# Copyright 2026 Simone Rizzo — Rizzo AI Academy. Licensed under the Apache License 2.0.
# Modifications for Jev: Copyright 2026 Loris Salsi. See NOTICE.
"""llama.cpp scoring: no generation, flat unpadded batches, two ways to branch a shared state.

`seq-copy` makes every question a sequence that references the prefix cells of sequence 0
(`llama_memory_seq_cp`) and scores several suffixes in one micro-batch. Models with hybrid
linear-attention memory (Qwen3.5) cannot copy sequences, so `state-restore` snapshots
sequence 0 after the prefill and puts it back before every suffix, one question at a time.
"""

import hashlib
import math
import time
from pathlib import Path

from .. import models
from ..runtime import llama_release
from ..runtime.llama_cpp import Session
from .prompts import PROMPT_VERSION, Compiled, canonical, compile_request
from .schema import Request

# What the answer-position probe asks: trivial, so a model that answers at all answers "B".
PROBE = {
    "state": "Invoice 123: payment received in full.",
    "questions": {
        "paid": {
            "type": "choice",
            "instructions": "Has the invoice been paid?",
            "options": [{"id": "no", "description": "No"}, {"id": "yes", "description": "Yes"}],
        }
    },
}
PROBE_ROUNDS = 2  # how many whitespace tokens the prefix may absorb
MIN_LETTER_MASS = 0.5
# Four questions of mixed length on one state: a full micro-batch of branches, which is where
# a runtime that cannot really share a model's memory between sequences shows it (two
# questions were not enough to expose Gemma 4 12B).
BRANCH_PROBE = {
    "state": {
        "ticket": "Hi, we were billed twice for March. Refund the duplicate today or we cancel.",
        "plan": "Business, monthly, 12 seats",
    },
    "questions": {
        "refund": {"type": "boolean", "instructions": "Does the customer ask for a refund?"},
        "churn": {"type": "boolean", "instructions": "Does the customer threaten to leave?"},
        "team": {
            "type": "choice",
            "instructions": "Which team should handle this?",
            "options": [
                {"id": "billing", "description": "Payments, invoicing, refunds"},
                {"id": "technical", "description": "Bugs, outages"},
                {"id": "sales", "description": "Pricing, new contracts"},
            ],
        },
        "anger": {
            "type": "score",
            "instructions": "How angry is the customer?",
            "levels": ["Calm", "Frustrated but civil", "Very angry or threatening"],
        },
    },
}
BRANCH_TOLERANCE = 0.05  # largest probability move allowed between shared and direct scoring

N_BATCH = 2048  # most tokens handed to one llama_decode call
# general.file_type of a GGUF file (enum llama_ftype), for files outside the registry
FILE_TYPES = {"1": "f16", "7": "q8_0", "15": "q4_k_m", "32": "bf16"}
BRANCH_STRATEGIES = ("auto", "seq-copy", "state-restore")
# Architectures whose memory is plain attention: sequence copies are known to work there.
# Everything else takes the state-restore path until measured, because an unsupported copy
# aborts inside llama.cpp instead of failing cleanly.
SEQ_COPY_ARCHITECTURES = {"spark2_5", "gemma4"}  # verified: identical probabilities to direct


def probe_answer_position(backend, rounds: int = PROBE_ROUNDS) -> float:
    """Share of the next-token probability that falls on the answer letters, on a trivial probe.

    A template can end before the point where the model answers: GLM writes "\\n" after
    `<|assistant|>`, so at the template's last position the letters carry no mass and the
    readout is noise. When the most likely token is pure whitespace, it is appended to the
    tokenizer's `answer_prefix` and the probe runs again. Returns the final letter mass.
    """
    request = Request.model_validate(PROBE)
    session = backend.session
    mass = 0.0
    for _ in range(rounds + 1):
        _, jobs = compile_request(backend.tokenizer, request, session.n_ctx)
        job = jobs[0]
        session.clear()
        row = backend._feed(job.tokens, 0, 0, True)
        full = session.logits_all(row)
        top = max(full)
        weights = [math.exp(x - top) for x in full]
        total = math.fsum(weights)
        mass = math.fsum(weights[slot] for slot in job.slots) / total
        likeliest = max(range(len(full)), key=full.__getitem__)
        piece = session.piece(likeliest)
        if mass >= MIN_LETTER_MASS or not piece or piece.strip():
            break
        backend.tokenizer.answer_prefix += piece
    session.clear()
    return mass


def probe_branch(backend) -> float:
    """Largest probability difference between shared and direct scoring of a small request.

    Sequence copies are only correct when the runtime shares every layer's memory between
    sequences; Gemma 4 12B on llama.cpp b11081 does not, while Gemma 4 E4B does. The probe
    settles it per loaded model instead of trusting the architecture name.
    """
    from .decisions import softmax

    request = Request.model_validate(BRANCH_PROBE)
    prefix, jobs = compile_request(backend.tokenizer, request, backend.session.n_ctx)
    shared, _ = backend.score(prefix, jobs, "shared")
    direct, _ = backend.score(prefix, jobs, "direct")
    return max(
        abs(a - b)
        for job in jobs
        for a, b in zip(softmax(shared[job.id]), softmax(direct[job.id]), strict=True)
    )


def resolve_branch(strategy: str, architecture: str | None) -> str:
    if strategy not in BRANCH_STRATEGIES:
        raise ValueError(f"--branch must be one of: {', '.join(BRANCH_STRATEGIES)}")
    if strategy != "auto":
        return strategy
    return "seq-copy" if architecture in SEQ_COPY_ARCHITECTURES else "state-restore"


class LlamaTokenizer:
    """The two tokenizer calls `prompts.compile_request` makes, served by the GGUF itself:
    its chat template rendered the way transformers renders it, its vocabulary for encoding."""

    def __init__(self, session, template: str):
        from jinja2.sandbox import ImmutableSandboxedEnvironment

        def raise_exception(message):
            raise ValueError(message)

        environment = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
        environment.globals["raise_exception"] = raise_exception
        self.template = environment.from_string(template)
        self.session = session
        self.pad_token_id = session.pad_token
        self.eos_token_id = session.eos_token
        # Some templates refuse a system turn; the system prompt then opens the user turn.
        self.system_folded = False
        # Text appended after the generation prompt so that the next token is the answer.
        self.answer_prefix = ""
        # transformers hands the special tokens to every template; templates such as MiniCPM5's
        # open with {{ bos_token }}, and a model trained with that BOS degrades badly without it.
        self.special_tokens = {}
        piece = getattr(session, "piece", None)
        for name in ("bos_token", "eos_token"):
            token = getattr(session, name, None)
            if piece is not None and token is not None:
                self.special_tokens[name] = piece(token)

    def apply_chat_template(self, messages, tokenize=False, **variables) -> str:
        if tokenize:
            raise ValueError("Render the text, then call encode()")
        if not self.system_folded:
            try:
                return self.template.render(messages=messages, **(self.special_tokens | variables))
            except ValueError as error:
                if "system" not in str(error).lower() or len(messages) < 2 or messages[0]["role"] != "system":
                    raise
                self.system_folded = True
        folded = [
            {"role": "user", "content": messages[0]["content"] + "\n\n" + messages[1]["content"]},
            *messages[2:],
        ]
        return self.template.render(messages=folded, **(self.special_tokens | variables))

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return self.session.tokenize(text, add_special_tokens)


class LlamaBackend:
    def __init__(
        self, session, tokenizer, metadata, batch_size=4, prefill_chunk=512, branch="seq-copy"
    ):
        if not 1 <= batch_size <= 16 or not 1 <= prefill_chunk <= 2048:
            raise ValueError("batch_size must be 1–16 and prefill_chunk 1–2048")
        if branch not in BRANCH_STRATEGIES[1:]:
            raise ValueError("branch must be seq-copy or state-restore once resolved")
        self.session = session
        self.tokenizer = tokenizer
        self.metadata = metadata
        self.batch_size = batch_size
        self.prefill_chunk = prefill_chunk
        self.branch = branch
        self._lowest_free = None

    @classmethod
    def load(
        cls,
        path,
        device="auto",
        ctx=8192,
        batch_size=4,
        prefill_chunk=512,
        threads=None,
        runtime_dir=None,
        branch="auto",
        gpu_layers=None,
    ):
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError(f"GGUF file not found at {path}. Run `jev download` first.")
        if ctx < 1:
            raise ValueError("ctx must be positive")
        if branch not in BRANCH_STRATEGIES:
            raise ValueError(f"--branch must be one of: {', '.join(BRANCH_STRATEGIES)}")
        started = time.perf_counter()
        # Hash the weights once at startup for auditability and calibration binding.
        with path.open("rb") as stream:
            sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
        pinned = models.identify(sha256)
        # The longest question is `ctx` tokens; a microbatch adds at most N_BATCH suffix tokens
        # on top of the prefix they share, so this many cells always suffice.
        session = Session.load(
            path,
            directory=runtime_dir or llama_release.locate(device),
            device=device,
            n_ctx=ctx + N_BATCH,
            n_batch=N_BATCH,
            n_ubatch=prefill_chunk,
            n_seq_max=batch_size + 1,
            threads=threads,
            gpu_layers=gpu_layers,
        )
        try:
            architecture = session.meta("general.architecture")
            template = session.chat_template()
            if not template:
                raise ValueError("The GGUF file carries no chat template")
            tokenizer = LlamaTokenizer(session, template)
            # Render once now, so a template without a system turn is known before scoring.
            tokenizer.apply_chat_template(
                [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except Exception:
            session.close()
            raise
        file_type = session.meta("general.file_type")
        chosen = session.device
        strategy = resolve_branch(branch, architecture)
        backend = cls(session, tokenizer, {}, batch_size, prefill_chunk, strategy)
        try:
            letter_mass = probe_answer_position(backend)
            # `auto` trusts a sequence copy only after seeing it agree with direct scoring.
            branch_delta = probe_branch(backend) if strategy == "seq-copy" else None
            if branch == "auto" and branch_delta is not None and branch_delta > BRANCH_TOLERANCE:
                strategy = backend.branch = "state-restore"
        except Exception:
            session.close()
            raise
        identity = {
            "model": pinned[0].name if pinned else None,
            "source": pinned[0].source if pinned else None,
            "gguf_repo": pinned[0].repo if pinned else None,
            "gguf_revision": pinned[0].revision if pinned else None,
            "source_files": {path.name: sha256},
            "precision": pinned[1].quant if pinned else FILE_TYPES.get(file_type, f"ftype{file_type}"),
            "architecture": architecture,
            "device": "gpu" if chosen else "cpu",
            "backend": chosen.backend.lower() if chosen else "cpu",
            "gpu_layers": "all" if gpu_layers is None else gpu_layers,
            "runtime": "llama.cpp",
            "llama_cpp_release": llama_release.RELEASE,
            "llama_cpp_commit": llama_release.COMMIT,
            "prompt_version": PROMPT_VERSION,
            "system_folded": tokenizer.system_folded,
            "answer_prefix": tokenizer.answer_prefix,
            "branch_strategy": strategy,
            # Binary models name their prompt version in the GGUF.
            "binary_prompt_version": session.meta("jev.prompt_version"),
        }
        backend.metadata = {
            **identity,
            "fingerprint": hashlib.sha256(canonical(identity).encode()).hexdigest(),
            "probe_letter_mass": letter_mass,
            "probe_branch_max_delta": branch_delta,
            "device_name": chosen.description if chosen else None,
            "context_cells": session.n_ctx,
            "load_seconds": time.perf_counter() - started,
        }
        return backend

    def _feed(self, tokens, start, sequence, want_logits) -> int | None:
        """Run `tokens` on one sequence, N_BATCH per call; index of the final logits row.
        llama.cpp splits each call into `prefill_chunk` micro-batches on its own."""
        last = None
        for offset in range(0, len(tokens), N_BATCH):
            piece = tokens[offset : offset + N_BATCH]
            final = want_logits and offset + len(piece) == len(tokens)
            self.session.decode(
                piece,
                range(start + offset, start + offset + len(piece)),
                [sequence] * len(piece),
                [len(piece) - 1] if final else (),
            )
            last = len(piece) - 1 if final else None
        return last

    def _groups(self, jobs, prefix_length):
        """Microbatches of up to `batch_size` suffixes that fit one llama_decode call."""
        group, used = [], 0
        for job in jobs:
            size = len(job.tokens) - prefix_length
            if group and (len(group) == self.batch_size or used + size > N_BATCH):
                yield group
                group, used = [], 0
            group.append(job)
            used += size
        if group:
            yield group

    def _track_memory(self):
        free = self.session.free_bytes()
        if free is not None:
            self._lowest_free = free if self._lowest_free is None else min(self._lowest_free, free)

    def peak_device_bytes(self) -> int | None:
        """Largest drop in free device memory since before the load. Other processes using
        the same GPU are counted too; None on the CPU."""
        if self._lowest_free is None:
            return None
        return max(self.session.idle_free - self._lowest_free, 0)

    def _seq_copy_branches(self, prefix, jobs, result):
        """Every micro-batch: branches reference the prefix cells of sequence 0, suffixes lie
        end to end without padding, each reads its own last position."""
        start = len(prefix)
        evaluated, batches = 0, 0
        for group in self._groups(sorted(jobs, key=lambda j: len(j.tokens)), start):
            for sequence in range(1, len(group) + 1):
                self.session.branch(0, sequence)
            suffixes = [job.tokens[start:] for job in group]
            if len(group) == 1:
                rows = [self._feed(suffixes[0], start, 1, True)]  # any length, in chunks
            else:
                tokens, positions, sequences, rows = [], [], [], []
                for sequence, suffix in enumerate(suffixes, start=1):
                    tokens += suffix
                    positions += range(start, start + len(suffix))
                    sequences += [sequence] * len(suffix)
                    rows.append(len(tokens) - 1)
                self.session.decode(tokens, positions, sequences, rows)
            for job, row in zip(group, rows, strict=True):
                result[job.id] = self.session.logits(row, job.slots)
            for sequence in range(1, len(group) + 1):
                self.session.drop(sequence)
            evaluated += sum(map(len, suffixes))
            batches += 1
        return evaluated, batches, 0.0

    def _state_restore_branches(self, prefix, jobs, result):
        """One question at a time on sequence 0; the prefix state is put back in between."""
        start = len(prefix)
        mark = time.perf_counter()
        snapshot = self.session.save_sequence(0)
        snapshot_seconds = time.perf_counter() - mark
        evaluated, batches = 0, 0
        for index, job in enumerate(jobs):
            if index:
                self.session.restore_sequence(snapshot, 0)
            suffix = job.tokens[start:]
            row = self._feed(suffix, start, 0, True)
            result[job.id] = self.session.logits(row, job.slots)
            evaluated += len(suffix)
            batches += 1
        return evaluated, batches, snapshot_seconds

    def score(self, prefix: list[int], jobs: list[Compiled], mode="shared"):
        if mode not in ("shared", "direct"):
            raise ValueError("Unknown execution mode")
        if not jobs:
            raise ValueError("No decisions supplied")
        if any(
            job.tokens[: len(prefix)] != prefix or len(job.tokens) <= len(prefix) for job in jobs
        ):
            raise ValueError("Invalid shared prefix")
        session = self.session
        started = time.perf_counter()
        result = {}
        prefix_seconds = snapshot_seconds = 0.0
        evaluated_tokens = 0
        batches = 0
        # A lone question has nobody to share the prefix with: one pass is the same computation
        # as `direct` and saves a call, which is a third of the latency of a short request.
        reuse = mode == "shared" and bool(prefix) and len(jobs) > 1
        if not reuse:
            for job in jobs:
                session.clear()
                row = self._feed(job.tokens, 0, 0, True)
                result[job.id] = session.logits(row, job.slots)
                evaluated_tokens += len(job.tokens)
                batches += 1
        else:
            mark = time.perf_counter()
            session.clear()
            self._feed(prefix, 0, 0, False)
            session.synchronize()
            prefix_seconds = time.perf_counter() - mark
            evaluated_tokens += len(prefix)
            branches = (
                self._seq_copy_branches if self.branch == "seq-copy" else self._state_restore_branches
            )
            evaluated, batches, snapshot_seconds = branches(prefix, jobs, result)
            evaluated_tokens += evaluated
        session.synchronize()
        self._track_memory()
        timing = {
            "inference_seconds": time.perf_counter() - started,
            "prefill_seconds": prefix_seconds,
            "snapshot_seconds": snapshot_seconds,
            "shared_prefix_tokens": len(prefix) if reuse else 0,
            "evaluated_tokens": evaluated_tokens,  # llama.cpp never pads
            "logical_input_tokens": sum(len(j.tokens) for j in jobs),
            "batches": batches,
            "branch_strategy": self.branch if reuse else None,
            "generated_tokens": 0,
        }
        if self._lowest_free is not None:
            timing["peak_device_bytes"] = self.peak_device_bytes()
        return result, timing
