"""
routers/transit.py — Transit API endpoints.

GET  /transit/now        — Current planetary positions.
GET  /transit/timeline   — Multi-day transit forecast.
POST /transit/state      — Personalized transit state.
POST /transit/narrative  — Text generation from transit state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ..transit import compute_transit_now, compute_transit_state, compute_transit_timeline
from ..narrative import generate_narrative

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


class RingSectors(BaseModel):
    sectors: List[float]


class TransitContribution(BaseModel):
    sectors: List[float]
    transit_intensity: float


class Delta(BaseModel):
    vs_previous: Optional[Dict[str, Any]] = None
    vs_30day_avg: Optional[Dict[str, Any]] = None


class TransitStateResponse(BaseModel):
    schema_: str = Field(..., alias="schema")
    generated_at: str
    ring: RingSectors
    transit_contribution: TransitContribution
    delta: Delta
    events: List[Dict[str, Any]]

    model_config = {"populate_by_name": True}


class TimelineDayResponse(BaseModel):
    date: str
    planets: Dict[str, PlanetPosition]
    sector_intensity: List[float]


class TimelineResponse(BaseModel):
    days: List[TimelineDayResponse]


class NarrativeResponse(BaseModel):
    headline: str
    body: str
    advice: str
    pushworthy: bool
    push_text: Optional[str] = None


# ── Request models ───────────────────────────────────────────────────────────

class TransitStateRequest(BaseModel):
    soulprint_sectors: List[float] = Field(..., min_length=12, max_length=12)
    quiz_sectors: List[float] = Field(..., min_length=12, max_length=12)


class NarrativeRequest(BaseModel):
    transit_state: Dict[str, Any]


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


@router.post("/state", response_model=TransitStateResponse)
def transit_state(body: TransitStateRequest) -> Dict[str, Any]:
    """Personalized transit state combining current transits with user profile."""
    return compute_transit_state(
        soulprint_sectors=body.soulprint_sectors,
        quiz_sectors=body.quiz_sectors,
    )


@router.get("/timeline", response_model=TimelineResponse)
def transit_timeline(
    days: int = Query(7, ge=1, le=30, description="Number of days to forecast (1-30)."),
) -> Dict[str, Any]:
    """Multi-day transit forecast. Cached 24h (ADR-1)."""
    return compute_transit_timeline(days=days)


@router.post("/narrative", response_model=NarrativeResponse)
def transit_narrative(body: NarrativeRequest) -> Dict[str, Any]:
    """Generate narrative text from transit state. Template-based, <50ms (ADR-3)."""
    return generate_narrative(body.transit_state)
