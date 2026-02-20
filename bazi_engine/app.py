from contextlib import asynccontextmanager
import os
import hmac
import hashlib
import time
from fastapi import FastAPI, HTTPException, Query, Request, Header
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime, timezone
from .types import BaziInput, Pillar
from .constants import STEMS, BRANCHES, ANIMALS
from .bazi import compute_bazi
from .western import compute_western_chart
from .fusion import (
    compute_fusion_analysis,
    PLANET_TO_WUXING,
    WUXING_ORDER,
    WuXingVector,
    equation_of_time,
    true_solar_time,
    calculate_wuxing_vector_from_planets,
    calculate_wuxing_from_bazi,
    calculate_harmony_index
)
from .time_utils import resolve_local_iso, LocalTimeError
from .bafe import validate_request as bafe_validate_request
# Legacy ephemeris bootstrap removed: no implicit downloads at startup


_BUILD_VERSION = "1.0.0-rc1-20260220"


def _build_metadata() -> Dict[str, str]:
    """Expose deploy metadata to verify that docs belong to the latest build."""
    return {
        "version": _BUILD_VERSION,
        "railway_commit_sha": os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"),
        "railway_deploy_id": os.getenv("RAILWAY_DEPLOYMENT_ID", "unknown"),
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logging.getLogger("uvicorn").info(f"BAFE starting: {_BUILD_VERSION}")
    yield


app = FastAPI(
    title="BaZi Engine v2 API",
    description="API for BaZi (Chinese Astrology) and Basic Western Astrology calculations.",
    version=_BUILD_VERSION,
    lifespan=lifespan
)

ZODIAC_SIGNS_DE = [
    "Widder",
    "Stier",
    "Zwillinge",
    "Krebs",
    "Löwe",
    "Jungfrau",
    "Waage",
    "Skorpion",
    "Schütze",
    "Steinbock",
    "Wassermann",
    "Fische",
]

STEM_TO_ELEMENT = {
    "Jia": "Holz",
    "Yi": "Holz",
    "Bing": "Feuer",
    "Ding": "Feuer",
    "Wu": "Erde",
    "Ji": "Erde",
    "Geng": "Metall",
    "Xin": "Metall",
    "Ren": "Wasser",
    "Gui": "Wasser",
}

BRANCH_TO_ANIMAL = {
    "Zi": "Ratte",
    "Chou": "Ochse",
    "Yin": "Tiger",
    "Mao": "Hase",
    "Chen": "Drache",
    "Si": "Schlange",
    "Wu": "Pferd",
    "Wei": "Ziege",
    "Shen": "Affe",
    "You": "Hahn",
    "Xu": "Hund",
    "Hai": "Schwein",
}


def format_pillar(pillar: Pillar) -> Dict[str, str]:
    stem = STEMS[pillar.stem_index]
    branch = BRANCHES[pillar.branch_index]
    return {
        "stamm": stem,
        "zweig": branch,
        "tier": BRANCH_TO_ANIMAL[branch],
        "element": STEM_TO_ELEMENT[stem],
    }


class BaziRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time (e.g. 2024-02-10T14:30:00)")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(13.4050, description="Longitude in degrees")
    lat: float = Field(52.52, description="Latitude in degrees")
    standard: Literal["CIVIL", "LMT"] = "CIVIL"
    boundary: Literal["midnight", "zi"] = "midnight"
    strict: bool = True
    ambiguousTime: Literal["earlier", "later"] = "earlier"
    nonexistentTime: Literal["error", "shift_forward"] = "error"

class WesternBodyResponse(BaseModel):
    name: str = Field(..., description="Planet name")
    longitude: float = Field(..., description="0-360 degrees")
    latitude: float
    distance: float
    speed: float
    is_retrograde: bool
    zodiac_sign: int
    degree_in_sign: float

class WesternChartResponse(BaseModel):
    jd_ut: float
    house_system: str
    bodies: Dict[str, WesternBodyResponse]
    houses: Dict[str, float]
    angles: Dict[str, float]

class WesternRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(13.4050, description="Longitude in degrees")
    lat: float = Field(52.52, description="Latitude in degrees")
    ambiguousTime: Literal["earlier", "later"] = "earlier"
    nonexistentTime: Literal["error", "shift_forward"] = "error"

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "service": "bazi_engine_v2",
        **_build_metadata(),
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/build")
def build_info():
    return _build_metadata()


@app.post("/validate")
async def validate(payload: Dict[str, Any]):
    """Contract-first validator endpoint (spec/schemas Draft-07)."""
    try:
        return bafe_validate_request(payload)
    except ValueError as e:
        # Request schema violation or invalid configuration
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Do not leak internals by default
        raise HTTPException(status_code=500, detail="Internal validation error")


@app.get("/api")
def api_endpoint(
    datum: str = Query(..., description="Datum im Format YYYY-MM-DD"),
    zeit: str = Query(..., description="Zeit im Format HH:MM[:SS]"),
    ort: Optional[str] = Query(None, description="Ort als 'lat,lon' oder freier Text"),
    tz: str = Query("Europe/Berlin", description="Timezone name"),
    lon: float = Query(13.4050, description="Longitude in degrees"),
    lat: float = Query(52.52, description="Latitude in degrees"),
    ambiguousTime: Literal["earlier", "later"] = Query("earlier"),
    nonexistentTime: Literal["error", "shift_forward"] = Query("error"),
):
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
        dt_utc = dt.astimezone(timezone.utc)
        chart = compute_western_chart(dt_utc, lat, lon)
        sun = chart.get("bodies", {}).get("Sun")
        if not sun or "zodiac_sign" not in sun:
            raise ValueError("Sonnenposition konnte nicht berechnet werden.")
        sign_index = int(sun["zodiac_sign"])
        sign_name = ZODIAC_SIGNS_DE[sign_index]
        return {
            "sonne": sign_name,
            "input": {
                "datum": datum,
                "zeit": zeit,
                "ort": ort,
                "tz": tz,
                "lat": lat,
                "lon": lon,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/calculate/bazi")
def calculate_bazi_endpoint(req: BaziRequest):
    try:
        dt_local, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        resolved_naive = dt_local.replace(tzinfo=None).isoformat()
        fold = 0 if req.ambiguousTime == "earlier" else 1
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
                "year": format_pillar(res.pillars.year),
                "month": format_pillar(res.pillars.month),
                "day": format_pillar(res.pillars.day),
                "hour": format_pillar(res.pillars.hour),
            },
            "chinese": {
                "year": {
                    "stem": STEMS[res.pillars.year.stem_index],
                    "branch": BRANCHES[res.pillars.year.branch_index],
                    "animal": ANIMALS[res.pillars.year.branch_index],
                },
                "month_master": STEMS[res.pillars.month.stem_index],
                "day_master": STEMS[res.pillars.day.stem_index],
                "hour_master": STEMS[res.pillars.hour.stem_index],
            },
            "dates": {
                "birth_local": res.birth_local_dt.isoformat(),
                "birth_utc": res.birth_utc_dt.isoformat(),
                "lichun_local": res.lichun_local_dt.isoformat()
            },
            "solar_terms_count": len(res.solar_terms_local_dt) if res.solar_terms_local_dt else 0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/calculate/western")
def calculate_western_endpoint(req: WesternRequest):
    try:
        dt_local, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        dt_utc = dt_local.astimezone(timezone.utc)
        
        chart = compute_western_chart(dt_utc, req.lat, req.lon)
        return chart
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# FUSION ASTROLOGY ENDPOINTS
# =============================================================================

class FusionRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")
    lat: float = Field(..., description="Latitude in degrees")
    ambiguousTime: Literal["earlier", "later"] = "earlier"
    nonexistentTime: Literal["error", "shift_forward"] = "error"
    bazi_pillars: Optional[Dict[str, Dict[str, str]]] = Field(
        None,
        description="Ba Zi pillars (optional — computed automatically if omitted)"
    )

class FusionResponse(BaseModel):
    input: Dict[str, Any]
    wu_xing_vectors: Dict[str, Dict[str, float]]
    harmony_index: Dict[str, Any]
    elemental_comparison: Dict[str, Dict[str, float]]
    cosmic_state: float
    fusion_interpretation: str

@app.post("/calculate/fusion", response_model=FusionResponse)
def calculate_fusion_endpoint(req: FusionRequest):
    """
    Fusion Astrology Analysis - Wu-Xing + Western Integration.
    
    Calculates the harmony between western planetary energies and
    chinese Ba Zi elemental structure using vector mathematics.
    
    Returns:
    - Wu-Xing vectors for both systems
    - Harmony Index (0-1 scale)
    - Element-by-element comparison
    - Cosmic State metric
    - Interpretation
    """
    try:
        dt_local, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        dt_utc = dt_local.astimezone(timezone.utc)

        # Get western chart
        western_chart = compute_western_chart(dt_utc, req.lat, req.lon)

        # Compute BaZi pillars if not provided
        pillars = req.bazi_pillars
        if pillars is None:
            fold = 0 if req.ambiguousTime == "earlier" else 1
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
                "year": format_pillar(bazi_result.pillars.year),
                "month": format_pillar(bazi_result.pillars.month),
                "day": format_pillar(bazi_result.pillars.day),
                "hour": format_pillar(bazi_result.pillars.hour),
            }

        # Compute fusion analysis
        fusion = compute_fusion_analysis(
            birth_utc_dt=dt_utc,
            latitude=req.lat,
            longitude=req.lon,
            bazi_pillars=pillars,
            western_bodies=western_chart["bodies"]
        )
        
        return {
            "input": {
                "date": req.date,
                "tz": req.tz,
                "lon": req.lon,
                "lat": req.lat
            },
            "wu_xing_vectors": fusion["wu_xing_vectors"],
            "harmony_index": fusion["harmony_index"],
            "elemental_comparison": fusion["elemental_comparison"],
            "cosmic_state": fusion["cosmic_state"],
            "fusion_interpretation": fusion["fusion_interpretation"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class WxRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")
    lat: float = Field(..., description="Latitude in degrees")
    ambiguousTime: Literal["earlier", "later"] = "earlier"
    nonexistentTime: Literal["error", "shift_forward"] = "error"

class WxResponse(BaseModel):
    input: Dict[str, Any]
    wu_xing_vector: Dict[str, float]
    dominant_element: str
    equation_of_time: float
    true_solar_time: float

@app.post("/calculate/wuxing", response_model=WxResponse)
def calculate_wuxing_endpoint(req: WxRequest):
    """
    Calculate Wu-Xing Element Vector from Western Planets.
    
    Maps planetary positions to Five Elements (Wu Xing) and
    returns the elemental distribution vector.
    """
    try:
        dt, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        dt_utc = dt.astimezone(timezone.utc)

        # Get western chart
        western_chart = compute_western_chart(dt_utc, req.lat, req.lon)

        # Calculate Wu-Xing vector
        wx_vector = calculate_wuxing_vector_from_planets(western_chart["bodies"])
        wx_normalized = wx_vector.normalize()
        
        # Get day of year for equation of time
        day_of_year = dt.timetuple().tm_yday
        
        # Calculate TST
        civil_time_hours = dt.hour + dt.minute / 60
        TST = true_solar_time(civil_time_hours, req.lon, day_of_year)
        
        return {
            "input": {
                "date": req.date,
                "tz": req.tz,
                "lon": req.lon,
                "lat": req.lat
            },
            "wu_xing_vector": wx_normalized.to_dict(),
            "dominant_element": max(wx_normalized.to_dict(), key=lambda k: wx_normalized.to_dict()[k]),
            "equation_of_time": equation_of_time(day_of_year),
            "true_solar_time": TST
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class TSTRequest(BaseModel):
    date: str = Field(..., description="ISO 8601 local date time")
    tz: str = Field("Europe/Berlin", description="Timezone name")
    lon: float = Field(..., description="Longitude in degrees")
    ambiguousTime: Literal["earlier", "later"] = "earlier"
    nonexistentTime: Literal["error", "shift_forward"] = "error"

class TSTResponse(BaseModel):
    input: Dict[str, Any]
    civil_time_hours: float
    longitude_correction_hours: float
    equation_of_time_hours: float
    true_solar_time_hours: float
    true_solar_time_formatted: str

@app.post("/calculate/tst", response_model=TSTResponse)
def calculate_tst_endpoint(req: TSTRequest):
    """
    Calculate True Solar Time (TST).
    
    Applies Equation of Time and longitude correction to convert
    civil time to astronomically correct solar time.
    
    Essential for accurate Ba Zi hour pillar calculations.
    """
    try:
        # Resolve time with DST handling
        dt, _ = resolve_local_iso(
            req.date, req.tz,
            ambiguous=req.ambiguousTime, nonexistent=req.nonexistentTime,
        )
        
        # Get day of year
        day_of_year = dt.timetuple().tm_yday
        
        # Civil time in hours
        civil_hours = dt.hour + dt.minute / 60 + dt.second / 3600
        
        # Longitude correction
        delta_t_long = req.lon * 4 / 60  # 4 minutes per degree
        
        # Equation of Time
        E_t = equation_of_time(day_of_year) / 60  # Convert to hours
        
        # True Solar Time
        TST = civil_hours + delta_t_long + E_t
        TST = TST % 24
        
        # Format TST as HH:MM
        hours = int(TST)
        minutes = int((TST - hours) * 60)
        tst_formatted = f"{hours:02d}:{minutes:02d}"
        
        return {
            "input": {
                "date": req.date,
                "tz": req.tz,
                "lon": req.lon
            },
            "civil_time_hours": round(civil_hours, 4),
            "longitude_correction_hours": round(delta_t_long, 4),
            "equation_of_time_hours": round(E_t, 4),
            "true_solar_time_hours": round(TST, 4),
            "true_solar_time_formatted": tst_formatted
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/info/wuxing-mapping")
def get_wuxing_mapping():
    """
    Get the planet to Wu-Xing element mapping used by this API.
    """
    return {
        "mapping": PLANET_TO_WUXING,
        "order": WUXING_ORDER,
        "description": {
            "PLANET_TO_WUXING": "Western planet to Chinese element mapping",
            "WUXING_ORDER": "Wu Xing cycle order: Holz -> Feuer -> Erde -> Metall -> Wasser"
        }
    }


# =============================================================================
# ELEVENLABS WEBHOOK ENDPOINT
# =============================================================================

class ElevenLabsChartRequest(BaseModel):
    birthDate: str = Field(..., description="Birth date in YYYY-MM-DD format")
    birthTime: Optional[str] = Field(None, description="Birth time in HH:MM format (optional)")
    birthPlace: Optional[str] = Field(None, description="Place name, e.g. 'Berlin, DE' — resolves lat/lon/timezone")
    birthLat: Optional[float] = Field(None, description="Birth latitude in degrees")
    birthLon: Optional[float] = Field(None, description="Birth longitude in degrees")
    birthTz: Optional[str] = Field(None, description="Birth timezone (e.g. Europe/Berlin)")
    ambiguousTime: Literal["earlier", "later"] = Field(
        "earlier", description="DST fall-back: 'earlier' (fold=0) or 'later' (fold=1)")
    nonexistentTime: Literal["error", "shift_forward"] = Field(
        "error", description="DST spring-forward gap: 'error' rejects, 'shift_forward' auto-adjusts")


def geocode_place(place: str, language: str = "de") -> Dict[str, Any]:
    """Resolve place name to lat/lon/timezone via Open-Meteo Geocoding API (free, no key).

    Accepts formats like "Berlin", "Berlin, DE", "Tokyo, JP".
    If a comma-separated country code is present, results are filtered by it.
    """
    import json as _json
    from urllib.parse import urlencode
    from urllib.request import urlopen, Request as UrlReq

    # Split "City, CC" into name + optional country filter
    parts = [p.strip() for p in place.split(",", maxsplit=1)]
    search_name = parts[0]
    country_filter = parts[1].upper() if len(parts) > 1 and len(parts[1].strip()) == 2 else None

    url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode({
        "name": search_name, "count": 5, "language": language, "format": "json",
    })
    with urlopen(UrlReq(url, headers={"User-Agent": "bafe-bazi-engine/1.0"}), timeout=5) as resp:
        data = _json.loads(resp.read().decode())

    results = data.get("results") or []
    if country_filter:
        filtered = [r for r in results if r.get("country_code", "").upper() == country_filter]
        if filtered:
            results = filtered

    if not results:
        raise ValueError(f"Could not geocode place: {place}")
    r = results[0]
    return {
        "lat": float(r["latitude"]),
        "lon": float(r["longitude"]),
        "timezone": str(r.get("timezone") or ""),
        "name": str(r.get("name") or place),
        "country_code": str(r.get("country_code") or ""),
    }


def verify_elevenlabs_signature(
    payload: bytes,
    signature_header: Optional[str],
    secret: str,
    tolerance_ms: int = 300000  # 5 minutes
) -> bool:
    """Verify HMAC signature from ElevenLabs-Signature header."""
    if not signature_header:
        return False

    # Parse signature header: "t=<timestamp>,v1=<signature>"
    parts = signature_header.split(',')
    timestamp_part = next((p for p in parts if p.startswith('t=')), None)
    signature_part = next((p for p in parts if p.startswith('v1=')), None)

    if not timestamp_part or not signature_part:
        return False

    timestamp = int(timestamp_part.split('=')[1])
    provided_signature = signature_part.split('=')[1]

    # Check timestamp tolerance
    now = int(time.time() * 1000)
    if abs(now - timestamp) > tolerance_ms:
        return False

    # Compute expected signature
    signed_payload = f"{timestamp}.".encode() + payload
    expected_signature = hmac.new(
        secret.encode(),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(provided_signature, expected_signature)


@app.post("/api/webhooks/chart")
async def elevenlabs_chart_webhook(
    request: Request,
    elevenlabs_signature: Optional[str] = Header(None, alias="elevenlabs-signature"),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    authorization: Optional[str] = Header(None)
):
    """
    ElevenLabs Agent Tool: Get Astrology Chart

    Returns Western zodiac sign and Chinese BaZi data for a birth date.
    Supports multiple auth methods: HMAC signature, API key header, or Bearer token.
    """
    tool_secret = os.environ.get("ELEVENLABS_TOOL_SECRET")

    if not tool_secret:
        raise HTTPException(status_code=500, detail="ELEVENLABS_TOOL_SECRET not configured")

    # Get raw body for signature verification
    raw_body = await request.body()

    # Try multiple authentication methods
    auth_valid = False

    # Method 1: HMAC signature (preferred)
    if elevenlabs_signature:
        auth_valid = verify_elevenlabs_signature(raw_body, elevenlabs_signature, tool_secret)

    # Method 2: Simple API key header
    if not auth_valid and x_api_key:
        auth_valid = hmac.compare_digest(x_api_key, tool_secret)

    # Method 3: Bearer token
    if not auth_valid and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            auth_valid = hmac.compare_digest(token, tool_secret)

    if not auth_valid:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    # Parse request
    try:
        import json
        data = json.loads(raw_body)
        req = ElevenLabsChartRequest(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

    # Resolve location from birthPlace if lat/lon/tz not fully specified
    geo_result = None
    lat = req.birthLat
    lon = req.birthLon
    tz = req.birthTz

    if req.birthPlace and (lat is None or lon is None or not tz):
        try:
            geo_result = geocode_place(req.birthPlace)
            if lat is None:
                lat = geo_result["lat"]
            if lon is None:
                lon = geo_result["lon"]
            if not tz:
                tz = geo_result["timezone"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Geocoding failed for '{req.birthPlace}': {e}")

    # Final fallbacks
    if lat is None:
        lat = 52.52
    if lon is None:
        lon = 13.405
    if not tz:
        tz = "Europe/Berlin"

    assumed_time = req.birthTime is None
    birth_time = req.birthTime or "12:00"
    datetime_str = f"{req.birthDate}T{birth_time}:00"

    try:
        # Resolve local time with explicit DST handling
        dt, time_res = resolve_local_iso(
            datetime_str, tz,
            ambiguous=req.ambiguousTime,
            nonexistent=req.nonexistentTime,
        )
        dt_utc = dt.astimezone(timezone.utc)

        # Calculate Western chart
        western_chart = compute_western_chart(dt_utc, lat, lon)
        bodies = western_chart.get("bodies", {})
        sun = bodies.get("Sun", {})
        moon = bodies.get("Moon", {})

        sun_sign_idx = int(sun.get("zodiac_sign", 0))
        moon_sign_idx = int(moon.get("zodiac_sign", 0))
        sun_sign = ZODIAC_SIGNS_DE[sun_sign_idx]
        moon_sign = ZODIAC_SIGNS_DE[moon_sign_idx]

        zodiac_en = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                     "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        # Calculate BaZi using the resolved local time
        resolved_naive_iso = dt.replace(tzinfo=None).isoformat()
        inp = BaziInput(
            birth_local=resolved_naive_iso,
            timezone=tz,
            longitude_deg=lon,
            latitude_deg=lat,
            time_standard="CIVIL",
            day_boundary="midnight",
            strict_local_time=True,
            fold=time_res.fold,
        )
        bazi_result = compute_bazi(inp)

        # Format BaZi pillars
        year_pillar = format_pillar(bazi_result.pillars.year)
        month_pillar = format_pillar(bazi_result.pillars.month)
        day_pillar = format_pillar(bazi_result.pillars.day)
        hour_pillar = format_pillar(bazi_result.pillars.hour)

        # Build pillar dict for fusion analysis
        bazi_pillars_for_fusion = {
            "year": {"stamm": year_pillar["stamm"], "zweig": year_pillar["zweig"]},
            "month": {"stamm": month_pillar["stamm"], "zweig": month_pillar["zweig"]},
            "day": {"stamm": day_pillar["stamm"], "zweig": day_pillar["zweig"]},
            "hour": {"stamm": hour_pillar["stamm"], "zweig": hour_pillar["zweig"]},
        }

        # Compute full fusion analysis
        fusion = compute_fusion_analysis(
            birth_utc_dt=dt_utc,
            latitude=lat,
            longitude=lon,
            bazi_pillars=bazi_pillars_for_fusion,
            western_bodies=bodies,
        )

        # Retrograde planets for voice agent context
        retrogrades = [name for name, b in bodies.items() if b.get("is_retrograde")]

        # Dominant elements
        wu_xing = fusion["wu_xing_vectors"]
        western_dominant = max(wu_xing["western_planets"], key=lambda k: wu_xing["western_planets"][k])
        bazi_dominant = max(wu_xing["bazi_pillars"], key=lambda k: wu_xing["bazi_pillars"][k])

        # Ascendant sign
        asc_raw = western_chart.get("angles", {}).get("Ascendant")
        asc_sign = None
        asc_deg_in_sign = None
        if isinstance(asc_raw, (int, float)):
            asc_sign = ZODIAC_SIGNS_DE[int(asc_raw // 30) % 12]
            asc_deg_in_sign = round(asc_raw % 30, 2)

        # Collect warnings for agent transparency
        warnings: list[str] = []
        if assumed_time:
            warnings.append("Geburtszeit nicht angegeben: Ascendent/Häuser sind nur Näherung.")
        if time_res.warning:
            warnings.append(time_res.warning)

        return {
            "western": {
                "sunSign": sun_sign,
                "moonSign": moon_sign,
                "sunSignEnglish": zodiac_en[sun_sign_idx],
                "moonSignEnglish": zodiac_en[moon_sign_idx],
                "ascendant": asc_raw,
                "ascendantSign": asc_sign,
                "ascendantDegreeInSign": asc_deg_in_sign,
                "retrogradePlanets": retrogrades,
            },
            "eastern": {
                "yearAnimal": year_pillar["tier"],
                "yearElement": year_pillar["element"],
                "monthAnimal": month_pillar["tier"],
                "monthElement": month_pillar["element"],
                "dayAnimal": day_pillar["tier"],
                "dayElement": day_pillar["element"],
                "dayMaster": day_pillar["stamm"],
                "hourAnimal": hour_pillar["tier"],
                "hourElement": hour_pillar["element"],
            },
            "fusion": {
                "harmonyIndex": fusion["harmony_index"]["harmony_index"],
                "harmonyInterpretation": fusion["harmony_index"]["interpretation"],
                "cosmicState": fusion["cosmic_state"],
                "westernDominantElement": western_dominant,
                "baziDominantElement": bazi_dominant,
                "wuXingWestern": wu_xing["western_planets"],
                "wuXingBazi": wu_xing["bazi_pillars"],
                "elementalComparison": fusion["elemental_comparison"],
                "interpretation": fusion["fusion_interpretation"],
            },
            "summary": {
                "sternzeichen": sun_sign,
                "mondzeichen": moon_sign,
                "chinesischesZeichen": f"{year_pillar['element']} {year_pillar['tier']}",
                "tagesmeister": f"{day_pillar['element']} ({day_pillar['stamm']})",
                "harmonie": f"{fusion['harmony_index']['harmony_index']:.0%}",
                "dominantesElement": f"West: {western_dominant}, Ost: {bazi_dominant}",
            },
            "meta": {
                "time": {
                    "inputLocal": time_res.input_local_iso,
                    "resolvedLocal": time_res.resolved_local_iso,
                    "resolvedUtc": time_res.resolved_utc_iso,
                    "timezone": time_res.tz,
                    "tzAbbrev": time_res.tz_abbrev,
                    "status": time_res.status,
                    "fold": time_res.fold,
                    "adjustedMinutes": time_res.adjusted_minutes,
                    "assumedTime": assumed_time,
                    "warnings": warnings,
                },
                "location": {
                    "lat": lat,
                    "lon": lon,
                    "tz": tz,
                    "birthPlace": req.birthPlace,
                    "geocoded": geo_result,
                },
            },
        }

    except LocalTimeError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": str(e),
                "hint": "The given birth time does not exist due to a DST transition. "
                        "Please provide a valid local time.",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
