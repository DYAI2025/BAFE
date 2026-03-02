"""
test_integration_fusion.py — End-to-end integration tests for compute_fusion_analysis()

These tests exercise the full pipeline:
  planetary positions → WuXingVector → harmony index → interpretation text

No HTTP, no ephemeris files needed. Uses fixed synthetic planetary data.

Integration assertions cover:
  - Output schema completeness
  - Mathematical consistency (vectors sum to > 0, harmony in [0,1])
  - Determinism (same input → same output)
  - Known reference cases (pure Fire vs pure Water → low harmony)
  - Text generation non-empty and harmony-consistent
"""
from __future__ import annotations

import pytest
from math import isclose
from datetime import datetime, timezone

from bazi_engine.fusion import compute_fusion_analysis, generate_fusion_interpretation
from bazi_engine.wuxing.vector import WuXingVector
from bazi_engine.wuxing.analysis import interpret_harmony

# ── Fixtures ─────────────────────────────────────────────────────────────────

BIRTH_UTC = datetime(2024, 2, 10, 13, 30, tzinfo=timezone.utc)

# Realistic western chart snapshot (no actual ephemeris needed)
WESTERN_BODIES_AQUARIUS = {
    "Sun":    {"longitude": 321.5, "is_retrograde": False, "zodiac_sign": 10},  # Aquarius → Fire
    "Moon":   {"longitude":  45.2, "is_retrograde": False, "zodiac_sign":  1},  # Taurus → Earth/Metal
    "Mercury":{"longitude": 305.1, "is_retrograde": True,  "zodiac_sign":  9},  # Capricorn → Earth (retro)
    "Venus":  {"longitude": 310.0, "is_retrograde": False, "zodiac_sign":  9},  # Metal
    "Mars":   {"longitude": 150.0, "is_retrograde": False, "zodiac_sign":  4},  # Fire
    "Jupiter":{"longitude":  60.0, "is_retrograde": False, "zodiac_sign":  2},  # Wood
    "Saturn": {"longitude": 340.0, "is_retrograde": False, "zodiac_sign": 10},  # Earth
}

BAZI_PILLARS_STANDARD = {
    "year":  {"stem": "Jia",  "branch": "Chen"},  # Wood / Earth
    "month": {"stem": "Bing", "branch": "Yin"},   # Fire  / Wood
    "day":   {"stem": "Jia",  "branch": "Chen"},  # Wood / Earth
    "hour":  {"stem": "Xin",  "branch": "Wei"},   # Metal / Earth
}

# Pure-element bodies for edge-case testing
BODIES_PURE_FIRE = {
    "Sun":  {"longitude": 0.0,   "is_retrograde": False},
    "Mars": {"longitude": 90.0,  "is_retrograde": False},
    "Pluto":{"longitude": 180.0, "is_retrograde": False},
}

BODIES_PURE_WATER = {
    "Moon":    {"longitude": 0.0,  "is_retrograde": False},
    "Neptune": {"longitude": 90.0, "is_retrograde": False},
    "Chiron":  {"longitude": 180.0,"is_retrograde": False},
}

PILLARS_PURE_WOOD = {
    "year":  {"stem": "Jia", "branch": "Mao"},  # Wood/Wood
    "month": {"stem": "Yi",  "branch": "Yin"},  # Wood/Wood
    "day":   {"stem": "Jia", "branch": "Mao"},
    "hour":  {"stem": "Yi",  "branch": "Yin"},
}

PILLARS_PURE_METAL = {
    "year":  {"stem": "Geng", "branch": "You"},  # Metal/Metal
    "month": {"stem": "Xin",  "branch": "You"},
    "day":   {"stem": "Geng", "branch": "Shen"},
    "hour":  {"stem": "Xin",  "branch": "You"},
}


# ── Schema / structure tests ──────────────────────────────────────────────────

