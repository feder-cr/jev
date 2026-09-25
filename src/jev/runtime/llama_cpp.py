# Derived from Rizzo Flow — https://github.com/Rizzo-AI-Academy/rizzo-flow
# Copyright 2026 Simone Rizzo — Rizzo AI Academy. Licensed under the Apache License 2.0.
# Modifications for Jev: Copyright 2026 Loris Salsi. See NOTICE.
"""ctypes binding to libllama, limited to what scoring needs: no sampling, no generation.

Struct layouts and signatures are transcribed from `include/llama.h` and
`ggml/include/ggml-backend.h` of the release pinned in `llama_release.py`. Structs are passed
by value, so a library built from another commit can crash instead of failing cleanly.
"""

import ctypes
import os
import sys
from ctypes import (
    POINTER,
    c_bool,
    c_char_p,
    c_float,
    c_int,
    c_int8,
    c_int32,
    c_size_t,
    c_uint8,
    c_uint32,
    c_uint64,
    c_void_p,
)
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from . import llama_release

LOG_ENV = "JEV_LLAMA_LOG"  # set to 1 to see llama.cpp's own info/debug lines
GPU_LAYERS = 999  # more than any model has: offload everything
# enum ggml_backend_dev_type
DEVICE_KINDS = {0: "cpu", 1: "gpu", 2: "igpu", 3: "accel", 4: "meta"}
SPLIT_MODE_NONE = 0
FLASH_ATTN_ENABLED = 1  # enum llama_flash_attn_type
LOG_LEVEL_WARN, LOG_LEVEL_ERROR = 3, 4


class ModelParams(ctypes.Structure):
    _fields_ = [
        ("devices", POINTER(c_void_p)),
        ("tensor_buft_overrides", c_void_p),
        ("n_gpu_layers", c_int32),
        ("split_mode", c_int),
        ("load_mode", c_int),
        ("lazy_mode", c_int),
        ("main_gpu", c_int32),
        ("tensor_split", c_void_p),
        ("progress_callback", c_void_p),
        ("progress_callback_user_data", c_void_p),
        ("kv_overrides", c_void_p),
        ("vocab_only", c_bool),
        ("check_tensors", c_bool),
        ("use_extra_bufts", c_bool),
        ("no_host", c_bool),
        ("no_alloc", c_bool),
        ("load_mtp", c_bool),
    ]


class ContextParams(ctypes.Structure):
    _fields_ = [
        ("n_ctx", c_uint32),
        ("n_batch", c_uint32),
        ("n_ubatch", c_uint32),
        ("n_seq_max", c_uint32),
        ("n_rs_seq", c_uint32),
        ("n_outputs_max", c_uint32),
        ("n_outputs_max_per_seq", c_uint32),
        ("n_threads", c_int32),
        ("n_threads_batch", c_int32),
        ("ctx_type", c_int),
        ("rope_scaling_type", c_int),
        ("pooling_type", c_int),
        ("attention_type", c_int),
        ("flash_attn_type", c_int),
        ("rope_freq_base", c_float),
        ("rope_freq_scale", c_float),
        ("yarn_ext_factor", c_float),
        ("yarn_attn_factor", c_float),
        ("yarn_beta_fast", c_float),
        ("yarn_beta_slow", c_float),
        ("yarn_orig_ctx", c_uint32),
        ("defrag_thold", c_float),
        ("cb_eval", c_void_p),
        ("cb_eval_user_data", c_void_p),
        ("type_k", c_int),
        ("type_v", c_int),
        ("abort_callback", c_void_p),
        ("abort_callback_data", c_void_p),
        ("embeddings", c_bool),
        ("offload_kqv", c_bool),
        ("no_perf", c_bool),
        ("op_offload", c_bool),
        ("swa_full", c_bool),
        ("kv_unified", c_bool),
        ("samplers", c_void_p),
        ("n_samplers", c_size_t),
        ("ctx_other", c_void_p),
    ]


class Batch(ctypes.Structure):
    _fields_ = [
        ("n_tokens", c_int32),
        ("token", POINTER(c_int32)),
        ("embd", POINTER(c_float)),
        ("pos", POINTER(c_int32)),
        ("n_seq_id", POINTER(c_int32)),
        ("seq_id", POINTER(POINTER(c_int32))),
        ("logits", POINTER(c_int8)),
    ]


LOG_CALLBACK = ctypes.CFUNCTYPE(None, c_int, c_char_p, c_void_p)

