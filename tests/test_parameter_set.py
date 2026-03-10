"""Tests: Versionable parameter_set in Wu-Xing calculations."""
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
    r = client.post("/calculate/fusion", json=PAYLOAD)
    return r.status_code == 200


_HAS_EPHEMERIS = _ephemeris_available()
_skip_no_ephe = pytest.mark.skipif(
    not _HAS_EPHEMERIS,
    reason="Swiss Ephemeris files not available",
)


@_skip_no_ephe
class TestParameterSet:
    def test_provenance_has_parameter_set(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        assert "parameter_set" in data["provenance"]

    def test_parameter_set_has_version(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        ps = data["provenance"]["parameter_set"]
        assert "version" in ps

    def test_parameter_set_has_retrograde_weight(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        ps = data["provenance"]["parameter_set"]
        assert "retrograde_weight" in ps
        assert ps["retrograde_weight"] == 1.3

    def test_parameter_set_has_hidden_stem_weights(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        ps = data["provenance"]["parameter_set"]
        assert "hidden_stem_main_qi" in ps
        assert ps["hidden_stem_main_qi"] == 1.0
        assert "hidden_stem_middle_qi" in ps
        assert ps["hidden_stem_middle_qi"] == 0.5
        assert "hidden_stem_residual_qi" in ps
        assert ps["hidden_stem_residual_qi"] == 0.3

    def test_parameter_set_in_wuxing_endpoint(self):
        r = client.post("/calculate/wuxing", json=PAYLOAD)
        data = r.json()
        assert "parameter_set" in data["provenance"]


def test_parameter_set_contains_aspect_orbs():
    """Aspect orbs must be documented in parameter_set."""
    from bazi_engine.provenance import WUXING_PARAMETER_SET
    assert "aspect_orbs" in WUXING_PARAMETER_SET
    orbs = WUXING_PARAMETER_SET["aspect_orbs"]
    assert "conjunction" in orbs
    assert "opposition" in orbs
    assert orbs["conjunction"] == 8.0
