"""
transit.py — Real-time planetary transit calculations.

Computes current planetary positions using Swiss Ephemeris.
Cached per hour (ADR-1: cachetools.TTLCache).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import swisseph as swe
from cachetools import TTLCache

from .ephemeris import SwissEphBackend, datetime_utc_to_jd_ut

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
        (lon_deg, _lat, _dist, speed_lon, _, _), _ret = swe.calc_ut(jd_ut, pid, flags)
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
