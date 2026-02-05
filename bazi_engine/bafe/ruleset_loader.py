from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def _repo_root_from_here() -> Path:
    # bazi_engine/bafe/ruleset_loader.py -> bazi_engine -> repo root
    here = Path(__file__).resolve()
    return here.parents[2]

def _spec_rulesets_dir() -> Path:
    return _repo_root_from_here() / "spec" / "rulesets"

def load_ruleset(ruleset_id: str) -> Dict[str, Any]:
    # Canonical mapping: id -> filename
    filename = f"{ruleset_id}.json"
    path = _spec_rulesets_dir() / filename
    if not path.exists():
        raise FileNotFoundError(f"Ruleset not found: {ruleset_id} ({path})")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("ruleset_id") != ruleset_id:
        raise ValueError("Ruleset id mismatch in file")
    return data

def ruleset_version(ruleset: Dict[str, Any]) -> str:
    return str(ruleset.get("ruleset_version", "MISSING"))

def branch_order(ruleset: Dict[str, Any]) -> List[str]:
    bo = ruleset.get("branch_order")
    if not isinstance(bo, list) or len(bo) != 12:
        raise ValueError("ruleset.branch_order must be a 12-item list")
    return [str(x) for x in bo]

def hidden_stems_for_branch(ruleset: Dict[str, Any], branch: str) -> List[str]:
    hs = ruleset.get("hidden_stems", {})
    mapping = hs.get("branch_to_hidden", {})
    if branch not in mapping:
        raise KeyError(f"hidden stems missing for branch: {branch}")
    lst = mapping[branch]
    if not isinstance(lst, list):
        raise TypeError("hidden stems entry must be a list")
    return [str(x) for x in lst]

def day_cycle_anchor_status(ruleset: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """
    Returns (anchor_jdn, anchor_verification).
    anchor_jdn may be None if missing.
    """
    anchor = ruleset.get("day_cycle_anchor", {})
    jdn = anchor.get("anchor_jdn", None)
    verification = str(anchor.get("anchor_verification", "MISSING"))
    if isinstance(jdn, int):
        return jdn, verification
    if isinstance(jdn, float) and jdn.is_integer():
        return int(jdn), verification
    return None, verification
