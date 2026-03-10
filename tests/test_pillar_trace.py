"""Tests: pillar derivation trace in /calculate/bazi response."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bazi_engine.app import app

client = TestClient(app)

PAYLOAD = {
    "date": "2024-02-10T14:30:00",
    "tz": "Europe/Berlin",
    "lon": 13.405,
    "lat": 52.52,
}


def _ephemeris_available() -> bool:
    r = client.post("/calculate/bazi", json=PAYLOAD)
    return r.status_code == 200


_HAS_EPHEMERIS = _ephemeris_available()
_skip_no_ephe = pytest.mark.skipif(
    not _HAS_EPHEMERIS,
    reason="Swiss Ephemeris files not available",
)


@_skip_no_ephe
class TestPillarTrace:
    """Pillar derivation trace must be available."""

    def test_trace_key_exists(self):
        r = client.post("/calculate/bazi", json=PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "derivation_trace" in data

    def test_year_trace_has_lichun(self):
        r = client.post("/calculate/bazi", json=PAYLOAD)
        data = r.json()
        trace = data["derivation_trace"]
        assert "year" in trace
        assert "lichun_crossing_utc" in trace["year"]
        assert "is_before_lichun" in trace["year"]

    def test_month_trace_has_jieqi(self):
        r = client.post("/calculate/bazi", json=PAYLOAD)
        data = r.json()
        trace = data["derivation_trace"]
        assert "month" in trace
        assert "jieqi_crossing_utc" in trace["month"]
        assert "solar_longitude_deg" in trace["month"]

    def test_day_trace_has_jdn(self):
        r = client.post("/calculate/bazi", json=PAYLOAD)
        data = r.json()
        trace = data["derivation_trace"]
        assert "day" in trace
        assert "julian_day_number" in trace["day"]
        assert "sexagenary_index" in trace["day"]

    def test_hour_trace_has_branch(self):
        r = client.post("/calculate/bazi", json=PAYLOAD)
        data = r.json()
        trace = data["derivation_trace"]
        assert "hour" in trace
        assert "local_hour" in trace["hour"]
        assert "branch_index" in trace["hour"]
