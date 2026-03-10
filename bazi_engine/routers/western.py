"""
routers/western.py — POST /calculate/western
"""
from __future__ import annotations

from datetime import timezone
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..exc import BaziEngineError
from ..provenance import build_provenance
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


class WesternBodyResponse(BaseModel):
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    speed: Optional[float] = None
    distance: Optional[float] = None
    zodiac_sign: Optional[int] = None
    degree_in_sign: Optional[float] = None
    is_retrograde: bool = False


class ProvenanceResponse(BaseModel):
    engine_version: str
    parameter_set_id: str
    ruleset_id: str
    ephemeris_id: str
    tzdb_version_id: str
    house_system: str
    zodiac_mode: str
    computation_timestamp: str


class WesternResponse(BaseModel):
    jd_ut: float
    bodies: Dict[str, WesternBodyResponse]
    houses: Optional[Dict[str, float]] = None
    angles: Optional[Dict[str, float]] = None
    provenance: ProvenanceResponse


@router.post("/western", response_model=WesternResponse)
def calculate_western_endpoint(req: WesternRequest) -> Dict[str, Any]:
    try:
        dt_local, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        dt_utc = dt_local.astimezone(timezone.utc)
        result = compute_western_chart(dt_utc, req.lat, req.lon)
        result["provenance"] = build_provenance()
        return result
    except BaziEngineError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
