"""
test_services_geocoding.py — Unit tests for bazi_engine/services/geocoding.py

HTTP calls are mocked — no network required. Tests the parsing logic,
country filtering, and error handling of geocode_place().
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from bazi_engine.services.geocoding import geocode_place

# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock_response(results: list) -> MagicMock:
    """Build a mock urlopen context manager returning given results."""
    body = json.dumps({"results": results}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


BERLIN_RESULT = {
    "name": "Berlin",
    "latitude": 52.52,
    "longitude": 13.405,
    "timezone": "Europe/Berlin",
    "country_code": "DE",
}

TOKYO_RESULT = {
    "name": "Tokyo",
    "latitude": 35.6762,
    "longitude": 139.6503,
    "timezone": "Asia/Tokyo",
    "country_code": "JP",
}

BERLIN_US_RESULT = {
    "name": "Berlin",
    "latitude": 44.4686,
    "longitude": -71.185,
    "timezone": "America/New_York",
    "country_code": "US",
}


class TestGeocodePlace:
    @patch("bazi_engine.services.geocoding.urlopen")
    def test_returns_berlin_coordinates(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([BERLIN_RESULT])
        result = geocode_place("Berlin")
        assert result["lat"] == 52.52
        assert result["lon"] == 13.405

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_returns_timezone(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([BERLIN_RESULT])
        result = geocode_place("Berlin")
        assert result["timezone"] == "Europe/Berlin"

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_returns_name(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([BERLIN_RESULT])
        result = geocode_place("Berlin")
        assert result["name"] == "Berlin"

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_returns_country_code(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([BERLIN_RESULT])
        result = geocode_place("Berlin")
        assert result["country_code"] == "DE"

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_returns_dict_with_required_keys(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([BERLIN_RESULT])
        result = geocode_place("Berlin")
        assert {"lat", "lon", "timezone", "name", "country_code"} <= result.keys()

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_empty_results_raises_value_error(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([])
        with pytest.raises(ValueError, match="Could not geocode"):
            geocode_place("NoSuchPlace123")

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_country_filter_selects_correct_result(self, mock_urlopen):
        """'Berlin, DE' should return the German Berlin, not the US one."""
        mock_urlopen.return_value = _mock_response([BERLIN_US_RESULT, BERLIN_RESULT])
        result = geocode_place("Berlin, DE")
        assert result["country_code"] == "DE"
        assert result["lat"] == 52.52

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_country_filter_ignored_if_no_match(self, mock_urlopen):
        """If no results match the country code, all results are used."""
        mock_urlopen.return_value = _mock_response([BERLIN_US_RESULT])
        result = geocode_place("Berlin, DE")
        # No DE result → falls back to first result
        assert result["country_code"] == "US"

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_lat_lon_are_floats(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([BERLIN_RESULT])
        result = geocode_place("Berlin")
        assert isinstance(result["lat"], float)
        assert isinstance(result["lon"], float)

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_first_result_used_without_country_filter(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([BERLIN_RESULT, TOKYO_RESULT])
        result = geocode_place("Berlin")
        assert result["name"] == "Berlin"

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_missing_timezone_defaults_to_empty_string(self, mock_urlopen):
        no_tz = {**BERLIN_RESULT, "timezone": None}
        mock_urlopen.return_value = _mock_response([no_tz])
        result = geocode_place("Berlin")
        assert result["timezone"] == ""

    @patch("bazi_engine.services.geocoding.urlopen")
    def test_none_results_key_raises(self, mock_urlopen):
        body = json.dumps({"results": None}).encode()
        m = MagicMock()
        m.read.return_value = body
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = m
        with pytest.raises(ValueError):
            geocode_place("Nowhere")
