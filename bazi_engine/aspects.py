"""
aspects.py — Planetary aspect calculations.

Computes angular aspects (conjunction, opposition, trine, square, sextile)
between all planet pairs. Pure function, no side effects.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Aspect definitions: (name, exact_angle, default_orb)
# Orb values are also documented in provenance.WUXING_PARAMETER_SET["aspect_orbs"]
ASPECT_DEFS: List[Tuple[str, float, float]] = [
    ("conjunction", 0.0, 8.0),
    ("sextile", 60.0, 6.0),
    ("square", 90.0, 7.0),
    ("trine", 120.0, 8.0),
    ("opposition", 180.0, 8.0),
]

# Major planets for aspect calculation
ASPECT_PLANETS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
]


def _angular_distance(lon1: float, lon2: float) -> float:
    """Shortest angular distance between two ecliptic longitudes."""
    diff = abs(lon1 - lon2) % 360
    return min(diff, 360 - diff)


def compute_aspects(
    bodies: Dict[str, Dict[str, Any]],
    planets: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Compute aspects between all planet pairs.

    Args:
        bodies: Dict of planet name -> {longitude, ...}
        planets: Which planets to include (default: ASPECT_PLANETS)

    Returns:
        List of aspect dicts: {planet1, planet2, type, angle, orb, exact_angle}
    """
    if planets is None:
        planets = [
            p for p in ASPECT_PLANETS
            if p in bodies and "longitude" in bodies[p] and bodies[p]["longitude"] is not None
        ]

    aspects: List[Dict[str, Any]] = []

    for i, p1 in enumerate(planets):
        for p2 in planets[i + 1:]:
            lon1 = bodies[p1]["longitude"]
            lon2 = bodies[p2]["longitude"]
            dist = _angular_distance(lon1, lon2)

            for name, exact, orb in ASPECT_DEFS:
                deviation = abs(dist - exact)
                if deviation <= orb:
                    aspects.append({
                        "planet1": p1,
                        "planet2": p2,
                        "type": name,
                        "angle": round(dist, 2),
                        "orb": round(deviation, 2),
                        "exact_angle": exact,
                    })
                    break  # one aspect per pair

    # Sort by tightest orb first
    aspects.sort(key=lambda a: a["orb"])
    return aspects
