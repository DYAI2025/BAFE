"""Tests: planetary aspects in /calculate/western response."""
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
    r = client.post("/calculate/western", json=PAYLOAD)
    return r.status_code == 200


_HAS_EPHEMERIS = _ephemeris_available()
_skip_no_ephe = pytest.mark.skipif(
    not _HAS_EPHEMERIS,
    reason="Swiss Ephemeris files not available",
)


@_skip_no_ephe
class TestAspects:
    """Aspects must appear in /calculate/western response."""

    def test_aspects_key_exists(self):
        r = client.post("/calculate/western", json=PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "aspects" in data
        assert isinstance(data["aspects"], list)

    def test_aspect_structure(self):
        r = client.post("/calculate/western", json=PAYLOAD)
        data = r.json()
        if data["aspects"]:
            aspect = data["aspects"][0]
            assert "planet1" in aspect
            assert "planet2" in aspect
            assert "type" in aspect
            assert "angle" in aspect
            assert "orb" in aspect
            assert aspect["type"] in (
                "conjunction", "opposition", "trine",
                "square", "sextile",
            )

    def test_aspect_orb_within_limit(self):
        r = client.post("/calculate/western", json=PAYLOAD)
        data = r.json()
        max_orb = 10.0  # degrees
        for aspect in data["aspects"]:
            assert abs(aspect["orb"]) <= max_orb

    def test_no_self_aspects(self):
        r = client.post("/calculate/western", json=PAYLOAD)
        data = r.json()
        for aspect in data["aspects"]:
            assert aspect["planet1"] != aspect["planet2"]

    def test_conjunction_near_zero(self):
        """A conjunction should have angle near 0°."""
        r = client.post("/calculate/western", json=PAYLOAD)
        data = r.json()
        conjunctions = [a for a in data["aspects"] if a["type"] == "conjunction"]
        for c in conjunctions:
            assert c["angle"] < 12  # within orb

    def test_at_least_some_aspects(self):
        """With 10 planets, there should be several aspects."""
        r = client.post("/calculate/western", json=PAYLOAD)
        data = r.json()
        assert len(data["aspects"]) >= 5
