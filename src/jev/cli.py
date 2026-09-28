"""`jev` command line: download the runtime and weights, list devices, decide on a request,
serve the Jev-compatible HTTP API."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import models
from .engine.backend import BRANCH_STRATEGIES
from .loader import DEVICES
from .runtime.llama_release import ACCELERATORS

API_KEY_ENV = "JEV_API_KEY"  # when set, `jev serve` requires `Authorization: Bearer <key>`


def write_json(value, destination):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Results are create-only; never silently overwrite evidence.
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)
    else:
        print(text, end="")


def progress(name, done, total):
    """One carriage-returned line per file; silent when stderr is not a terminal."""
    if sys.stderr.isatty():
        share = f"{100 * done / total:5.1f}%" if total else f"{done >> 20} MiB"
        sys.stderr.write(f"\r{name}: {share}")
        if total and done >= total:
            sys.stderr.write("\n")


def add_model_options(parser):
    parser.add_argument("--model", choices=tuple(models.MODELS), default=models.DEFAULT_MODEL)
    parser.add_argument("--quant", choices=models.QUANTS, default=models.DEFAULT_QUANT)
    parser.add_argument("--gguf", type=Path, help="Any GGUF file; overrides --model/--quant")
    parser.add_argument(
        "--device",
        choices=DEVICES,
        default="auto",
        help="auto = best GPU of the installed runtime, else CPU; a family name requires it",
    )
    parser.add_argument("--threads", type=int, help="CPU threads")
    parser.add_argument(
        "--gpu-layers", type=int, help="Layers kept on the GPU (default: all); the rest run on the CPU"
    )
    parser.add_argument("--batch-size", type=int, default=4, help="Questions per micro-batch")
    parser.add_argument(
        "--ctx",
        type=int,
        default=8192,
        help="Context limit in tokens per question (state + question); longer inputs are rejected",
    )
    parser.add_argument(
        "--branch",
        choices=BRANCH_STRATEGIES,
        default="auto",
        help="How questions branch from the shared state: sequence copy or state restore",
    )
    parser.add_argument("--calibration", type=Path)
    parser.add_argument(
        "--binary",
        action="store_true",
        help="Binary model: answers yes/no (noul) questions only, as 1 or 0; other types are refused",
    )


def main():
    parser = argparse.ArgumentParser(description="Jev — local typed decisions")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser(
        "download", help="Download the pinned llama.cpp runtime for this machine and the weights"
    )
    download.add_argument("--model", choices=tuple(models.MODELS), default=models.DEFAULT_MODEL)
    download.add_argument("--quant", choices=models.QUANTS, default=models.DEFAULT_QUANT)
    download.add_argument(
        "--runtime",
        choices=ACCELERATORS,
        default="auto",
        help="llama.cpp build: auto = Metal on a Mac, CUDA with an NVIDIA driver, else Vulkan",
    )
    download.add_argument("--only", choices=("runtime", "weights"))
    download.add_argument("--destination", type=Path, help="Weights; default: under models/")
    commands.add_parser("devices", help="Show which compute backends this install can use")
    decide = commands.add_parser("decide", help="Answer the questions of one request file")
    add_model_options(decide)
    decide.add_argument(
        "input",
        type=Path,
        help="A POST /v1/systemone body, answered in the same wire format; or a native engine "
        "request (no `model` field), answered with the engine's full output",
    )
    decide.add_argument("--output")
    serve = commands.add_parser(
        "serve", help="Serve the Jev-compatible HTTP API (POST /v1/systemone, GET /v1/models)"
    )
    add_model_options(serve)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8017)
    args = parser.parse_args()
    try:
        if args.command == "download":
            if args.only != "weights":
                from .runtime.llama_release import install

                print(install(args.runtime, progress))
            if args.only != "runtime":
                print(models.download_gguf(args.model, args.quant, args.destination, progress))
            return
        if args.command == "devices":
            from .loader import describe

            write_json(describe(), None)
            return
        from .api import wire
        from .api.translate import resolve_model, served_name, to_native, to_wire
        from .engine.calibration import Calibration
        from .engine.engine import Engine
        from .engine.schema import Request
        from .loader import load_backend

        # Validate the request before loading gigabytes of weights.
        if args.command == "decide":
            text = args.input.read_text(encoding="utf-8")
            # The wire body always has a `model` field and the native request forbids one, so the
            # field tells them apart; a wire body is translated exactly as the server does it.
            wire_request = None
            body = json.loads(text)
            if isinstance(body, dict) and "model" in body:
                wire_request = wire.SystemOneRequest.model_validate_json(text)
                request, keys = to_native(wire_request)
            else:
                request = Request.model_validate_json(text)
        backend = load_backend(
            model=args.model,
            quant=args.quant,
            gguf=args.gguf,
            device=args.device,
            ctx=args.ctx,
            batch_size=args.batch_size,
            threads=args.threads,
            branch=args.branch,
            gpu_layers=args.gpu_layers,
        )
        calibration = Calibration.from_file(args.calibration) if args.calibration else None
        # A GGUF that names a binary prompt version is a binary model: no flag needed.
        binary = args.binary or bool(backend.metadata.get("binary_prompt_version"))
        engine = Engine(backend, ctx=args.ctx, calibration=calibration, binary=binary)
        if args.command == "serve":
            import uvicorn

            from .api.app import create_app

            api_key = os.environ.get(API_KEY_ENV) or None
            print(
                f"jev: {served_name(backend.metadata)} on http://{args.host}:{args.port}"
                f" ({'Bearer auth' if api_key else 'no auth'})",
                file=sys.stderr,
            )
            uvicorn.run(create_app(engine, api_key=api_key), host=args.host, port=args.port)
            return
        if wire_request is None:
            write_json(engine.decide(request), args.output)
            return
        # Checked before inference, as the server does: any `jev-*` alias or the served name.
        model = resolve_model(wire_request.model, served_name(backend.metadata))
        write_json(to_wire(wire_request, engine.decide(request), keys, model), args.output)
    except (ValueError, OSError, ImportError) as error:
        print(f"jev: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
