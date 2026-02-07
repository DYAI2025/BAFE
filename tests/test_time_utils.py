"""Tests for time_utils.py - Time parsing and conversion utilities."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bazi_engine.time_utils import (
    LocalTimeError,
    parse_local_iso,
    lmt_tzinfo,
    to_chart_local,
    apply_day_boundary,
)


class TestLocalTimeError:
    """Tests for LocalTimeError exception."""

    def test_is_value_error(self):
        assert issubclass(LocalTimeError, ValueError)

    def test_can_raise(self):
        with pytest.raises(LocalTimeError):
            raise LocalTimeError("test error")

    def test_message_preserved(self):
        try:
            raise LocalTimeError("custom message")
        except LocalTimeError as e:
            assert "custom message" in str(e)


class TestParseLocalIso:
    """Tests for parse_local_iso function."""

    def test_valid_datetime_lenient(self):
        dt = parse_local_iso("2024-02-10T14:30:00", "Europe/Berlin", strict=False, fold=0)
        assert dt.year == 2024
        assert dt.month == 2
        assert dt.day == 10
        assert dt.hour == 14
        assert dt.minute == 30

    def test_valid_datetime_strict(self):
        dt = parse_local_iso("2024-02-10T14:30:00", "Europe/Berlin", strict=True, fold=0)
        assert dt.year == 2024

    def test_timezone_applied(self):
        dt = parse_local_iso("2024-02-10T14:30:00", "Europe/Berlin", strict=False, fold=0)
        assert dt.tzinfo is not None
        assert str(dt.tzinfo) == "Europe/Berlin"

    def test_different_timezones(self):
        dt_berlin = parse_local_iso("2024-02-10T14:30:00", "Europe/Berlin", strict=False, fold=0)
        dt_tokyo = parse_local_iso("2024-02-10T14:30:00", "Asia/Tokyo", strict=False, fold=0)
        # Same local time, different UTC
        assert dt_berlin.utcoffset() != dt_tokyo.utcoffset()

    def test_fold_parameter(self):
        # During DST fall-back, 2:30 AM occurs twice
        # fold=0 is first occurrence (DST), fold=1 is second (standard)
        dt_fold0 = parse_local_iso("2024-10-27T02:30:00", "Europe/Berlin", strict=False, fold=0)
        dt_fold1 = parse_local_iso("2024-10-27T02:30:00", "Europe/Berlin", strict=False, fold=1)
        assert dt_fold0.fold == 0
        assert dt_fold1.fold == 1

    def test_invalid_timezone_raises(self):
        with pytest.raises(Exception):  # ZoneInfo raises various exceptions
            parse_local_iso("2024-02-10T14:30:00", "Invalid/Timezone", strict=False, fold=0)

    def test_invalid_datetime_raises(self):
        with pytest.raises(ValueError):
            parse_local_iso("not-a-date", "Europe/Berlin", strict=False, fold=0)

    def test_nonexistent_time_strict_raises(self):
        # 2024-03-31 02:30 doesn't exist in Europe/Berlin (spring forward)
        with pytest.raises(LocalTimeError):
            parse_local_iso("2024-03-31T02:30:00", "Europe/Berlin", strict=True, fold=0)

    def test_nonexistent_time_lenient_passes(self):
        # Lenient mode should not raise
        dt = parse_local_iso("2024-03-31T02:30:00", "Europe/Berlin", strict=False, fold=0)
        assert dt is not None


class TestLmtTzinfo:
    """Tests for lmt_tzinfo function."""

    def test_prime_meridian(self):
        tz = lmt_tzinfo(0.0)
        assert tz.utcoffset(None) == timedelta(0)

    def test_berlin_longitude(self):
        # Berlin: 13.405° E → 13.405 * 4 = 53.62 minutes = ~54 min offset
        tz = lmt_tzinfo(13.405)
        offset = tz.utcoffset(None)
        assert offset.total_seconds() == pytest.approx(13.405 * 240, abs=1)

    def test_new_york_longitude(self):
        # New York: -74° W → -74 * 4 = -296 minutes
        tz = lmt_tzinfo(-74.0)
        offset = tz.utcoffset(None)
        assert offset.total_seconds() == pytest.approx(-74.0 * 240, abs=1)

    def test_180_degree(self):
        tz = lmt_tzinfo(180.0)
        offset = tz.utcoffset(None)
        # 180 * 240 = 43200 seconds = 12 hours
        assert offset.total_seconds() == 43200

    def test_negative_180_degree(self):
        tz = lmt_tzinfo(-180.0)
        offset = tz.utcoffset(None)
        assert offset.total_seconds() == -43200


class TestToChartLocal:
    """Tests for to_chart_local function."""

    def test_civil_time_unchanged(self):
        dt = datetime(2024, 2, 10, 14, 30, tzinfo=ZoneInfo("Europe/Berlin"))
        chart_local, birth_utc = to_chart_local(dt, 13.405, "CIVIL")
        assert chart_local == dt

    def test_civil_returns_utc(self):
        dt = datetime(2024, 2, 10, 14, 30, tzinfo=ZoneInfo("Europe/Berlin"))
        chart_local, birth_utc = to_chart_local(dt, 13.405, "CIVIL")
        assert birth_utc.tzinfo == timezone.utc

    def test_lmt_converts_to_local_mean_time(self):
        dt = datetime(2024, 2, 10, 14, 30, tzinfo=ZoneInfo("Europe/Berlin"))
        chart_local, birth_utc = to_chart_local(dt, 13.405, "LMT")
        # LMT should use longitude-based offset
        assert chart_local.tzinfo != dt.tzinfo

    def test_lmt_preserves_utc_instant(self):
        dt = datetime(2024, 2, 10, 14, 30, tzinfo=ZoneInfo("Europe/Berlin"))
        chart_local, birth_utc = to_chart_local(dt, 13.405, "LMT")
        # Both should represent the same instant in UTC
        assert chart_local.astimezone(timezone.utc) == birth_utc

    def test_case_insensitive(self):
        dt = datetime(2024, 2, 10, 14, 30, tzinfo=ZoneInfo("Europe/Berlin"))
        chart_lmt, _ = to_chart_local(dt, 13.405, "lmt")
        chart_LMT, _ = to_chart_local(dt, 13.405, "LMT")
        assert chart_lmt == chart_LMT


class TestApplyDayBoundary:
    """Tests for apply_day_boundary function."""

    def test_midnight_unchanged(self):
        dt = datetime(2024, 2, 10, 14, 30)
        result = apply_day_boundary(dt, "midnight")
        assert result == dt

    def test_zi_adds_one_hour(self):
        dt = datetime(2024, 2, 10, 14, 30)
        result = apply_day_boundary(dt, "zi")
        expected = datetime(2024, 2, 10, 15, 30)
        assert result == expected

    def test_zi_crosses_midnight(self):
        dt = datetime(2024, 2, 10, 23, 30)
        result = apply_day_boundary(dt, "zi")
        expected = datetime(2024, 2, 11, 0, 30)
        assert result == expected

    def test_case_insensitive(self):
        dt = datetime(2024, 2, 10, 14, 30)
        result_lower = apply_day_boundary(dt, "zi")
        result_upper = apply_day_boundary(dt, "ZI")
        # Both should add one hour (case insensitive)
        assert result_lower == result_upper

    def test_default_is_midnight(self):
        dt = datetime(2024, 2, 10, 14, 30)
        result = apply_day_boundary(dt, "anything_else")
        # Unknown value should not modify (treated as midnight)
        assert result == dt