# name -> (result, arguments). Looked up in libllama first, then in the ggml libraries.
SIGNATURES = {
    "llama_log_set": (None, [LOG_CALLBACK, c_void_p]),
    "llama_backend_init": (None, []),
    "llama_model_default_params": (ModelParams, []),
    "llama_context_default_params": (ContextParams, []),
    "llama_model_load_from_file": (c_void_p, [c_char_p, ModelParams]),
    "llama_model_free": (None, [c_void_p]),
    "llama_init_from_model": (c_void_p, [c_void_p, ContextParams]),
    "llama_free": (None, [c_void_p]),
    "llama_model_get_vocab": (c_void_p, [c_void_p]),
    "llama_model_meta_val_str": (c_int32, [c_void_p, c_char_p, c_char_p, c_size_t]),
    "llama_model_chat_template": (c_char_p, [c_void_p, c_char_p]),
    "llama_model_size": (c_uint64, [c_void_p]),
    "llama_vocab_n_tokens": (c_int32, [c_void_p]),
    "llama_vocab_pad": (c_int32, [c_void_p]),
    "llama_vocab_eos": (c_int32, [c_void_p]),
    "llama_vocab_bos": (c_int32, [c_void_p]),
    "llama_tokenize": (
        c_int32,
        [c_void_p, c_char_p, c_int32, POINTER(c_int32), c_int32, c_bool, c_bool],
    ),
    "llama_token_to_piece": (c_int32, [c_void_p, c_int32, c_char_p, c_int32, c_int32, c_bool]),
    "llama_n_ctx": (c_uint32, [c_void_p]),
    "llama_n_batch": (c_uint32, [c_void_p]),
    "llama_n_seq_max": (c_uint32, [c_void_p]),
    "llama_get_memory": (c_void_p, [c_void_p]),
    "llama_memory_clear": (None, [c_void_p, c_bool]),
    "llama_memory_seq_cp": (None, [c_void_p, c_int32, c_int32, c_int32, c_int32]),
    "llama_memory_seq_rm": (c_bool, [c_void_p, c_int32, c_int32, c_int32]),
    # Whole-sequence state serialization: the branching path for models whose memory
    # (hybrid linear attention) cannot be copied between sequences.
    "llama_state_seq_get_size": (c_size_t, [c_void_p, c_int32]),
    "llama_state_seq_get_data": (c_size_t, [c_void_p, POINTER(c_uint8), c_size_t, c_int32]),
    "llama_state_seq_set_data": (c_size_t, [c_void_p, POINTER(c_uint8), c_size_t, c_int32]),
    "llama_decode": (c_int32, [c_void_p, Batch]),
    "llama_synchronize": (None, [c_void_p]),
    "llama_get_logits_ith": (POINTER(c_float), [c_void_p, c_int32]),
    "ggml_backend_load_all_from_path": (None, [c_char_p]),
    "ggml_backend_dev_count": (c_size_t, []),
    "ggml_backend_dev_get": (c_void_p, [c_size_t]),
    "ggml_backend_dev_name": (c_char_p, [c_void_p]),
    "ggml_backend_dev_description": (c_char_p, [c_void_p]),
    "ggml_backend_dev_memory": (None, [c_void_p, POINTER(c_size_t), POINTER(c_size_t)]),
    "ggml_backend_dev_type": (c_int, [c_void_p]),
    "ggml_backend_dev_backend_reg": (c_void_p, [c_void_p]),
    "ggml_backend_reg_name": (c_char_p, [c_void_p]),
}


@dataclass(frozen=True)
class Device:
    handle: int
    name: str  # e.g. CUDA0, Vulkan0, Metal
    description: str  # e.g. NVIDIA GeForce RTX 4050 Laptop GPU
    kind: str  # cpu | gpu | igpu | accel | meta
    backend: str  # ggml registry name: CUDA, Vulkan, Metal, ROCm, SYCL, CPU
    total_bytes: int

    def public(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "backend": self.backend,
            "total_bytes": self.total_bytes,
        }


def _shared(directory: Path, stem: str) -> Path | None:
    """`ggml-base` -> ggml-base.dll | libggml-base.dylib | libggml-base.so in `directory`."""
    if sys.platform == "win32":
        names = [f"{stem}.dll"]
    elif sys.platform == "darwin":
        names = [f"lib{stem}.dylib"]
    else:
        names = [f"lib{stem}.so"]
    return next((directory / n for n in names if (directory / n).exists()), None)


