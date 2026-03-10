"""Tests for provenance block in /calculate/* responses."""
from __future__ import annotations

import os
from datetime import datetime

import pytest

from fastapi.testclient import TestClient

from bazi_engine import __version__
from bazi_engine.app import app
from bazi_engine.provenance import build_provenance

client = TestClient(app)


def _ephemeris_available() -> bool:
    """Check if any /calculate endpoint requiring ephemeris works."""
    r = client.post("/calculate/bazi", json={
        "date": "2024-02-10T14:30:00", "tz": "Europe/Berlin",
        "lon": 13.405, "lat": 52.52,
    })
    return r.status_code == 200


_HAS_EPHEMERIS = _ephemeris_available()
_skip_no_ephe = pytest.mark.skipif(
    not _HAS_EPHEMERIS,
    reason="Swiss Ephemeris files not available (set EPHEMERIS_MODE=MOSEPH or SE_EPHE_PATH)",
)

PROVENANCE_FIELDS = {
    "engine_version",
    "parameter_set_id",
    "ruleset_id",
    "ephemeris_id",
    "tzdb_version_id",
    "house_system",
    "zodiac_mode",
    "computation_timestamp",
}

# Standard test payload for endpoints that need date/location
BAZI_PAYLOAD = {
    "date": "2024-02-10T14:30:00",
    "tz": "Europe/Berlin",
    "lon": 13.405,
    "lat": 52.52,
}


class TestBuildProvenance:
    """Unit tests for the build_provenance function."""

    def test_returns_all_fields(self):
        prov = build_provenance()
        assert set(prov.keys()) == PROVENANCE_FIELDS

    def test_engine_version_matches(self):
        prov = build_provenance()
        assert prov["engine_version"] == __version__

    def test_computation_timestamp_is_valid_iso(self):
        prov = build_provenance()
        ts = prov["computation_timestamp"]
        # Should parse without error
        dt = datetime.fromisoformat(ts)
        assert dt is not None

    def test_default_values(self):
        prov = build_provenance()
        assert prov["parameter_set_id"] == "default_v1"
        assert prov["ruleset_id"] == "traditional_bazi_2026"
        assert prov["house_system"] == "placidus"
        assert prov["zodiac_mode"] == "tropical"

    def test_overrides(self):
        prov = build_provenance(
            parameter_set_id="custom",
            house_system="whole_sign",
        )
        assert prov["parameter_set_id"] == "custom"
        assert prov["house_system"] == "whole_sign"


@_skip_no_ephe
class TestProvenanceInBaziEndpoint:
    """POST /calculate/bazi must include provenance."""

    def test_bazi_has_provenance(self):
        r = client.post("/calculate/bazi", json=BAZI_PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "provenance" in data
        assert set(data["provenance"].keys()) == PROVENANCE_FIELDS

    def test_bazi_provenance_version(self):
        r = client.post("/calculate/bazi", json=BAZI_PAYLOAD)
        data = r.json()
        assert data["provenance"]["engine_version"] == __version__

    def test_bazi_provenance_timestamp_valid(self):
        r = client.post("/calculate/bazi", json=BAZI_PAYLOAD)
        ts = r.json()["provenance"]["computation_timestamp"]
        dt = datetime.fromisoformat(ts)
        assert dt is not None


@_skip_no_ephe
class TestProvenanceInWesternEndpoint:
    """POST /calculate/western must include provenance."""

    def test_western_has_provenance(self):
        r = client.post("/calculate/western", json=BAZI_PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "provenance" in data
        assert set(data["provenance"].keys()) == PROVENANCE_FIELDS

    def test_western_provenance_version(self):
        r = client.post("/calculate/western", json=BAZI_PAYLOAD)
        data = r.json()
        assert data["provenance"]["engine_version"] == __version__


@_skip_no_ephe
class TestProvenanceInFusionEndpoint:
    """POST /calculate/fusion must include provenance."""

    def test_fusion_has_provenance(self):
        r = client.post("/calculate/fusion", json=BAZI_PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "provenance" in data
        assert set(data["provenance"].keys()) == PROVENANCE_FIELDS

    def test_fusion_provenance_version(self):
        r = client.post("/calculate/fusion", json=BAZI_PAYLOAD)
        data = r.json()
        assert data["provenance"]["engine_version"] == __version__


@_skip_no_ephe
class TestProvenanceInWuxingEndpoint:
    """POST /calculate/wuxing must include provenance."""

    def test_wuxing_has_provenance(self):
        r = client.post("/calculate/wuxing", json=BAZI_PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "provenance" in data
        assert set(data["provenance"].keys()) == PROVENANCE_FIELDS

    def test_wuxing_provenance_version(self):
        r = client.post("/calculate/wuxing", json=BAZI_PAYLOAD)
        data = r.json()
        assert data["provenance"]["engine_version"] == __version__


class TestProvenanceInTSTEndpoint:
    """POST /calculate/tst must include provenance."""

    def test_tst_has_provenance(self):
        payload = {"date": "2024-02-10T14:30:00", "tz": "Europe/Berlin", "lon": 13.405}
        r = client.post("/calculate/tst", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "provenance" in data
        assert set(data["provenance"].keys()) == PROVENANCE_FIELDS

    def test_tst_provenance_version(self):
        payload = {"date": "2024-02-10T14:30:00", "tz": "Europe/Berlin", "lon": 13.405}
        r = client.post("/calculate/tst", json=payload)
        data = r.json()
        assert data["provenance"]["engine_version"] == __version__

    def test_tst_provenance_timestamp_valid(self):
        payload = {"date": "2024-02-10T14:30:00", "tz": "Europe/Berlin", "lon": 13.405}
        r = client.post("/calculate/tst", json=payload)
        ts = r.json()["provenance"]["computation_timestamp"]
        dt = datetime.fromisoformat(ts)
        assert dt is not None


@_skip_no_ephe
class TestProvenanceConsistency:
    """All /calculate/* endpoints return consistent provenance structure."""

    @pytest.mark.parametrize("endpoint,payload", [
        ("/calculate/bazi", BAZI_PAYLOAD),
        ("/calculate/western", BAZI_PAYLOAD),
        ("/calculate/fusion", BAZI_PAYLOAD),
        ("/calculate/wuxing", BAZI_PAYLOAD),
        ("/calculate/tst", {"date": "2024-02-10T14:30:00", "tz": "Europe/Berlin", "lon": 13.405}),
    ])
    def test_all_endpoints_have_provenance(self, endpoint, payload):
        r = client.post(endpoint, json=payload)
        assert r.status_code == 200, f"{endpoint} returned {r.status_code}: {r.text}"
        data = r.json()
        assert "provenance" in data, f"{endpoint} missing provenance"
        prov = data["provenance"]
        assert prov["engine_version"] == __version__
        assert set(prov.keys()) == PROVENANCE_FIELDS
        # Timestamp must be parseable
        datetime.fromisoformat(prov["computation_timestamp"])
