from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional, Protocol, Tuple
import os

import swisseph as swe

from .exc import EphemerisUnavailableError


def norm360(deg: float) -> float:
    x = deg % 360.0
    if x < 0:
        x += 360.0
    return x


def wrap180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def assert_no_moseph_fallback(requested_flags: int, returned_flags: int) -> None:
    """Raise EphemerisUnavailableError if Swiss Ephemeris silently fell back to Moshier.

    pyswisseph does NOT raise an error when SE1 files are missing -- it silently
    downgrades to the lower-precision Moshier analytical ephemeris and sets the
    FLG_MOSEPH bit in the returned flags.  For a B2B paid API this silent
    precision downgrade is unacceptable.

    Args:
        requested_flags: The flags passed TO swe.calc_ut / swe.calc.
        returned_flags:  The flags returned FROM swe.calc_ut / swe.calc.

    Raises:
        EphemerisUnavailableError: when MOSEPH was used but not requested.
    """
    requested_moseph = bool(requested_flags & swe.FLG_MOSEPH)
    used_moseph = bool(returned_flags & swe.FLG_MOSEPH)
    if used_moseph and not requested_moseph:
        raise EphemerisUnavailableError(
            "Swiss Ephemeris silently fell back to Moshier (lower precision). "
            "SE1 data files are missing or unreadable. "
            "Set SE_EPHE_PATH to a directory containing the required .se1 files.",
            detail={
                "requested_flags": requested_flags,
                "returned_flags": returned_flags,
            },
        )


class EphemerisBackend(Protocol):
    def delta_t_seconds(self, jd_ut: float) -> float: ...
    def jd_tt_from_jd_ut(self, jd_ut: float) -> float: ...
    def sun_lon_deg_ut(self, jd_ut: float) -> float: ...
    def solcross_ut(self, target_lon_deg: float, jd_start_ut: float) -> Optional[float]: ...


@dataclass
class SwissEphBackend:
    flags: int = swe.FLG_SWIEPH
    ephe_path: Optional[str] = None
    mode: str = "SWIEPH"

    def __post_init__(self) -> None:
        mode = self.mode.upper()
        env_mode = os.environ.get("EPHEMERIS_MODE")
        if env_mode:
            mode = env_mode.upper()

        if mode not in {"SWIEPH", "MOSEPH"}:
            raise ValueError(
                f"Unsupported ephemeris mode: {mode!r}. "
                "Use 'SWIEPH' (default, high precision) or 'MOSEPH' (analytical fallback)."
            )

        if mode == "MOSEPH":
            self.flags = swe.FLG_MOSEPH
            self.mode = "MOSEPH"
            return

        # SWIEPH: require SE1 files -- never silently degrade.
        path = ensure_ephemeris_files(self.ephe_path)
        swe.set_ephe_path(path)
        self.flags = swe.FLG_SWIEPH
        self.mode = "SWIEPH"

    def delta_t_seconds(self, jd_ut: float) -> float:
        return swe.deltat(jd_ut) * 86400.0

    def jd_tt_from_jd_ut(self, jd_ut: float) -> float:
        return jd_ut + swe.deltat(jd_ut)

    def sun_lon_deg_ut(self, jd_ut: float) -> float:
        (lon, _lat, _dist, *_), ret = swe.calc_ut(jd_ut, swe.SUN, self.flags)
        assert_no_moseph_fallback(self.flags, ret)
        return norm360(lon)

    def solcross_ut(self, target_lon_deg: float, jd_start_ut: float) -> Optional[float]:
        return swe.solcross_ut(target_lon_deg, jd_start_ut, self.flags)

    def calc_ut(
        self, jd_ut: float, planet_id: int, extra_flags: int = 0,
    ) -> Tuple[Tuple[float, ...], int]:
        """Thin wrapper around swe.calc_ut with fallback detection.

        Returns the (result_tuple, flags) pair, raising
        EphemerisUnavailableError if MOSEPH was used unexpectedly.
        """
        combined = self.flags | extra_flags
        result, ret = swe.calc_ut(jd_ut, planet_id, combined)
        assert_no_moseph_fallback(combined, ret)
        return result, ret


def datetime_utc_to_jd_ut(dt_utc: datetime) -> float:
    if dt_utc.tzinfo is None or dt_utc.utcoffset() != timedelta(0):
        raise ValueError("Expected aware UTC datetime")
    h = dt_utc.hour + dt_utc.minute / 60.0 + (dt_utc.second + dt_utc.microsecond / 1e6) / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h)


def jd_ut_to_datetime_utc(jd_ut: float) -> datetime:
    y, m, d, h = swe.revjul(jd_ut)
    hour = int(h)
    rem = (h - hour) * 3600.0
    minute = int(rem // 60.0)
    sec = rem - minute * 60.0
    second = int(sec)
    micro = int(round((sec - second) * 1_000_000))
    if micro >= 1_000_000:
        micro -= 1_000_000
        second += 1
    if second >= 60:
        second -= 60
        minute += 1
    if minute >= 60:
        minute -= 60
        hour += 1
    base = datetime(y, m, d, 0, 0, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(hours=hour, minutes=minute, seconds=second, microseconds=micro)


EPHEMERIS_FILES_REQUIRED = [
    "sepl_18.se1",
    "semo_18.se1",
    "seas_18.se1",
    "seplm06.se1",
]


def _resolve_ephe_path(ephe_path: Optional[str]) -> Path:
    # Default to a user-writable cache path (no implicit downloads).
    if ephe_path:
        return Path(ephe_path)
    env = os.environ.get("SE_EPHE_PATH")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "bazi_engine" / "swisseph"


@lru_cache(maxsize=1)
def ensure_ephemeris_files(ephe_path: Optional[str] = None) -> str:
    """
    Ensure ephemeris files are present locally.

    Contract-first / offline-safe behavior:
    - NEVER downloads files.
    - Creates the directory if missing.
    - Raises EphemerisUnavailableError if required files are missing.
    """
    path = _resolve_ephe_path(ephe_path)
    path.mkdir(parents=True, exist_ok=True)
    missing = [name for name in EPHEMERIS_FILES_REQUIRED if not (path / name).exists()]
    if missing:
        raise EphemerisUnavailableError(
            "Swiss Ephemeris files missing. Provide them via SE_EPHE_PATH or ephe_path. "
            f"Missing: {missing}. Resolved path: {path}",
            detail={"missing_files": missing, "resolved_path": str(path)},
        )
    return str(path)
