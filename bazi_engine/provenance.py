"""
provenance.py — Computation provenance metadata for Datenwahrheit.

Every /calculate/* response includes a provenance block documenting
which engine version, ephemeris, ruleset, and parameters produced the result.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from . import __version__


WUXING_PARAMETER_SET: Dict[str, Any] = {
    "version": "1.0.0",
    "retrograde_weight": 1.3,
    "hidden_stem_main_qi": 1.0,
    "hidden_stem_middle_qi": 0.5,
    "hidden_stem_residual_qi": 0.3,
    "stem_weight": 1.0,
    "mercury_dual_rule": "earth_day_metal_night",
    "harmony_method": "dot_product",
    "aspect_orbs": {
        "conjunction": 8.0,
        "sextile": 6.0,
        "square": 7.0,
        "trine": 8.0,
        "opposition": 8.0,
    },
}


HOUSE_SYSTEM_LABELS: Dict[str, str] = {
    "P": "placidus",
    "O": "porphyry",
    "W": "whole_sign",
}


def normalize_house_system(code: Optional[str]) -> str:
    """Map single-char house system code to stable label for provenance.

    ``compute_western_chart()`` returns ``"P"``, ``"O"``, or ``"W"``
    depending on latitude-driven fallback.  We normalise to a human-readable
    lowercase label so the provenance block is always consistent.
    """
    if code is None:
        return "unknown"
    return HOUSE_SYSTEM_LABELS.get(code, code.lower())


def _detect_tzdb_version() -> str:
    """Best-effort detection of the IANA tzdata version."""
    try:
        from importlib.metadata import version as pkg_version
        return pkg_version("tzdata")
    except Exception:
        pass
    try:
        import importlib.resources as ir
        tzdata = ir.files("tzdata")  # type: ignore[attr-defined]
        zi_dir = tzdata / "zoneinfo"
        tz_file = zi_dir / "tzdata.zi"
        if hasattr(tz_file, "read_text"):
            first_line = tz_file.read_text().split("\n", 1)[0]
            if first_line.startswith("# version"):
                return first_line.split()[-1]
    except Exception:
        pass
    return "unknown"


def _detect_ephemeris_id() -> str:
    """Identify the active ephemeris backend."""
    mode = os.environ.get("EPHEMERIS_MODE", "SWIEPH").upper()
    if mode == "MOSEPH":
        return "moshier_analytic"
    # Default: Swiss Ephemeris with sepl_18 data files
    return "swieph_sepl18"


# Cache at module load — env var won't change during server lifetime
_EPHEMERIS_ID: str = _detect_ephemeris_id()


@dataclass(frozen=True)
class Provenance:
    """Immutable provenance record attached to every /calculate/* response."""
    engine_version: str
    parameter_set_id: str
    ruleset_id: str
    ephemeris_id: str
    tzdb_version_id: str
    house_system: str
    zodiac_mode: str
    computation_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "parameter_set_id": self.parameter_set_id,
            "ruleset_id": self.ruleset_id,
            "ephemeris_id": self.ephemeris_id,
            "tzdb_version_id": self.tzdb_version_id,
            "house_system": self.house_system,
            "zodiac_mode": self.zodiac_mode,
            "computation_timestamp": self.computation_timestamp,
        }


def build_provenance(
    *,
    parameter_set_id: str = "default_v1",
    ruleset_id: str = "traditional_bazi_2026",
    house_system: str = "placidus",
    zodiac_mode: str = "tropical",
) -> Dict[str, Any]:
    """Build a provenance dict for inclusion in API responses.

    Parameters can be overridden per-endpoint when the request specifies
    a non-default house system or zodiac mode.
    """
    prov = Provenance(
        engine_version=__version__,
        parameter_set_id=parameter_set_id,
        ruleset_id=ruleset_id,
        ephemeris_id=_EPHEMERIS_ID,
        tzdb_version_id=_detect_tzdb_version(),
        house_system=house_system,
        zodiac_mode=zodiac_mode,
        computation_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    result = prov.to_dict()
    result["parameter_set"] = WUXING_PARAMETER_SET
    return result