class Library:
    """The loaded runtime: libllama plus the ggml libraries and compute backends beside it."""

    _loaded: ClassVar[dict[Path, "Library"]] = {}

    def __init__(self, directory: Path):
        self.directory = Path(directory).resolve()
        if llama_release.find_library(self.directory) is None:
            raise ValueError(f"{llama_release.library_name()} not found in {self.directory}")
        self._handles = self._open()
        for name, (result, arguments) in SIGNATURES.items():
            function = next((getattr(h, name) for h in self._handles if hasattr(h, name)), None)
            if function is None:
                raise ValueError(
                    f"{self.directory}: symbol {name} is missing; the runtime must be llama.cpp "
                    f"{llama_release.RELEASE} ({llama_release.COMMIT[:7]})"
                )
            function.restype, function.argtypes = result, arguments
            setattr(self, name, function)
        verbose = os.environ.get(LOG_ENV) == "1"

        def log(level, text, _):
            # Warnings and errors only; level 5 continues a line that was probably dropped.
            # The full-size window cache is our own choice (see Session.load), not news.
            if verbose or (
                level in (LOG_LEVEL_WARN, LOG_LEVEL_ERROR) and b"full-size SWA cache" not in text
            ):
                sys.stderr.write(text.decode("utf-8", errors="replace"))

        self._log = LOG_CALLBACK(log)  # referenced for the life of the library
        self.llama_log_set(self._log, None)
        # Release builds ship every compute backend as a plug-in next to libllama.
        self.ggml_backend_load_all_from_path(str(self.directory).encode())
        self.llama_backend_init()

    @classmethod
    def open(cls, directory: Path | None = None) -> "Library":
        """One instance per directory and process: backends register globally in ggml."""
        directory = Path(directory or llama_release.locate()).resolve()
        if directory not in cls._loaded:
            cls._loaded[directory] = cls(directory)
        return cls._loaded[directory]

    def _open(self):
        folder = str(self.directory)
        if sys.platform == "win32":
            # Dependencies of the plug-ins (CUDA runtime, OpenMP) sit in the same folder.
            os.add_dll_directory(folder)
            if folder not in os.environ.get("PATH", ""):
                os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")
        else:
            # A library already loaded satisfies later lookups by soname, which stands in for
            # LD_LIBRARY_PATH: the CUDA libraries come as a separate package in this folder.
            for pattern in ("libcudart.so*", "libcublasLt.so*", "libcublas.so*"):
                for extra in sorted(self.directory.glob(pattern))[:1]:
                    ctypes.CDLL(str(extra), mode=ctypes.RTLD_GLOBAL)
        handles = []
        for stem in ("ggml-base", "ggml", "llama"):
            path = _shared(self.directory, stem)
            if path is not None:
                handles.append(ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL))
        return handles[::-1]

    def devices(self) -> list[Device]:
        found = []
        for index in range(self.ggml_backend_dev_count()):
            handle = self.ggml_backend_dev_get(index)
            free, total = c_size_t(), c_size_t()
            self.ggml_backend_dev_memory(handle, ctypes.byref(free), ctypes.byref(total))
            registry = self.ggml_backend_dev_backend_reg(handle)
            found.append(
                Device(
                    handle,
                    self.ggml_backend_dev_name(handle).decode(),
                    self.ggml_backend_dev_description(handle).decode(),
                    DEVICE_KINDS.get(self.ggml_backend_dev_type(handle), "unknown"),
                    self.ggml_backend_reg_name(registry).decode(),
                    total.value,
                )
            )
        return found

    def free_bytes(self, device: Device) -> int:
        free, total = c_size_t(), c_size_t()
        self.ggml_backend_dev_memory(device.handle, ctypes.byref(free), ctypes.byref(total))
        return free.value


def choose_device(devices: list[Device], wanted: str) -> Device | None:
    """The device that runs the whole model, or None for the CPU.

    `auto` prefers a discrete GPU, then an integrated one, then the CPU. Anything else is a
    request: `gpu` for any GPU, or text matched against backend, name and description
    (`cuda`, `vulkan`, `metal`, `Vulkan1`, `radeon`). A request that cannot be met raises.
    """
    gpus = sorted(
        (d for d in devices if d.kind in ("gpu", "igpu")),
        key=lambda d: (d.kind != "gpu", -d.total_bytes),
    )
    if wanted == "cpu":
        return None
    if wanted == "auto":
        return gpus[0] if gpus else None
    if wanted != "gpu":
        needle = wanted.lower()
        gpus = [
            d
            for d in gpus
            if needle in (d.backend.lower(), d.name.lower()) or needle in d.description.lower()
        ]
    if not gpus:
        seen = ", ".join(f"{d.name} ({d.description})" for d in devices) or "none"
        raise ValueError(
            f"--device {wanted}: no such GPU in this llama.cpp runtime. Devices: {seen}. "
            "Install another runtime with `jev download --only runtime --runtime ...`."
        )
    return gpus[0]


