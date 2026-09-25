"""Find the weights and load the scoring backend."""

from pathlib import Path

from . import models
from .runtime import llama_release
from .runtime.llama_cpp import Library

DEVICES = ("auto", "gpu", "cpu", "cuda", "vulkan", "metal", "rocm", "sycl")


def load_backend(
    model=models.DEFAULT_MODEL,
    quant=models.DEFAULT_QUANT,
    gguf=None,
    device="auto",
    ctx=8192,
    batch_size=4,
    threads=None,
    branch="auto",
    gpu_layers=None,
):
    from .engine.backend import LlamaBackend

    if gguf is not None:
        path = Path(gguf)
        if path.suffix.lower() != ".gguf":
            raise ValueError(f"--gguf expects a .gguf file, not {path}")
    else:
        if model not in models.MODELS:
            raise ValueError(f"--model must be one of: {', '.join(models.MODELS)}")
        if quant not in models.MODELS[model].files:
            raise ValueError(
                f"{model} has no {quant} file; available: {', '.join(models.MODELS[model].files)}"
            )
        path = models.MODELS[model].path(quant)
    if not path.is_file():
        raise ValueError(
            f"GGUF file not found at {path}. Run `jev download --model {model} --quant {quant}`."
        )
    return LlamaBackend.load(
        path,
        device=device,
        ctx=ctx,
        batch_size=batch_size,
        threads=threads,
        branch=branch,
        gpu_layers=gpu_layers,
    )


def describe() -> dict:
    """What `jev devices` prints: the installed runtimes and what the best one sees."""
    installed = llama_release.installed()
    report = {
        "llama_cpp_release": llama_release.RELEASE,
        "installed_runtimes": installed,
        "runtime_dir": None,
        "devices": [],
    }
    try:
        directory = llama_release.locate()
    except ValueError as error:
        report["error"] = str(error)
        return report
    library = Library.open(directory)
    report["runtime_dir"] = str(directory)
    report["devices"] = [d.public() for d in library.devices()]
    return report
