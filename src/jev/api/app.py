"""FastAPI application: the Jev contract in front of one resident engine."""

import hmac
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from .. import __version__
from . import wire
from .translate import ALIAS_PREFIX, WireError, resolve_model, served_name, to_native, to_wire

DINO = Path(__file__).with_name("dino.html")


def create_app(engine, api_key: str | None = None) -> FastAPI:
    """One engine, one model. With `api_key`, every call except `/health` needs
    `Authorization: Bearer <api_key>`, as the hosted API does."""
    served = served_name(engine.backend.metadata)
    started = datetime.now(UTC).date().isoformat()
    app = FastAPI(
        title="Jev",
        version=__version__,
        description="Typed decisions read from a local model's logits, in the Jev wire format.",
    )

    def authorize(authorization: str | None = Header(default=None)):
        if api_key and not hmac.compare_digest(
            (authorization or "").encode(), f"Bearer {api_key}".encode()
        ):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.exception_handler(ValueError)
    def unprocessable(_: Request, error: ValueError):
        # Limits of this engine (options, context length) and of the native request, in the
        # same shape as FastAPI's own validation errors.
        if isinstance(error, ValidationError):
            detail = [
                {"loc": ["body", *item["loc"]], "msg": item["msg"], "type": item["type"]}
                for item in error.errors()
            ]
        else:
            detail = [{"loc": getattr(error, "loc", ["body"]), "msg": str(error), "type": "value_error"}]
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.post(
        "/v1/systemone",
        response_model=wire.SystemOneResponse,
        dependencies=[Depends(authorize)],
    )
    def systemone(body: wire.SystemOneRequest, response: Response):
        model = resolve_model(body.model, served)
        native, keys = to_native(body)
        result = engine.decide(native)
        timing = result["timing"]
        response.headers["Server-Timing"] = (
            f"inference;dur={1000 * timing.get('inference_seconds', 0):.1f}, "
            f"total;dur={1000 * timing.get('total_seconds', 0):.1f}"
        )
        return to_wire(body, result, keys, model)

    @app.get("/v1/models", response_model=wire.ModelMetadataList, dependencies=[Depends(authorize)])
    def models():
        return {
            "models": [
                {
                    "name": served,
                    "description": "Typed decisions read from the option logits of a local "
                    "model; no text is generated.",
                    "release_date": started,
                },
                {
                    "name": f"{ALIAS_PREFIX}latest",
                    "description": f"Compatibility alias: answered by {served} on this server, "
                    "not by TypeSafe's Jev.",
                    "release_date": started,
                },
            ]
        }

    @app.get("/health")
    def health():
        return {"status": "ready", "model": served, "engine": engine.backend.metadata}

    @app.get("/dino", response_class=HTMLResponse, include_in_schema=False)
    def dino():
        # A Chrome Dino-style demo: two yes/no questions per decision, asked by the page.
        return DINO.read_text(encoding="utf-8")

    return app


__all__ = ["WireError", "create_app"]
