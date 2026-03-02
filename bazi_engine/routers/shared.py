"""
routers/shared.py — Constants and helpers shared across routers.

Extracted from app.py to avoid duplication. Imported by individual routers.
"""
from __future__ import annotations

from typing import Dict
from ..types import Pillar
from ..constants import STEMS, BRANCHES

ZODIAC_SIGNS_DE = [
    "Widder", "Stier", "Zwillinge", "Krebs", "Löwe", "Jungfrau",
    "Waage", "Skorpion", "Schütze", "Steinbock", "Wassermann", "Fische",
]

STEM_TO_ELEMENT: Dict[str, str] = {
    "Jia": "Holz", "Yi": "Holz",
    "Bing": "Feuer", "Ding": "Feuer",
    "Wu": "Erde", "Ji": "Erde",
    "Geng": "Metall", "Xin": "Metall",
    "Ren": "Wasser", "Gui": "Wasser",
}

BRANCH_TO_ANIMAL: Dict[str, str] = {
    "Zi": "Ratte", "Chou": "Ochse", "Yin": "Tiger", "Mao": "Hase",
    "Chen": "Drache", "Si": "Schlange", "Wu": "Pferd", "Wei": "Ziege",
    "Shen": "Affe", "You": "Hahn", "Xu": "Hund", "Hai": "Schwein",
}


def format_pillar(pillar: Pillar) -> Dict[str, str]:
    stem = STEMS[pillar.stem_index]
    branch = BRANCHES[pillar.branch_index]
    return {
        "stamm": stem,
        "zweig": branch,
        "tier": BRANCH_TO_ANIMAL[branch],
        "element": STEM_TO_ELEMENT[stem],
    }
