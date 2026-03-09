"""
routers/transit.py — Transit API endpoints.

GET /transit/now — Current planetary positions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..transit import compute_transit_now

router = APIRouter(prefix="/transit", tags=["Transit"])


# ── Response models ──────────────────────────────────────────────────────────

class PlanetPosition(BaseModel):
    longitude: float
    sector: int
    sign: str
    speed: float


class TransitNowResponse(BaseModel):
    computed_at: str
    planets: Dict[str, PlanetPosition]
    sector_intensity: List[float]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/now", response_model=TransitNowResponse)
def transit_now(
    datetime_param: Optional[str] = Query(
        None,
        alias="datetime",
        description="Optional UTC datetime in ISO format. Default: now.",
    ),
) -> Dict[str, Any]:
    """Current planetary positions from Swiss Ephemeris."""
    dt_utc = None
    if datetime_param:
        dt_utc = datetime.fromisoformat(
            datetime_param.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    return compute_transit_now(dt_utc=dt_utc)