class Session:
    """One model and one context. Sequence 0 holds the shared prefix, the others its branches."""

    def __init__(self, library, model, context, device, n_ctx, n_batch, n_seq_max, idle_free):
        self.library = library
        self.idle_free = idle_free  # free device memory before the model was loaded
        self.model = model
        self.context = context
        self.device = device
        self.n_ctx = n_ctx
        self.n_batch = n_batch
        self.n_seq_max = n_seq_max
        self.vocab = library.llama_model_get_vocab(model)
        self.memory = library.llama_get_memory(context)

    @classmethod
    def load(
        cls,
        gguf: Path,
        *,
        directory: Path | None = None,
        device: str = "auto",
        n_ctx: int = 16384,
        n_batch: int = 2048,
        n_ubatch: int = 512,
        n_seq_max: int = 5,
        threads: int | None = None,
        gpu_layers: int | None = None,
    ) -> "Session":
        library = Library.open(directory)
        chosen = choose_device(library.devices(), device)
        idle_free = library.free_bytes(chosen) if chosen else None
        model_params = library.llama_model_default_params()
        # A NULL-terminated device list; empty means CPU only. One device, never a split:
        # a second GPU or an integrated one would otherwise receive part of the layers.
        targets = (c_void_p * 2)(chosen.handle if chosen else None, None)
        model_params.devices = targets
        model_params.split_mode = SPLIT_MODE_NONE
        # Every layer on the device unless a count is given: a model larger than the device
        # memory can keep its last layers on the CPU, slower but scorable.
        model_params.n_gpu_layers = (GPU_LAYERS if gpu_layers is None else gpu_layers) if chosen else 0
        model = library.llama_model_load_from_file(str(gguf).encode(), model_params)
        if not model:
            raise ValueError(f"llama.cpp cannot load {gguf}")
        params = library.llama_context_default_params()
        params.n_ctx = n_ctx
        params.n_batch = min(n_batch, n_ctx)
        params.n_ubatch = min(n_ubatch, params.n_batch)
        params.n_seq_max = n_seq_max
        # One buffer shared by all sequences: branching the prefix then shares its cells
        # instead of copying them, and the context is a budget rather than a per-branch slice.
        params.kv_unified = True
        # Sliding-window layers keep every position too. With the compact window cache a cell
        # held by several sequences is never recycled, and after a long prefix the branches
        # find no free cell (llama_decode returns 1). Costs memory, not correctness.
        params.swa_full = True
        # Flash attention: measured -20% on short prompts and -4% on long ones on the CPU
        # (Core Ultra 7 255H, 16 threads); identical answers.
        params.flash_attn_type = FLASH_ATTN_ENABLED
        # Logits are read at one position per sequence; the default reserves n_batch rows of
        # the whole vocabulary.
        params.n_outputs_max = n_seq_max
        params.offload_kqv = chosen is not None
        params.no_perf = True
        if threads:
            params.n_threads = params.n_threads_batch = threads
        context = library.llama_init_from_model(model, params)
        if not context:
            library.llama_model_free(model)
            raise ValueError(
                f"llama.cpp cannot create a {n_ctx}-token context; lower --ctx or --batch-size"
            )
        return cls(
            library,
            model,
            context,
            chosen,
            int(library.llama_n_ctx(context)),
            int(library.llama_n_batch(context)),
            int(library.llama_n_seq_max(context)),
            idle_free,
        )

    def close(self):
        if self.context:
            self.library.llama_free(self.context)
            self.library.llama_model_free(self.model)
            self.context = self.model = self.vocab = self.memory = None

    # --- text -----------------------------------------------------------------------------

    def tokenize(self, text: str, add_special: bool = False) -> list[int]:
        raw = text.encode("utf-8")
        capacity = len(raw) + 8  # a token covers at least one byte
        buffer = (c_int32 * capacity)()
        # parse_special: control tokens written in the template text become their own ids.
        count = self.library.llama_tokenize(
            self.vocab, raw, len(raw), buffer, capacity, add_special, True
        )
        if count < 0:
            raise ValueError("llama_tokenize: buffer too small")
        return buffer[:count]

    def piece(self, token: int) -> str:
        buffer = ctypes.create_string_buffer(256)
        count = self.library.llama_token_to_piece(self.vocab, token, buffer, 256, 0, True)
        if count < 0:
            raise ValueError("llama_token_to_piece: buffer too small")
        return buffer.raw[:count].decode("utf-8", errors="replace")

    def meta(self, key: str) -> str | None:
        buffer = ctypes.create_string_buffer(1024)
        count = self.library.llama_model_meta_val_str(self.model, key.encode(), buffer, 1024)
        return buffer.value.decode("utf-8") if count >= 0 else None

    def chat_template(self) -> str | None:
        template = self.library.llama_model_chat_template(self.model, None)
        return template.decode("utf-8") if template else None

    @property
    def pad_token(self) -> int | None:
        token = self.library.llama_vocab_pad(self.vocab)
        return token if token >= 0 else None

    @property
    def bos_token(self) -> int | None:
        token = self.library.llama_vocab_bos(self.vocab)
        return token if token >= 0 else None

    @property
    def eos_token(self) -> int | None:
        token = self.library.llama_vocab_eos(self.vocab)
        return token if token >= 0 else None

    @property
    def vocab_size(self) -> int:
        return self.library.llama_vocab_n_tokens(self.vocab)

    # --- compute --------------------------------------------------------------------------

    def decode(self, tokens, positions, sequences, outputs=()) -> None:
        """One forward pass over a flat batch; logits are produced only at `outputs` indices."""
        count = len(tokens)
        if not 0 < count <= self.n_batch:
            raise ValueError(f"Batch of {count} tokens; the limit is {self.n_batch}")
        ids = (c_int32 * count)(*sequences)
        width = ctypes.sizeof(c_int32)
        base = ctypes.addressof(ids)
        flags = (c_int8 * count)()
        for index in outputs:
            flags[index] = 1
        batch = Batch(
            count,
            (c_int32 * count)(*tokens),
            None,
            (c_int32 * count)(*positions),
            (c_int32 * count)(*([1] * count)),
            (POINTER(c_int32) * count)(
                *(ctypes.cast(base + width * i, POINTER(c_int32)) for i in range(count))
            ),
            flags,
        )
        status = self.library.llama_decode(self.context, batch)
        if status != 0:
            reason = "the context is full" if status == 1 else "compute error"
            raise ValueError(f"llama_decode returned {status}: {reason}")

    def logits(self, index: int, slots: list[int]) -> list[float]:
        """Logits of the given vocabulary rows at batch position `index`."""
        row = self.library.llama_get_logits_ith(self.context, index)
        if not row:
            raise ValueError(f"No logits were produced at batch position {index}")
        return [float(row[slot]) for slot in slots]

    def logits_all(self, index: int) -> list[float]:
        """The whole vocabulary row at batch position `index` (diagnostics, not scoring)."""
        row = self.library.llama_get_logits_ith(self.context, index)
        if not row:
            raise ValueError(f"No logits were produced at batch position {index}")
        return row[: self.vocab_size]

    def clear(self) -> None:
        self.library.llama_memory_clear(self.memory, True)

    def branch(self, source: int, target: int) -> None:
        """Make `target` reference the cells of `source` (sequence copy; attention-only models)."""
        self.library.llama_memory_seq_cp(self.memory, source, target, -1, -1)

    def drop(self, sequence: int) -> None:
        self.library.llama_memory_seq_rm(self.memory, sequence, -1, -1)

    def save_sequence(self, sequence: int = 0):
        """Serialize the whole state of one sequence; the branching path for hybrid models."""
        size = self.library.llama_state_seq_get_size(self.context, sequence)
        if size <= 0:
            raise ValueError(f"llama.cpp reports an empty state for sequence {sequence}")
        buffer = (c_uint8 * size)()
        written = self.library.llama_state_seq_get_data(self.context, buffer, size, sequence)
        if written != size:
            raise ValueError(f"llama.cpp wrote {written} of {size} state bytes")
        return buffer

    def restore_sequence(self, state, sequence: int = 0) -> None:
        """Drop whatever `sequence` holds and put a saved state back in its place."""
        self.library.llama_memory_seq_rm(self.memory, sequence, -1, -1)
        read = self.library.llama_state_seq_set_data(self.context, state, len(state), sequence)
        if read == 0:
            raise ValueError(f"llama.cpp could not restore the saved state of sequence {sequence}")

    def synchronize(self) -> None:
        self.library.llama_synchronize(self.context)

    def free_bytes(self) -> int | None:
        return self.library.free_bytes(self.device) if self.device else None
