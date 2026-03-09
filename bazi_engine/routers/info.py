"""
routers/info.py — Informational and utility endpoints.

Endpoints: GET /, /health, /build, /api (zodiac lookup), /info/wuxing-mapping
"""
from __future__ import annotations

import os
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..exc import BaziEngineError
from ..fusion import PLANET_TO_WUXING, WUXING_ORDER
from ..time_utils import resolve_local_iso
from ..western import compute_western_chart
from .shared import ZODIAC_SIGNS_DE

from .. import __version__ as _ENGINE_VERSION

router = APIRouter(tags=["Info"])

_BUILD_VERSION = os.environ.get("BUILD_VERSION", _ENGINE_VERSION)


# ── Response models ──────────────────────────────────────────────────────────

class RootResponse(BaseModel):
    status: str
    service: str
    version: str


class HealthResponse(BaseModel):
    status: str
    engine: str = "FuFirE"
    version: str = ""


class BuildResponse(BaseModel):
    version: str
    railway_commit_sha: Optional[str] = None
    railway_deploy_id: Optional[str] = None
    fly_alloc_id: Optional[str] = None
    fly_region: Optional[str] = None


class ApiResponse(BaseModel):
    sonne: str
    input: Dict[str, Any]


class WuxingMappingResponse(BaseModel):
    mapping: Dict[str, Any]
    order: list
    description: Dict[str, str]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_metadata() -> Dict[str, str]:
    meta: Dict[str, str] = {"version": _BUILD_VERSION}
    if os.environ.get("EXPOSE_BUILD_METADATA"):
        meta["railway_commit_sha"] = os.environ.get("RAILWAY_GIT_COMMIT_SHA", "")
        meta["railway_deploy_id"] = os.environ.get("RAILWAY_DEPLOYMENT_ID", "")
        meta["fly_alloc_id"] = os.environ.get("FLY_ALLOC_ID", "")
        meta["fly_region"] = os.environ.get("FLY_REGION", "")
    return meta


@router.get("/", response_model=RootResponse)
def read_root() -> Dict[str, Any]:
    return {"status": "ok", "service": "fufire", **_build_metadata()}


@router.get("/health", response_model=HealthResponse)
def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "engine": "FuFirE", "version": _ENGINE_VERSION}


@router.get("/build", response_model=BuildResponse)
def build_info() -> Dict[str, str]:
    return _build_metadata()


@router.get("/api", response_model=ApiResponse)
def api_endpoint(
    datum: str = Query(..., description="Datum im Format YYYY-MM-DD"),
    zeit: str = Query(..., description="Zeit im Format HH:MM[:SS]"),
    ort: Optional[str] = Query(None, description="Ort als 'lat,lon'"),
    tz: str = Query("Europe/Berlin", description="Timezone name"),
    lon: float = Query(13.4050, description="Longitude in degrees"),
    lat: float = Query(52.52, description="Latitude in degrees"),
    ambiguousTime: Literal["earlier", "later"] = Query("earlier"),
    nonexistentTime: Literal["error", "shift_forward"] = Query("error"),
) -> Dict[str, Any]:
    from datetime import timezone as tz_mod
    try:
        if ort:
            if "," in ort:
                parts = [p.strip() for p in ort.split(",", maxsplit=1)]
                if len(parts) == 2:
                    lat = float(parts[0])
                    lon = float(parts[1])
            else:
                raise ValueError("Ort muss als 'lat,lon' angegeben werden, wenn gesetzt.")

        dt, _ = resolve_local_iso(
            f"{datum}T{zeit}", tz,
            ambiguous=ambiguousTime, nonexistent=nonexistentTime,
        )
        dt_utc = dt.astimezone(tz_mod.utc)
        chart = compute_western_chart(dt_utc, lat, lon)
        sun = chart.get("bodies", {}).get("Sun")
        if not sun or "zodiac_sign" not in sun:
            raise ValueError("Sonnenposition konnte nicht berechnet werden.")
        sign_index = int(sun["zodiac_sign"])
        sign_name = ZODIAC_SIGNS_DE[sign_index]
        return {"sonne": sign_name, "input": {"datum": datum, "zeit": zeit, "ort": ort, "tz": tz, "lat": lat, "lon": lon}}
    except BaziEngineError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/info/wuxing-mapping", response_model=WuxingMappingResponse)
def get_wuxing_mapping() -> Dict[str, Any]:
    return {
        "mapping": PLANET_TO_WUXING,
        "order": WUXING_ORDER,
        "description": {
            "PLANET_TO_WUXING": "Western planet to Chinese element mapping",
            "WUXING_ORDER": "Wu Xing cycle order: Holz -> Feuer -> Erde -> Metall -> Wasser",
        },
    }
