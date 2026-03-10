"""
routers/bazi.py — POST /calculate/bazi
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..bazi import compute_bazi
from ..constants import STEMS, BRANCHES, ANIMALS
from ..exc import BaziEngineError
from ..provenance import build_provenance
from ..time_utils import resolve_local_iso, AmbiguousTimeChoice, NonexistentTimePolicy
from ..types import BaziInput, Fold
from .shared import format_pillar, ProvenanceResponse

router = APIRouter(prefix="/calculate", tags=["BaZi"])


class BaziRequest(BaseModel):
    date: str = Field(..., description="Local ISO8601 datetime")
    tz: str = Field("Europe/Berlin", description="IANA timezone name")
    lon: float = Field(13.4050, description="Longitude in degrees")
    lat: float = Field(52.52, description="Latitude in degrees")
    standard: Literal["CIVIL", "LMT"] = Field("CIVIL")
    boundary: Literal["midnight", "zi"] = Field("midnight")
    ambiguousTime: AmbiguousTimeChoice = Field("earlier")
    nonexistentTime: NonexistentTimePolicy = Field("error")


class PillarDetail(BaseModel):
    stamm: str
    zweig: str
    tier: str
    element: str


class BaziPillarsResponse(BaseModel):
    year: PillarDetail
    month: PillarDetail
    day: PillarDetail
    hour: PillarDetail


class ChineseYearInfo(BaseModel):
    stem: str
    branch: str
    animal: str


class ChineseSection(BaseModel):
    year: ChineseYearInfo
    month_master: str
    day_master: str
    hour_master: str


class BaziDatesResponse(BaseModel):
    birth_local: str
    birth_utc: str
    lichun_local: str


class BaziTransitionResponse(BaseModel):
    solar_year: int
    is_before_lichun: bool
    lichun_year_start: str
    lichun_next: Optional[str] = None


class BaziResponse(BaseModel):
    input: BaziRequest
    pillars: BaziPillarsResponse
    chinese: ChineseSection
    dates: BaziDatesResponse
    transition: BaziTransitionResponse
    solar_terms_count: int
    provenance: ProvenanceResponse


@router.post("/bazi", response_model=BaziResponse)
def calculate_bazi_endpoint(req: BaziRequest) -> Dict[str, Any]:
    try:
        dt_local, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        resolved_naive = dt_local.replace(tzinfo=None).isoformat()
        fold: Fold = 0 if req.ambiguousTime == "earlier" else 1
        inp = BaziInput(
            birth_local=resolved_naive,
            timezone=req.tz,
            longitude_deg=req.lon,
            latitude_deg=req.lat,
            time_standard=req.standard,
            day_boundary=req.boundary,
            strict_local_time=True,
            fold=fold,
        )
        res = compute_bazi(inp)
        return {
            "input": req.model_dump(),
            "pillars": {
                "year":  format_pillar(res.pillars.year),
                "month": format_pillar(res.pillars.month),
                "day":   format_pillar(res.pillars.day),
                "hour":  format_pillar(res.pillars.hour),
            },
            "chinese": {
                "year": {
                    "stem":   STEMS[res.pillars.year.stem_index],
                    "branch": BRANCHES[res.pillars.year.branch_index],
                    "animal": ANIMALS[res.pillars.year.branch_index],
                },
                "month_master": STEMS[res.pillars.month.stem_index],
                "day_master":   STEMS[res.pillars.day.stem_index],
                "hour_master":  STEMS[res.pillars.hour.stem_index],
            },
            "dates": {
                "birth_local":  res.birth_local_dt.isoformat(),
                "birth_utc":    res.birth_utc_dt.isoformat(),
                "lichun_local": res.lichun_local_dt.isoformat(),
            },
            "transition": {
                "solar_year": res.solar_year,
                "is_before_lichun": res.is_before_lichun,
                "lichun_year_start": res.lichun_local_dt.isoformat(),
                "lichun_next": res.lichun_next_local_dt.isoformat() if res.lichun_next_local_dt else None,
            },
            "solar_terms_count": len(res.solar_terms_local_dt) if res.solar_terms_local_dt else 0,
            "provenance": build_provenance(),
        }
    except BaziEngineError:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal calculation error")
