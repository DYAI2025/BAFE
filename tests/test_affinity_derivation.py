"""Tests fuer das Affinity Derivation Tool."""

import pytest
from tools.sector_vad import SECTOR_VAD, VADProfile
from tools.affinity_math import cosine_similarity, compute_affinity_row, compare_rows


class TestCosineSimilarity:
    def test_identical_profiles(self):
        a = VADProfile(0.5, 0.8, 0.3)
        assert cosine_similarity(a, a) == pytest.approx(1.0, abs=0.001)

    def test_orthogonal_profiles(self):
        a = VADProfile(1.0, 0.0, 0.0)
        b = VADProfile(0.0, 1.0, 0.0)
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=0.001)

    def test_opposite_valence(self):
        a = VADProfile(+0.8, 0.5, 0.5)
        b = VADProfile(-0.8, 0.5, 0.5)
        # Nicht perfekt gegensaetzlich wegen A und D Ueberlapp
        sim = cosine_similarity(a, b)
        assert sim < 0.5  # Aber niedrig

    def test_zero_vector(self):
        a = VADProfile(0.0, 0.0, 0.0)
        b = VADProfile(0.5, 0.5, 0.5)
        assert cosine_similarity(a, b) == 0.0


class TestComputeAffinityRow:
    def test_sum_approximately_one(self):
        vad = VADProfile(0.3, 0.7, 0.5)
        row = compute_affinity_row(vad)
        assert sum(row) == pytest.approx(1.0, abs=0.05)

    def test_all_non_negative(self):
        vad = VADProfile(-0.5, 0.9, 0.8)
        row = compute_affinity_row(vad)
        assert all(v >= 0 for v in row)

    def test_twelve_elements(self):
        vad = VADProfile(0.1, 0.5, 0.5)
        row = compute_affinity_row(vad)
        assert len(row) == 12

    def test_scorpio_affinity_for_dark_intense(self):
        """Negativ, hoch-aktiviert, dominant -> muss S7 (Skorpion) treffen."""
        vad = VADProfile(valence=-0.4, arousal=0.85, dominance=0.8)
        row = compute_affinity_row(vad)
        # S7 (Skorpion) hat exakt dieses Profil
        assert row[7] == max(row), f"S7 sollte Peak sein, ist aber {row}"

    def test_pisces_affinity_for_soft_submissive(self):
        """Mild positiv, niedrig-aktiviert, sehr submissiv -> S11 (Fische)."""
        vad = VADProfile(valence=+0.1, arousal=0.2, dominance=0.1)
        row = compute_affinity_row(vad)
        assert row[11] == max(row), f"S11 sollte Peak sein, ist aber {row}"

    def test_aries_affinity_for_impulsive_dominant(self):
        """Positiv, hoch-aktiviert, sehr dominant -> S0 (Widder) oder S4 (Loewe)."""
        vad = VADProfile(valence=+0.3, arousal=0.9, dominance=0.9)
        row = compute_affinity_row(vad)
        # S0 und S4 haben aehnliches Profil, einer muss Top-2 sein
        top2 = sorted(range(12), key=lambda s: row[s], reverse=True)[:2]
        assert 0 in top2 or 4 in top2, f"S0 oder S4 sollte Top-2 sein: {row}"


class TestCompareRows:
    def test_identical_is_coherent(self):
        a = [0.1] * 12
        result = compare_rows(a, a)
        assert result["coherent"] is True
        assert result["max_delta"] == 0.0

    def test_large_delta_is_mismatch(self):
        a = [0.5] + [0.05] * 11
        b = [0.0] + [0.05] * 11
        result = compare_rows(a, b, threshold=0.15)
        assert result["coherent"] is False
        assert result["max_delta_sector"] == 0


class TestSectorVADConsistency:
    def test_all_twelve_sectors_defined(self):
        assert len(SECTOR_VAD) == 12

    def test_valence_range(self):
        for s, vad in SECTOR_VAD.items():
            assert -1.0 <= vad.valence <= 1.0, f"S{s} valence out of range"

    def test_arousal_range(self):
        for s, vad in SECTOR_VAD.items():
            assert 0.0 <= vad.arousal <= 1.0, f"S{s} arousal out of range"

    def test_dominance_range(self):
        for s, vad in SECTOR_VAD.items():
            assert 0.0 <= vad.dominance <= 1.0, f"S{s} dominance out of range"

    def test_scorpio_is_negative_valence(self):
        assert SECTOR_VAD[7].valence < 0, "Skorpion muss negativ-valence sein"

    def test_pisces_is_low_dominance(self):
        assert SECTOR_VAD[11].dominance <= 0.2, "Fische muss niedrig-dominant sein"

    def test_aries_is_high_arousal(self):
        assert SECTOR_VAD[0].arousal >= 0.8, "Widder muss hoch-aktiviert sein"
