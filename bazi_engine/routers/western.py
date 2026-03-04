"""
routers/western.py — POST /calculate/western
"""
from __future__ import annotations

from datetime import timezone
from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..exc import BaziEngineError
from ..time_utils import resolve_local_iso, AmbiguousTimeChoice, NonexistentTimePolicy
from ..western import compute_western_chart

router = APIRouter(prefix="/calculate", tags=["Western Astrology"])


class WesternRequest(BaseModel):
    date: str = Field(..., description="Local ISO8601 datetime")
    tz: str = Field("Europe/Berlin", description="IANA timezone name")
    lon: float = Field(13.4050, description="Longitude in degrees")
    lat: float = Field(52.52, description="Latitude in degrees")
    ambiguousTime: AmbiguousTimeChoice = Field("earlier")
    nonexistentTime: NonexistentTimePolicy = Field("error")


@router.post("/western")
def calculate_western_endpoint(req: WesternRequest) -> Dict[str, Any]:
    try:
        dt_local, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        dt_utc = dt_local.astimezone(timezone.utc)
        return compute_western_chart(dt_utc, req.lat, req.lon)
    except BaziEngineError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
