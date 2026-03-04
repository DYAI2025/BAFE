"""
app.py — FastAPI application factory.

Creates the FastAPI instance, registers global exception handlers,
and mounts all routers. No business logic lives here.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .exc import BaziEngineError, EphemerisUnavailableError
from .routers import info, bazi, western, fusion, validate, chart, webhooks

_BUILD_VERSION = "1.0.0-rc1-20260220"


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logging.getLogger("uvicorn").info(f"BAFE starting: {_BUILD_VERSION}")
    yield


app = FastAPI(
    title="BaZi Engine v2 API",
    description="API for BaZi (Chinese Astrology) and Basic Western Astrology calculations.",
    version=_BUILD_VERSION,
    lifespan=lifespan,
)


# ── Global exception handlers ─────────────────────────────────────────────────

@app.exception_handler(BaziEngineError)
async def bazi_engine_error_handler(request: Request, exc: BaziEngineError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


@app.exception_handler(EphemerisUnavailableError)
async def ephemeris_error_handler(request: Request, exc: EphemerisUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content=exc.to_dict())


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
