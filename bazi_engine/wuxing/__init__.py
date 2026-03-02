"""
bazi_engine/wuxing — Wu-Xing (Five Elements) domain package.

Re-exports everything for backwards compatibility with
``from bazi_engine.fusion import WuXingVector, PLANET_TO_WUXING, ...``
"""
from .constants import PLANET_TO_WUXING, WUXING_ORDER, WUXING_INDEX
from .vector import WuXingVector
from .analysis import (
    planet_to_wuxing,
    calculate_wuxing_vector_from_planets,
    is_night_chart,
    calculate_wuxing_from_bazi,
    calculate_harmony_index,
    interpret_harmony,
)

__all__ = [
    "PLANET_TO_WUXING",
    "WUXING_ORDER",
    "WUXING_INDEX",
    "WuXingVector",
    "planet_to_wuxing",
    "calculate_wuxing_vector_from_planets",
    "is_night_chart",
    "calculate_wuxing_from_bazi",
    "calculate_harmony_index",
    "interpret_harmony",
]
