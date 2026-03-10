"""Tests: Wu-Xing contribution ledger in fusion/wuxing responses."""
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
class TestWesternContributionLedger:
    """Per-planet Wu-Xing contribution breakdown."""

    def test_fusion_has_contribution_ledger(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "contribution_ledger" in data

    def test_ledger_has_western_entries(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        ledger = data["contribution_ledger"]
        assert "western" in ledger
        assert isinstance(ledger["western"], list)
        assert len(ledger["western"]) >= 5

    def test_western_entry_structure(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        entry = data["contribution_ledger"]["western"][0]
        assert "planet" in entry
        assert "element" in entry
        assert "weight" in entry
        assert "is_retrograde" in entry
        assert "category" in entry
        assert entry["element"] in ("Holz", "Feuer", "Erde", "Metall", "Wasser")
        assert entry["category"] in ("traditional", "modern_heuristic", "experimental")

    def test_mercury_shows_day_night_rationale(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        mercury = [e for e in data["contribution_ledger"]["western"]
                   if e["planet"] == "Mercury"]
        assert len(mercury) == 1
        assert "rationale" in mercury[0]
        assert "chart" in mercury[0]["rationale"].lower()

    def test_retrograde_weight_is_1_3(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        for entry in data["contribution_ledger"]["western"]:
            if entry["is_retrograde"]:
                assert entry["weight"] == 1.3
            else:
                assert entry["weight"] == 1.0

    def test_wuxing_endpoint_has_contribution_ledger(self):
        r = client.post("/calculate/wuxing", json=PAYLOAD)
        assert r.status_code == 200
        data = r.json()
        assert "contribution_ledger" in data
        assert "western" in data["contribution_ledger"]


@_skip_no_ephe
class TestBaziContributionLedger:
    """Per-pillar Wu-Xing contribution breakdown."""

    def test_ledger_has_bazi_entries(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        ledger = data["contribution_ledger"]
        assert "bazi" in ledger
        assert isinstance(ledger["bazi"], list)
        assert len(ledger["bazi"]) >= 4

    def test_bazi_entry_structure(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        entry = data["contribution_ledger"]["bazi"][0]
        assert "pillar" in entry
        assert "source" in entry
        assert "element" in entry
        assert "weight" in entry
        assert "category" in entry
        assert entry["pillar"] in ("year", "month", "day", "hour")
        assert entry["category"] == "traditional"

    def test_hidden_stems_have_qi_weights(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        hidden = [e for e in data["contribution_ledger"]["bazi"] if e["source"].startswith("hidden")]
        assert len(hidden) >= 1
        for h in hidden:
            assert h["weight"] in (1.0, 0.5, 0.3)

    def test_stem_weight_is_1(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        data = r.json()
        stems = [e for e in data["contribution_ledger"]["bazi"] if e["source"] == "stem"]
        assert len(stems) == 4
        for s in stems:
            assert s["weight"] == 1.0


@_skip_no_ephe
class TestCategoryTags:
    """Verify category assignment for contribution ledger entries."""

    TRADITIONAL_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    MODERN_PLANETS = {"Uranus", "Neptune", "Pluto"}
    EXPERIMENTAL_BODIES = {"Chiron", "Lilith", "North Node", "South Node"}

    def _western_ledger(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        assert r.status_code == 200
        return r.json()["contribution_ledger"]["western"]

    def _bazi_ledger(self):
        r = client.post("/calculate/fusion", json=PAYLOAD)
        assert r.status_code == 200
        return r.json()["contribution_ledger"]["bazi"]

    def test_traditional_planets_tagged_traditional(self):
        for entry in self._western_ledger():
            if entry["planet"] in self.TRADITIONAL_PLANETS:
                assert entry["category"] == "traditional", (
                    f"{entry['planet']} should be traditional, got {entry['category']}"
                )

    def test_modern_planets_tagged_modern_heuristic(self):
        for entry in self._western_ledger():
            if entry["planet"] in self.MODERN_PLANETS:
                assert entry["category"] == "modern_heuristic", (
                    f"{entry['planet']} should be modern_heuristic, got {entry['category']}"
                )

    def test_experimental_bodies_tagged_experimental(self):
        for entry in self._western_ledger():
            if entry["planet"] in self.EXPERIMENTAL_BODIES:
                assert entry["category"] == "experimental", (
                    f"{entry['planet']} should be experimental, got {entry['category']}"
                )

    def test_bazi_entries_all_traditional(self):
        for entry in self._bazi_ledger():
            assert entry["category"] == "traditional", (
                f"BaZi entry for {entry['pillar']}/{entry['source']} should be traditional"
            )
