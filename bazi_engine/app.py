"""
app.py — FastAPI application factory.

Creates the FastAPI instance, registers global exception handlers,
and mounts all routers. No business logic lives here.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import math

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .exc import BaziEngineError, EphemerisUnavailableError
from . import __version__
from .routers import info, bazi, western, fusion, validate, chart, webhooks, transit


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logging.getLogger("uvicorn").info(f"FuFirE starting: {__version__}")
    yield


app = FastAPI(
    title="FuFirE — Fusion Firmament Engine",
    description="FuFirE: Deterministic astronomical calculation engine for BaZi (Chinese Astrology) and Western Astrology with Wu-Xing fusion.",
    version=__version__,
    lifespan=lifespan,
)


# ── Global exception handlers ─────────────────────────────────────────────────

@app.exception_handler(BaziEngineError)
async def bazi_engine_error_handler(request: Request, exc: BaziEngineError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


@app.exception_handler(EphemerisUnavailableError)
async def ephemeris_error_handler(request: Request, exc: EphemerisUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Override default handler to sanitize values that stdlib json cannot
    serialize (NaN/Inf floats, Exception objects in Pydantic error ctx)."""
    import json as _json

    def _sanitize(obj, *, _depth: int = 0, _max_depth: int = 20):  # type: ignore[no-untyped-def]
        if _depth >= _max_depth:
            return "<nested>"
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if isinstance(obj, dict):
            return {k: _sanitize(v, _depth=_depth + 1) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_sanitize(v, _depth=_depth + 1) for v in obj]
        # Catch non-serializable objects (e.g. ValueError in Pydantic ctx)
        try:
            _json.dumps(obj)
        except (TypeError, ValueError):
            return str(obj)
        return obj

    return JSONResponse(
        status_code=422,
        content=_sanitize({"detail": exc.errors()}),
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": "ephemeris_unavailable", "message": str(exc), "detail": {}},
    )


# ── Routers ──────────────────────────────────────────────────────────────────

app.include_router(info.router)
app.include_router(validate.router)
app.include_router(bazi.router)
app.include_router(western.router)
app.include_router(fusion.router)
app.include_router(chart.router)
app.include_router(webhooks.router)
app.include_router(transit.router)


# ── OpenAPI customization ────────────────────────────────────────────────────

def _custom_openapi():  # type: ignore[no-untyped-def]
    """Patch the auto-generated OpenAPI to reference the contract schemas
    for /validate (ValidateRequest / ValidateResponse) instead of generic
    ``object``. No runtime behavior change — documentation only."""
    if app.openapi_schema:
        return app.openapi_schema

    import json
    from pathlib import Path
    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Load Draft-07 schemas, hoist definitions to components/schemas,
    # and rewrite $ref paths from #/definitions/X to #/components/schemas/X
    # so that openapi-generator and other tooling can resolve them.
    spec_dir = Path(__file__).resolve().parent.parent / "spec" / "schemas"
    all_schemas = schema.setdefault("components", {}).setdefault("schemas", {})

    def _rewrite_refs(obj: Any) -> Any:
        """Recursively rewrite #/definitions/X → #/components/schemas/X."""
        if isinstance(obj, dict):
            return {
                k: (v.replace("#/definitions/", "#/components/schemas/")
                    if k == "$ref" and isinstance(v, str)
                    else _rewrite_refs(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_rewrite_refs(item) for item in obj]
        return obj

    for name in ("ValidateRequest", "ValidateResponse"):
        path = spec_dir / f"{name}.schema.json"
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw.pop("$schema", None)
            raw.pop("$id", None)
            # Hoist definitions to top-level components/schemas
            for def_name, def_schema in raw.pop("definitions", {}).items():
                if def_name not in all_schemas:
                    all_schemas[def_name] = _rewrite_refs(def_schema)
            all_schemas[name] = _rewrite_refs(raw)

    # Patch /validate path to reference the real schemas
    validate_path = schema.get("paths", {}).get("/validate", {}).get("post")
    if validate_path:
        validate_path["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ValidateRequest"}
                }
            },
        }
        validate_path["responses"] = {
            "200": {
                "description": "Validation result",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ValidateResponse"}
                    }
                },
            },
            "422": {
                "description": "Request schema violation",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                    }
                },
            },
            "500": {
                "description": "Internal validation error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                    }
                },
            },
        }

    # Standard error envelope used by exception handlers
    schema.setdefault("components", {}).setdefault("schemas", {})["ErrorEnvelope"] = {
        "type": "object",
        "properties": {
            "error": {"type": "string"},
            "message": {"type": "string"},
            "detail": {"type": "object"},
        },
        "required": ["error", "message"],
    }

    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi  # type: ignore[method-assign]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
