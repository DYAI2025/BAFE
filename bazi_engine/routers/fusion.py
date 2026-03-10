"""
routers/fusion.py — Wu-Xing Fusion endpoints.

Endpoints:
  POST /calculate/fusion   — Wu-Xing + Western harmony analysis
  POST /calculate/wuxing   — Wu-Xing vector from planetary positions
  POST /calculate/tst      — True Solar Time calculation
"""
from __future__ import annotations

from datetime import timezone
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..bazi import compute_bazi
from ..exc import BaziEngineError
from ..provenance import build_provenance, normalize_house_system
from ..fusion import (
    compute_fusion_analysis,
    calculate_wuxing_vector_from_planets_with_ledger,
    equation_of_time,
    true_solar_time,
)
from ..time_utils import resolve_local_iso, AmbiguousTimeChoice, NonexistentTimePolicy
from ..types import BaziInput, Fold
from ..western import compute_western_chart
from .shared import format_pillar, ProvenanceResponse
from .western import HouseQuality

router = APIRouter(prefix="/calculate", tags=["Fusion / Wu-Xing"])


# ── /calculate/fusion ────────────────────────────────────────────────────────

class FusionRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")
    lat: float = Field(..., description="Latitude in degrees")
    ambiguousTime: AmbiguousTimeChoice = "earlier"
    nonexistentTime: NonexistentTimePolicy = "error"
    bazi_pillars: Optional[Dict[str, Dict[str, str]]] = Field(
        None, description="BaZi pillars (auto-computed if omitted)"
    )


class FusionResponse(BaseModel):
    input: Dict[str, Any]
    wu_xing_vectors: Dict[str, Dict[str, float]]
    harmony_index: Dict[str, Any]
    calibration: Optional[Dict[str, Any]] = None
    elemental_comparison: Dict[str, Dict[str, float]]
    cosmic_state: float
    fusion_interpretation: str
    contribution_ledger: Optional[Dict[str, Any]] = None
    house_quality: Optional[HouseQuality] = None
    provenance: ProvenanceResponse


@router.post("/fusion", response_model=FusionResponse)
def calculate_fusion_endpoint(req: FusionRequest) -> Dict[str, Any]:
    """Wu-Xing + Western harmony analysis."""
    try:
        dt_local, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        dt_utc = dt_local.astimezone(timezone.utc)
        western_chart = compute_western_chart(dt_utc, req.lat, req.lon)

        pillars = req.bazi_pillars
        if pillars is None:
            fold: Fold = 0 if req.ambiguousTime == "earlier" else 1
            inp = BaziInput(
                birth_local=dt_local.replace(tzinfo=None).isoformat(),
                timezone=req.tz,
                longitude_deg=req.lon,
                latitude_deg=req.lat,
                time_standard="CIVIL",
                day_boundary="midnight",
                strict_local_time=True,
                fold=fold,
            )
            bazi_result = compute_bazi(inp)
            pillars = {
                "year":  format_pillar(bazi_result.pillars.year),
                "month": format_pillar(bazi_result.pillars.month),
                "day":   format_pillar(bazi_result.pillars.day),
                "hour":  format_pillar(bazi_result.pillars.hour),
            }

        ascendant = western_chart.get("angles", {}).get("Ascendant")
        fusion = compute_fusion_analysis(
            birth_utc_dt=dt_utc,
            latitude=req.lat,
            longitude=req.lon,
            bazi_pillars=pillars,
            western_bodies=western_chart["bodies"],
            ascendant=ascendant,
        )
        return {
            "input": {"date": req.date, "tz": req.tz, "lon": req.lon, "lat": req.lat},
            "wu_xing_vectors":      fusion["wu_xing_vectors"],
            "harmony_index":        fusion["harmony_index"],
            "calibration":          fusion["calibration"],
            "elemental_comparison": fusion["elemental_comparison"],
            "cosmic_state":         fusion["cosmic_state"],
            "fusion_interpretation": fusion["fusion_interpretation"],
            "contribution_ledger": fusion["contribution_ledger"],
            "house_quality": western_chart.get("house_quality"),
            "provenance": build_provenance(
                house_system=normalize_house_system(western_chart.get("house_system")),
            ),
        }
    except BaziEngineError:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal calculation error")


