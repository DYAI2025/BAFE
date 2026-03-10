"""
transit.py — Real-time planetary transit calculations.

Computes current planetary positions using Swiss Ephemeris.
Cached per hour (ADR-1: cachetools.TTLCache).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import swisseph as swe
from cachetools import TTLCache

from .ephemeris import SwissEphBackend, assert_no_moseph_fallback, datetime_utc_to_jd_ut

# Planet IDs for transit calculation (7 classical planets)
TRANSIT_PLANETS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
}

ZODIAC_SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]

# Planet weights for sector intensity calculation.
# Outer planets move slower → higher weight per sector presence.
PLANET_WEIGHTS = {
    "sun": 1.0,
    "moon": 0.5,
    "mercury": 0.6,
    "venus": 0.7,
    "mars": 0.8,
    "jupiter": 1.2,
    "saturn": 1.5,
}

# Cache: 1 hour TTL, max 64 entries (keyed by truncated hour)
_transit_cache: TTLCache = TTLCache(maxsize=64, ttl=3600)

# Timeline cache: 24h TTL (ADR-1), keyed by date+days
_timeline_cache: TTLCache = TTLCache(maxsize=16, ttl=86400)


def _cache_key(dt: datetime) -> str:
    """Truncate to hour for cache key."""
    return dt.strftime("%Y-%m-%dT%H")


def compute_transit_now(
    dt_utc: Optional[datetime] = None,
    ephe_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute current planetary positions.

    Args:
        dt_utc: UTC datetime (default: now)
        ephe_path: Swiss Ephemeris file path override

    Returns:
        Dict with computed_at, planets, sector_intensity
    """
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)

    key = _cache_key(dt_utc)
    if key in _transit_cache:
        return _transit_cache[key]

    backend = SwissEphBackend(ephe_path=ephe_path)
    jd_ut = datetime_utc_to_jd_ut(dt_utc)
    flags = backend.flags | swe.FLG_SPEED

    planets: Dict[str, Dict[str, Any]] = {}

    for name, pid in TRANSIT_PLANETS.items():
        (lon_deg, _lat, _dist, speed_lon, _, _), ret = swe.calc_ut(jd_ut, pid, flags)
        assert_no_moseph_fallback(flags, ret)
        sector = int(lon_deg // 30)
        planets[name] = {
            "longitude": round(lon_deg, 1),
            "sector": sector,
            "sign": ZODIAC_SIGNS[sector],
            "speed": round(speed_lon, 2),
        }

    # Sector intensity: weighted sum of planet presence per sector
    sector_intensity = [0.0] * 12
    for name, pdata in planets.items():
        weight = PLANET_WEIGHTS.get(name, 1.0)
        sector_intensity[pdata["sector"]] += weight

    # Normalize to 0-1 range
    max_val = max(sector_intensity) if max(sector_intensity) > 0 else 1.0
    sector_intensity = [round(v / max_val, 2) for v in sector_intensity]

    result = {
        "computed_at": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "planets": planets,
        "sector_intensity": sector_intensity,
    }

    _transit_cache[key] = result
    return result


def compute_transit_state(
    soulprint_sectors: List[float],
    quiz_sectors: List[float],
    dt_utc: Optional[datetime] = None,
    ephe_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute personalized transit state.

    Combines current planetary transits with user's soulprint and quiz vectors
    to produce a personal impact assessment.

    Args:
        soulprint_sectors: 12-element user soulprint vector
        quiz_sectors: 12-element quiz result vector
        dt_utc: UTC datetime (default: now)

    Returns:
        Transit State JSON conforming to TRANSIT_STATE_v1 schema
    """
    transit_now = compute_transit_now(dt_utc=dt_utc, ephe_path=ephe_path)
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)

    # Transit contribution per sector: weighted planet presence
    transit_sectors = transit_now["sector_intensity"]

    # Personal impact: transit_strength × (soulprint + quiz)
    impact = [0.0] * 12
    for s in range(12):
        personal = soulprint_sectors[s] + quiz_sectors[s]
        impact[s] = round(transit_sectors[s] * personal, 2)

    # Transit intensity: mean of non-zero impacts
    non_zero = [v for v in impact if v > 0]
    transit_intensity = round(sum(non_zero) / len(non_zero), 2) if non_zero else 0.0

    # Ring sectors: soulprint + quiz contribution + transit contribution
    ring_sectors = [
        round(soulprint_sectors[s] + quiz_sectors[s] * 0.5 + impact[s] * 0.3, 2)
        for s in range(12)
    ]

    # Detect events (pass ring_sectors for dominance_shift detection)
    events = _detect_events(transit_now, soulprint_sectors, impact, ring_sectors)

    return {
        "schema": "TRANSIT_STATE_v1",
        "generated_at": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ring": {"sectors": ring_sectors},
        "transit_contribution": {
            "sectors": [round(v, 2) for v in transit_sectors],
            "transit_intensity": transit_intensity,
        },
        "delta": {
            "vs_previous": None,
            "vs_30day_avg": None,  # Null until history store exists (ADR-2, Addendum 3.4)
        },
        "events": events,
    }


def _detect_events(
    transit_now: Dict[str, Any],
    soulprint: List[float],
    impact: List[float],
    ring_sectors: Optional[List[float]] = None,
    avg_30d_sectors: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """
    Detect transit events: resonance jumps, dominance shifts, moon events.

    Three MVP triggers:
    - resonance_jump: planet on user's peak sector, impact >= 0.18
    - dominance_shift: current dominant sector != 30-day avg dominant (margin >= 0.08)
    - moon_event: moon on high-impact sector (>= 0.5)

    dominance_shift requires avg_30d_sectors (History Store, T-03).
    Guard clause: skipped when avg_30d_sectors is None (Addendum 3.4).
    """
    events: List[Dict[str, Any]] = []

    # Find peak soulprint sector
    peak_sector = max(range(12), key=lambda s: soulprint[s])

    # Check each planet: if it sits on the user's peak sector
    for name, pdata in transit_now["planets"].items():
        sector = pdata["sector"]
        if sector == peak_sector and impact[sector] >= 0.18:
            events.append({
                "type": "resonance_jump",
                "priority": 1,
                "sector": sector,
                "trigger_planet": name,
                "description_de": f"{name.capitalize()} aktiviert dein {ZODIAC_SIGNS[sector].capitalize()}-Feld",
                "personal_context": f"Dein stärkstes Feld wird von {name.capitalize()} berührt",
            })

    # Dominance shift: fires when history store provides 30-day averages
    if avg_30d_sectors is not None and ring_sectors is not None:
        current_dominant = max(range(12), key=lambda s: ring_sectors[s])
        avg_dominant = max(range(12), key=lambda s: avg_30d_sectors[s])
        if current_dominant != avg_dominant:
            margin = ring_sectors[current_dominant] - ring_sectors[avg_dominant]
            if margin >= 0.08:
                events.append({
                    "type": "dominance_shift",
                    "priority": 1,
                    "sector": current_dominant,
                    "trigger_planet": "",
                    "description_de": (
                        f"Dein Schwerpunkt wechselt zu "
                        f"{ZODIAC_SIGNS[current_dominant].capitalize()}"
                    ),
                    "personal_context": (
                        f"Sektor {current_dominant} ({ZODIAC_SIGNS[current_dominant].capitalize()}) "
                        f"übernimmt die Führung"
                    ),
                })

    # Moon event: if moon is on a high-impact sector
    moon_sector = transit_now["planets"]["moon"]["sector"]
    if impact[moon_sector] >= 0.5:
        events.append({
            "type": "moon_event",
            "priority": 2,
            "sector": moon_sector,
            "trigger_planet": "moon",
            "description_de": f"Mond verstärkt dein {ZODIAC_SIGNS[moon_sector].capitalize()}-Feld",
            "personal_context": "Emotionale Resonanz heute besonders stark",
        })

    return events


def compute_transit_timeline(
    days: int = 7,
    start_utc: Optional[datetime] = None,
    ephe_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute multi-day transit forecast.

    Args:
        days: Number of days to forecast (1-30)
        start_utc: Start date (default: today at noon UTC)
        ephe_path: Swiss Ephemeris file path override

    Returns:
        Dict with list of daily transit snapshots
    """
    if start_utc is None:
        start_utc = datetime.now(timezone.utc).replace(
            hour=12, minute=0, second=0, microsecond=0
        )

    cache_key = f"timeline:{start_utc.strftime('%Y-%m-%d')}:{days}"
    if cache_key in _timeline_cache:
        return _timeline_cache[cache_key]

    result_days: List[Dict[str, Any]] = []
    for i in range(days):
        day_dt = start_utc + timedelta(days=i)
        snapshot = compute_transit_now(dt_utc=day_dt, ephe_path=ephe_path)
        result_days.append({
            "date": day_dt.strftime("%Y-%m-%d"),
            "planets": snapshot["planets"],
            "sector_intensity": snapshot["sector_intensity"],
        })

    result = {"days": result_days}
    _timeline_cache[cache_key] = result
    return result
