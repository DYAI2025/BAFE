import sys
from pathlib import Path

import pytest

# Ensure repository root is importable when running pytest without installation.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def clear_transit_caches():
    """Clear transit caches between tests to prevent order-dependent results."""
    from bazi_engine.transit import _transit_cache, _timeline_cache
    _transit_cache.clear()
    _timeline_cache.clear()
    yield
    _transit_cache.clear()
    _timeline_cache.clear()
