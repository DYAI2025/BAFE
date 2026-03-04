from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal, Optional, Tuple

from .exc import InputError


class LocalTimeError(InputError, ValueError):
    """Raised for nonexistent or ambiguous local times (DST edge cases).

    Inherits from both InputError (→ HTTP 422 via global handler) and
    ValueError for backwards compatibility with code that catches ValueError.
    """
    http_status = 422
    error_code = "dst_time_error"

    def __init__(self, message: str, **kwargs: object) -> None:  # type: ignore[override]
        # InputError expects keyword-only 'detail'; ValueError expects positional.
        InputError.__init__(self, message)
        ValueError.__init__(self, message)

NonexistentTimePolicy = Literal["error", "shift_forward"]
AmbiguousTimeChoice = Literal["earlier", "later"]
LocalTimeStatus = Literal["ok", "ambiguous", "nonexistent_shifted"]


@dataclass(frozen=True)
class LocalTimeResolution:
    tz: str
    status: LocalTimeStatus
    fold: int
    input_local_iso: str
    resolved_local_iso: str
    resolved_utc_iso: str
    tz_abbrev: Optional[str] = None
    adjusted_minutes: int = 0
    warning: Optional[str] = None


def _roundtrip_ok(naive_local: datetime, tz: ZoneInfo, fold: int) -> bool:
    dt = naive_local.replace(tzinfo=tz, fold=fold)
    back = dt.astimezone(timezone.utc).astimezone(tz)
    return back.replace(tzinfo=None) == naive_local


def resolve_local_iso(
    birth_local_iso: str,
    tz_name: str,
    *,
    ambiguous: AmbiguousTimeChoice = "earlier",
    nonexistent: NonexistentTimePolicy = "error",
) -> Tuple[datetime, LocalTimeResolution]:
    """Resolve local ISO time with explicit DST handling.

    - Ambiguous times (DST fall-back): choose ``earlier`` (fold=0) or ``later`` (fold=1).
    - Nonexistent times (DST spring-forward gap):
        ``error``: raise LocalTimeError (default).
        ``shift_forward``: advance minute-by-minute to the next valid local time.
    """
    try:
        naive = datetime.fromisoformat(birth_local_iso)
    except ValueError as e:
        raise LocalTimeError(
            f"Invalid date/time format: '{birth_local_iso}'. Expected ISO 8601 (e.g. '2024-02-10T14:30:00').",
        ) from e
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError) as e:
        raise LocalTimeError(
            f"Unknown timezone: '{tz_name}'. Use an IANA timezone name (e.g. 'Europe/Berlin').",
        ) from e

    ok0 = _roundtrip_ok(naive, tz, fold=0)
    ok1 = _roundtrip_ok(naive, tz, fold=1)

    dt0 = naive.replace(tzinfo=tz, fold=0)
    dt1 = naive.replace(tzinfo=tz, fold=1)
    is_ambiguous = ok0 and ok1 and dt0.utcoffset() != dt1.utcoffset()
    is_nonexistent = (not ok0) and (not ok1)

    chosen_fold = 0 if ambiguous == "earlier" else 1

    if is_nonexistent:
        if nonexistent == "error":
            raise LocalTimeError(
                f"Nonexistent local time due to DST transition: {birth_local_iso} in {tz_name}. "
                "Provide a valid time or set nonexistentTime='shift_forward'."
            )
        # Shift forward to next valid minute (DST gaps are typically 30-60 min).
        for minutes in range(1, 181):
            candidate = naive + timedelta(minutes=minutes)
            if _roundtrip_ok(candidate, tz, fold=0) or _roundtrip_ok(candidate, tz, fold=1):
                dt = candidate.replace(tzinfo=tz, fold=0)
                return dt, LocalTimeResolution(
                    tz=tz_name,
                    status="nonexistent_shifted",
                    fold=0,
                    input_local_iso=birth_local_iso,
                    resolved_local_iso=dt.isoformat(),
                    resolved_utc_iso=dt.astimezone(timezone.utc).isoformat(),
                    tz_abbrev=dt.tzname(),
                    adjusted_minutes=minutes,
                    warning=f"Input local time did not exist (DST gap). "
                            f"Shifted forward by {minutes} min to {dt.isoformat()}.",
                )
        raise LocalTimeError(
            f"Could not resolve nonexistent time within 180 minutes: "
            f"{birth_local_iso} in {tz_name}."
        )

    # Normal or ambiguous
    dt = naive.replace(tzinfo=tz, fold=chosen_fold)
    status: LocalTimeStatus = "ambiguous" if is_ambiguous else "ok"
    warning = None
    if is_ambiguous:
        warning = (
            f"Ambiguous local time during DST fall-back. "
            f"Chosen: {ambiguous} (fold={chosen_fold}, offset={dt.utcoffset()})."
        )
    return dt, LocalTimeResolution(
        tz=tz_name,
        status=status,
        fold=chosen_fold,
        input_local_iso=birth_local_iso,
        resolved_local_iso=dt.isoformat(),
        resolved_utc_iso=dt.astimezone(timezone.utc).isoformat(),
        tz_abbrev=dt.tzname(),
        warning=warning,
    )


def parse_local_iso(birth_local_iso: str, tz_name: str, *, strict: bool, fold: int) -> datetime:
    try:
        naive = datetime.fromisoformat(birth_local_iso)
    except ValueError as e:
        raise LocalTimeError(
            f"Invalid date/time format: '{birth_local_iso}'. Expected ISO 8601 (e.g. '2024-02-10T14:30:00').",
        ) from e
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError) as e:
        raise LocalTimeError(
            f"Unknown timezone: '{tz_name}'. Use an IANA timezone name (e.g. 'Europe/Berlin').",
        ) from e
    dt = naive.replace(tzinfo=tz, fold=fold)

    if not strict:
        return dt

    # Round-trip check local -> utc -> local
    utc = dt.astimezone(timezone.utc)
    back = utc.astimezone(tz)

    if back.replace(tzinfo=None) != naive:
        raise LocalTimeError(
            f"Nonexistent or normalized local time for zone {tz_name}: {birth_local_iso}. "
            f"Round-trip became {back.isoformat()} (fold={back.fold})."
        )
    return dt

def lmt_tzinfo(longitude_deg: float) -> timezone:
    return timezone(timedelta(seconds=longitude_deg * 240.0))

def to_chart_local(birth_local: datetime, longitude_deg: float, time_standard: str) -> Tuple[datetime, datetime]:
    birth_utc = birth_local.astimezone(timezone.utc)
    if time_standard.upper() == "LMT":
        return birth_utc.astimezone(lmt_tzinfo(longitude_deg)), birth_utc
    return birth_local, birth_utc

def apply_day_boundary(dt_local: datetime, day_boundary: str) -> datetime:
    if day_boundary.lower() == "zi":
        return dt_local + timedelta(hours=1)
    return dt_local
