import os
import sys
from pathlib import Path

import pytest

# Ensure repository root is importable when running pytest without installation.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _se1_files_available() -> bool:
    """Check if Swiss Ephemeris SE1 files are available."""
    from bazi_engine.ephemeris import EPHEMERIS_FILES_REQUIRED, _resolve_ephe_path
    path = _resolve_ephe_path(None)
    return all((path / name).exists() for name in EPHEMERIS_FILES_REQUIRED)


# If SE1 files are not present and EPHEMERIS_MODE is not explicitly set,
# default to MOSEPH for the test suite.  This preserves the pre-existing test
# behaviour (AUTO used to silently fall back) while production code now
# refuses to silently degrade.
if not os.environ.get("EPHEMERIS_MODE") and not _se1_files_available():
    os.environ["EPHEMERIS_MODE"] = "MOSEPH"


@pytest.fixture(autouse=True)
def clear_transit_caches():
    """Clear transit caches between tests to prevent order-dependent results."""
    from bazi_engine.transit import _transit_cache, _timeline_cache
    _transit_cache.clear()
    _timeline_cache.clear()
    yield
    _transit_cache.clear()
    _timeline_cache.clear()


@pytest.fixture(autouse=True)
def clear_ephemeris_cache():
    """Clear ensure_ephemeris_files LRU cache between tests."""
    from bazi_engine.ephemeris import ensure_ephemeris_files
    ensure_ephemeris_files.cache_clear()
    yield
    ensure_ephemeris_files.cache_clear()
