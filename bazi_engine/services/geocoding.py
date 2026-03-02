"""
services/geocoding.py — Place name → lat/lon/timezone resolution.

Uses Open-Meteo Geocoding API (free, no API key required).
Extracted from app.py to keep HTTP utility logic separate from routing.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request as UrlReq, urlopen


def geocode_place(place: str, language: str = "de") -> Dict[str, Any]:
    """Resolve place name to lat/lon/timezone via Open-Meteo Geocoding API.

    Accepts formats like "Berlin", "Berlin, DE", "Tokyo, JP".
    If a comma-separated 2-letter country code is present, results are
    filtered by it.

    Args:
        place:    Place name, optionally with country code suffix.
        language: Language code for result names (default: "de").

    Returns:
        Dict with keys: lat, lon, timezone, name, country_code.

    Raises:
        ValueError: If no matching place is found.
    """
    parts = [p.strip() for p in place.split(",", maxsplit=1)]
    search_name = parts[0]
    country_filter = (
        parts[1].upper()
        if len(parts) > 1 and len(parts[1].strip()) == 2
        else None
    )

    url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode({
        "name": search_name, "count": 5, "language": language, "format": "json",
    })
    with urlopen(UrlReq(url, headers={"User-Agent": "bafe-bazi-engine/1.0"}), timeout=5) as resp:
        data = json.loads(resp.read().decode())

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