class TestFusionOutputSchema:
    def setup_method(self):
        self.result = compute_fusion_analysis(
            birth_utc_dt=BIRTH_UTC,
            latitude=52.52,
            longitude=13.405,
            bazi_pillars=BAZI_PILLARS_STANDARD,
            western_bodies=WESTERN_BODIES_AQUARIUS,
        )

    def test_top_level_keys_present(self):
        expected = {
            "wu_xing_vectors", "harmony_index",
            "elemental_comparison", "cosmic_state", "fusion_interpretation",
        }
        assert expected <= self.result.keys()

    def test_wu_xing_vectors_has_two_sub_keys(self):
        vecs = self.result["wu_xing_vectors"]
        assert "western_planets" in vecs
        assert "bazi_pillars" in vecs

    def test_wu_xing_each_vector_has_five_elements(self):
        vecs = self.result["wu_xing_vectors"]
        for key in ("western_planets", "bazi_pillars"):
            assert len(vecs[key]) == 5, f"{key} should have 5 elements"

    def test_wu_xing_element_keys_are_german(self):
        for key in ("western_planets", "bazi_pillars"):
            assert set(self.result["wu_xing_vectors"][key].keys()) == {
                "Holz", "Feuer", "Erde", "Metall", "Wasser"
            }

    def test_harmony_index_structure(self):
        h = self.result["harmony_index"]
        assert "harmony_index" in h
        assert "interpretation" in h

    def test_elemental_comparison_has_five_elements(self):
        comp = self.result["elemental_comparison"]
        assert len(comp) == 5

    def test_elemental_comparison_each_has_diff_keys(self):
        for elem, data in self.result["elemental_comparison"].items():
            assert {"western", "bazi", "difference"} <= data.keys()

    def test_cosmic_state_is_float(self):
        assert isinstance(self.result["cosmic_state"], float)

    def test_fusion_interpretation_is_non_empty_string(self):
        interp = self.result["fusion_interpretation"]
        assert isinstance(interp, str)
        assert len(interp) > 10


# ── Mathematical invariants ───────────────────────────────────────────────────

class TestFusionMathInvariants:
    def _run(self, western, pillars):
        return compute_fusion_analysis(
            birth_utc_dt=BIRTH_UTC,
            latitude=52.52,
            longitude=13.405,
            bazi_pillars=pillars,
            western_bodies=western,
        )

    def test_harmony_index_in_0_1(self):
        result = self._run(WESTERN_BODIES_AQUARIUS, BAZI_PILLARS_STANDARD)
        h = result["harmony_index"]["harmony_index"]
        assert 0.0 <= h <= 1.0

    def test_cosmic_state_in_0_1(self):
        result = self._run(WESTERN_BODIES_AQUARIUS, BAZI_PILLARS_STANDARD)
        assert 0.0 <= result["cosmic_state"] <= 1.0

    def test_elemental_difference_equals_western_minus_bazi(self):
        result = self._run(WESTERN_BODIES_AQUARIUS, BAZI_PILLARS_STANDARD)
        vecs = result["wu_xing_vectors"]
        comp = result["elemental_comparison"]
        for elem in ("Holz", "Feuer", "Erde", "Metall", "Wasser"):
            expected_diff = round(vecs["western_planets"][elem] - vecs["bazi_pillars"][elem], 3)
            assert isclose(comp[elem]["difference"], expected_diff, abs_tol=1e-6), (
                f"{elem}: diff={comp[elem]['difference']}, expected={expected_diff}"
            )

    def test_normalized_vectors_have_l2_norm_1(self):
        """wu_xing_vectors stores L2-normalized unit vectors (‖v‖₂ = 1)."""
        from math import sqrt
        result = self._run(WESTERN_BODIES_AQUARIUS, BAZI_PILLARS_STANDARD)
        for key in ("western_planets", "bazi_pillars"):
            values = list(result["wu_xing_vectors"][key].values())
            l2 = sqrt(sum(x ** 2 for x in values))
            assert isclose(l2, 1.0, abs_tol=1e-6), f"{key} L2 norm={l2}, expected 1.0"

    def test_determinism_same_input_same_output(self):
        r1 = self._run(WESTERN_BODIES_AQUARIUS, BAZI_PILLARS_STANDARD)
        r2 = self._run(WESTERN_BODIES_AQUARIUS, BAZI_PILLARS_STANDARD)
        assert r1["harmony_index"]["harmony_index"] == r2["harmony_index"]["harmony_index"]
        assert r1["cosmic_state"] == r2["cosmic_state"]
        assert r1["fusion_interpretation"] == r2["fusion_interpretation"]

    def test_pure_fire_vs_pure_water_low_harmony(self):
        """Sun+Mars+Pluto (Fire) vs Water pillars → orthogonal → low harmony."""
        result = self._run(BODIES_PURE_FIRE, {
            "year": {"stem": "Ren", "branch": "Zi"},
            "month": {"stem": "Gui", "branch": "Hai"},
            "day": {"stem": "Ren", "branch": "Zi"},
            "hour": {"stem": "Gui", "branch": "Hai"},
        })
        h = result["harmony_index"]["harmony_index"]
        assert h < 0.3, f"Fire vs Water should have low harmony, got {h}"

    def test_same_element_profile_high_harmony(self):
        """Same bodies for both systems → perfect harmony."""
        # Use same planetary bodies for western, and pillars that map to same elements
        # Jia/Mao = pure Wood, Jupiter = Wood → high harmony
        result = self._run(
            {"Jupiter": {"longitude": 0.0, "is_retrograde": False}},
            PILLARS_PURE_WOOD,
        )
        h = result["harmony_index"]["harmony_index"]
        assert h > 0.7, f"Wood vs Wood should have high harmony, got {h}"