# ── /calculate/wuxing ────────────────────────────────────────────────────────

class WxRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")
    lat: float = Field(..., description="Latitude in degrees")
    ambiguousTime: AmbiguousTimeChoice = "earlier"
    nonexistentTime: NonexistentTimePolicy = "error"


class WxResponse(BaseModel):
    input: Dict[str, Any]
    wu_xing_vector: Dict[str, float]
    dominant_element: str
    equation_of_time: float
    true_solar_time: float
    contribution_ledger: Optional[Dict[str, Any]] = None
    provenance: ProvenanceResponse


@router.post("/wuxing", response_model=WxResponse)
def calculate_wuxing_endpoint(req: WxRequest) -> Dict[str, Any]:
    """Wu-Xing element vector from western planetary positions."""
    try:
        dt, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        dt_utc = dt.astimezone(timezone.utc)
        western_chart = compute_western_chart(dt_utc, req.lat, req.lon)
        asc = western_chart.get("angles", {}).get("Ascendant")
        wx_vector, wx_ledger = calculate_wuxing_vector_from_planets_with_ledger(
            western_chart["bodies"], ascendant=asc,
        )
        wx_norm = wx_vector.normalize()
        day_of_year = dt.timetuple().tm_yday
        civil_time_hours = dt.hour + dt.minute / 60
        TST = true_solar_time(civil_time_hours, req.lon, day_of_year)
        return {
            "input": {"date": req.date, "tz": req.tz, "lon": req.lon, "lat": req.lat},
            "wu_xing_vector":  wx_norm.to_dict(),
            "dominant_element": max(wx_norm.to_dict(), key=lambda k: wx_norm.to_dict()[k]),
            "equation_of_time": equation_of_time(day_of_year),
            "true_solar_time":  TST,
            "contribution_ledger": {"western": wx_ledger},
            "provenance": build_provenance(
                house_system=normalize_house_system(western_chart.get("house_system")),
            ),
        }
    except BaziEngineError:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal calculation error")


# ── /calculate/tst ───────────────────────────────────────────────────────────

class TSTRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")
    ambiguousTime: AmbiguousTimeChoice = "earlier"
    nonexistentTime: NonexistentTimePolicy = "error"


class TSTResponse(BaseModel):
    input: Dict[str, Any]
    civil_time_hours: float
    longitude_correction_hours: float
    equation_of_time_hours: float
    true_solar_time_hours: float
    true_solar_time_formatted: str
    provenance: ProvenanceResponse


@router.post("/tst", response_model=TSTResponse)
def calculate_tst_endpoint(req: TSTRequest) -> Dict[str, Any]:
    """True Solar Time (TST) calculation."""
    try:
        dt, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        day_of_year = dt.timetuple().tm_yday
        civil_hours = dt.hour + dt.minute / 60 + dt.second / 3600
        delta_t_long = req.lon * 4 / 60
        E_t = equation_of_time(day_of_year) / 60
        TST = (civil_hours + delta_t_long + E_t) % 24
        hours = int(TST)
        minutes = int((TST - hours) * 60)
        return {
            "input": {"date": req.date, "tz": req.tz, "lon": req.lon},
            "civil_time_hours":             round(civil_hours, 4),
            "longitude_correction_hours":   round(delta_t_long, 4),
            "equation_of_time_hours":       round(E_t, 4),
            "true_solar_time_hours":        round(TST, 4),
            "true_solar_time_formatted":    f"{hours:02d}:{minutes:02d}",
            "provenance": build_provenance(),
        }
    except BaziEngineError:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal calculation error")
