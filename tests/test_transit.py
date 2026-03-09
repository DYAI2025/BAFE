"""Tests for transit API endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from bazi_engine.app import app

client = TestClient(app)

# Known planetary longitudes for a fixed date (mock data).
# We mock swe.calc_ut to return deterministic values.
# Keys are swisseph planet IDs: SUN=0, MOON=1, MERCURY=2, VENUS=3, MARS=4, JUPITER=5, SATURN=6
MOCK_PLANET_DATA = {
    0: (348.7, 0.0, 1.0, 1.01, 0.0, 0.0),   # Sun → sector 11, pisces
    1: (187.2, 0.0, 0.003, 13.2, 0.0, 0.0),  # Moon → sector 6, libra
    2: (332.1, 0.0, 0.8, 1.8, 0.0, 0.0),     # Mercury → sector 11, pisces
    3: (15.4, 0.0, 0.7, 1.2, 0.0, 0.0),      # Venus → sector 0, aries
    4: (112.8, 0.0, 1.5, 0.7, 0.0, 0.0),     # Mars → sector 3, cancer
    5: (78.3, 0.0, 5.0, 0.08, 0.0, 0.0),     # Jupiter → sector 2, gemini
    6: (342.9, 0.0, 9.5, 0.03, 0.0, 0.0),    # Saturn → sector 11, pisces
}


def mock_calc_ut(jd_ut, planet_id, flags):
    """Mock swe.calc_ut to return deterministic planet positions."""
    if planet_id in MOCK_PLANET_DATA:
        return MOCK_PLANET_DATA[planet_id], 0
    raise Exception(f"Unknown planet {planet_id}")


class TestTransitNow:
    """GET /transit/now — current planetary positions."""

    def test_returns_200(self):
        with patch("bazi_engine.transit.swe.calc_ut", side_effect=mock_calc_ut):
            r = client.get("/transit/now")
        assert r.status_code == 200

    def test_response_has_required_fields(self):
        with patch("bazi_engine.transit.swe.calc_ut", side_effect=mock_calc_ut):
            r = client.get("/transit/now")
        data = r.json()
        assert "computed_at" in data
        assert "planets" in data
        assert "sector_intensity" in data

    def test_planets_have_required_fields(self):
        with patch("bazi_engine.transit.swe.calc_ut", side_effect=mock_calc_ut):
            r = client.get("/transit/now")
        data = r.json()
        planets = data["planets"]
        required_planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
        for name in required_planets:
            assert name in planets, f"Missing planet: {name}"
            p = planets[name]
            assert "longitude" in p
            assert "sector" in p
            assert "sign" in p
            assert "speed" in p

    def test_sector_is_longitude_divided_by_30(self):
        with patch("bazi_engine.transit.swe.calc_ut", side_effect=mock_calc_ut):
            r = client.get("/transit/now")
        data = r.json()
        sun = data["planets"]["sun"]
        # Sun at 348.7° → sector 11 (348.7 / 30 = 11.6)
        assert sun["sector"] == 11
        assert sun["sign"] == "pisces"

    def test_sector_intensity_has_12_elements(self):
        with patch("bazi_engine.transit.swe.calc_ut", side_effect=mock_calc_ut):
            r = client.get("/transit/now")
        data = r.json()
        assert len(data["sector_intensity"]) == 12

    def test_accepts_optional_datetime_param(self):
        with patch("bazi_engine.transit.swe.calc_ut", side_effect=mock_calc_ut):
            r = client.get("/transit/now?datetime=2026-03-09T12:00:00Z")
        assert r.status_code == 200

    def test_computed_at_is_iso_format(self):
        with patch("bazi_engine.transit.swe.calc_ut", side_effect=mock_calc_ut):
            r = client.get("/transit/now")
        data = r.json()
        dt = datetime.fromisoformat(data["computed_at"].replace("Z", "+00:00"))
        assert dt.tzinfo is not None