# ── Interpretation consistency ────────────────────────────────────────────────

class TestFusionInterpretationConsistency:
    def _run(self, western, pillars):
        return compute_fusion_analysis(
            birth_utc_dt=BIRTH_UTC,
            latitude=0.0, longitude=0.0,
            bazi_pillars=pillars,
            western_bodies=western,
        )

    def test_high_harmony_gets_positive_text(self):
        result = self._run(
            {"Jupiter": {"longitude": 0.0, "is_retrograde": False}},
            PILLARS_PURE_WOOD,
        )
        text = result["fusion_interpretation"]
        assert "starker Resonanz" in text or "harmonisch" in text or "Resonanz" in text

    def test_low_harmony_gets_tension_text(self):
        result = self._run(BODIES_PURE_FIRE, {
            "year": {"stem": "Ren", "branch": "Zi"},
            "month": {"stem": "Gui", "branch": "Hai"},
            "day": {"stem": "Ren", "branch": "Zi"},
            "hour": {"stem": "Gui", "branch": "Hai"},
        })
        text = result["fusion_interpretation"]
        assert "unterschiedliche Richtungen" in text or "Integration" in text

    def test_harmony_index_in_interpretation_text(self):
        result = self._run(WESTERN_BODIES_AQUARIUS, BAZI_PILLARS_STANDARD)
        text = result["fusion_interpretation"]
        assert "Harmonie-Index" in text

    def test_dominant_elements_mentioned(self):
        result = self._run(WESTERN_BODIES_AQUARIUS, BAZI_PILLARS_STANDARD)
        text = result["fusion_interpretation"]
        assert "Westliche Dominanz" in text
        assert "Östliche Dominanz" in text


# ── generate_fusion_interpretation standalone ─────────────────────────────────

class TestGenerateFusionInterpretation:
    def test_returns_string(self):
        v = WuXingVector(1.0, 1.0, 1.0, 1.0, 1.0)
        comp = {e: {"western": 0.2, "bazi": 0.2, "difference": 0.0}
                for e in ("Holz", "Feuer", "Erde", "Metall", "Wasser")}
        result = generate_fusion_interpretation(0.8, comp, v, v)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("h,fragment", [
        (0.8, "Resonanz"),
        (0.5, "Balance"),
        (0.1, "unterschiedliche Richtungen"),
    ])
    def test_harmony_level_reflected_in_text(self, h, fragment):
        v = WuXingVector(1.0, 0.0, 0.0, 0.0, 0.0)
        comp = {}
        result = generate_fusion_interpretation(h, comp, v, v)
        assert fragment in result, f"h={h}: expected '{fragment}' in text"


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestFusionEdgeCases:
    def test_empty_bodies_still_returns_result(self):
        """No planetary bodies → zero vector → result still valid dict."""
        result = compute_fusion_analysis(
            birth_utc_dt=BIRTH_UTC,
            latitude=0.0, longitude=0.0,
            bazi_pillars=BAZI_PILLARS_STANDARD,
            western_bodies={},
        )
        assert "harmony_index" in result
        assert "wu_xing_vectors" in result

    def test_all_error_bodies_treated_as_empty(self):
        bodies_with_errors = {
            "Sun":  {"error": "calc failed"},
            "Moon": {"error": "not found"},
        }
        result = compute_fusion_analysis(
            birth_utc_dt=BIRTH_UTC,
            latitude=0.0, longitude=0.0,
            bazi_pillars=BAZI_PILLARS_STANDARD,
            western_bodies=bodies_with_errors,
        )
        assert isinstance(result["cosmic_state"], float)

    def test_single_pillar_works(self):
        result = compute_fusion_analysis(
            birth_utc_dt=BIRTH_UTC,
            latitude=0.0, longitude=0.0,
            bazi_pillars={"year": {"stem": "Jia", "branch": "Zi"}},
            western_bodies=WESTERN_BODIES_AQUARIUS,
        )
        assert 0.0 <= result["harmony_index"]["harmony_index"] <= 1.0
