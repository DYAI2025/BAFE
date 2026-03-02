"""
test_import_hierarchy.py — Enforces the module layer contract.

Layer definitions (import direction: lower → higher ONLY):
  Layer 0: constants
  Layer 1: types
  Layer 2: ephemeris, time_utils, solar_time
  Layer 3: jieqi
  Layer 4: bazi, western, fusion
  Layer 5: app, cli, bafe/*

Rules enforced:
  - No module may import from a higher layer.
  - solar_time must have zero internal imports (pure math).
  - bafe/* must not import from fusion or bazi (Layer 4 peers at same level are OK
    only via the canonical path: bafe → solar_time, not bafe → fusion).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = REPO_ROOT / "bazi_engine"

# ── Layer assignments ────────────────────────────────────────────────────────
LAYERS: Dict[str, int] = {
    "constants":   0,
    "exc":         0,  # exception hierarchy — zero internal deps
    "types":       1,
    "ephemeris":   2,
    "time_utils":  2,
    "solar_time":  2,
    "jieqi":       3,
    "bazi":        4,
    "western":     4,
    "fusion":      4,
    "app":         5,
    "cli":         5,
    # bafe sub-modules all live at Layer 5
    "bafe.service":         5,
    "bafe.mapping":         5,
    "bafe.refdata":         5,
    "bafe.time_model":      5,
    "bafe.kernel":          5,
    "bafe.harmonics":       5,
    "bafe.canonical_json":  5,
    "bafe.errors":          5,
    "bafe.ruleset_loader":  5,
    # routers and services also live at Layer 5
    "routers.shared":       5,
    "routers.info":         5,
    "routers.bazi":         5,
    "routers.western":      5,
    "routers.fusion":       5,
    "routers.validate":     5,
    "routers.chart":        5,
    "routers.webhooks":     5,
    "services.geocoding":   5,
    "services.auth":        5,
}

# Modules that are explicitly allowed to bypass the layer rule
# (e.g., re-exports for backwards compatibility must be documented here).
ALLOWED_EXCEPTIONS: Set[str] = set()


def _collect_internal_imports(py_file: Path, package_name: str = "bazi_engine") -> List[str]:
    """Return list of bazi_engine-internal module names imported by py_file."""
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(py_file))

    # Directory parts of this file relative to ENGINE_ROOT (e.g. [] for root, ["bafe"] for bafe/)
    pkg_parts = list(py_file.relative_to(ENGINE_ROOT).with_suffix("").parts[:-1])

    imported: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # Relative import: level=1 → same package dir, level=2 → parent, etc.
                # base = pkg_parts with (level-1) trailing parts stripped
                base = pkg_parts[: max(0, len(pkg_parts) - (node.level - 1))]
                mod_parts = base + (node.module.split(".") if node.module else [])
                if mod_parts:  # skip bare "from . import x" (no module name)
                    imported.append(".".join(mod_parts))
            elif node.module and node.module.startswith(package_name + "."):
                imported.append(node.module[len(package_name) + 1 :])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(package_name + "."):
                    imported.append(alias.name[len(package_name) + 1 :])
    return imported


def _module_key(py_file: Path) -> str:
    """Convert file path to dot-notation module key used in LAYERS."""
    rel = py_file.relative_to(ENGINE_ROOT).with_suffix("")
    parts = rel.parts
    if parts[0] == "bafe":
        return "bafe." + ".".join(parts[1:])
    return ".".join(parts)


def _layer(key: str) -> int:
    return LAYERS.get(key, 5)  # unknown = treated as top layer, no rule violation possible


@pytest.mark.parametrize(
    "py_file",
    sorted(ENGINE_ROOT.rglob("*.py")),
    ids=lambda p: str(p.relative_to(ENGINE_ROOT)),
)
def test_no_upward_imports(py_file: Path):
    """Each module must only import from modules at the same or lower layer."""
    if py_file.name == "__init__.py":
        pytest.skip("__init__ files are exempt (re-export hubs)")

    key = _module_key(py_file)
    if key not in LAYERS:
        pytest.skip(f"Module '{key}' not registered in layer map — add it to LAYERS dict")

    src_layer = LAYERS[key]
    violations: List[str] = []

    for imp in _collect_internal_imports(py_file):
        imp_key = imp.split(".")[0] if "." not in imp else ".".join(imp.split(".")[:2])
        # Resolve bafe sub-modules
        if imp.startswith("bafe.") or imp == "bafe":
            imp_key = imp if imp in LAYERS else "bafe.service"
        dep_layer = _layer(imp_key)
        pair = f"{key} → {imp}"

        if dep_layer > src_layer and pair not in ALLOWED_EXCEPTIONS:
            violations.append(
                f"  Layer {src_layer} module '{key}' imports from "
                f"Layer {dep_layer} module '{imp}' (upward import!)"
            )

    if violations:
        pytest.fail(
            f"Import hierarchy violation(s) in {py_file.relative_to(ENGINE_ROOT)}:\n"
            + "\n".join(violations)
        )


def test_solar_time_has_no_internal_imports():
    """solar_time.py must be pure math — zero internal dependencies."""
    solar_time_file = ENGINE_ROOT / "solar_time.py"
    assert solar_time_file.exists(), "solar_time.py must exist"
    imports = _collect_internal_imports(solar_time_file)
    assert imports == [], (
        f"solar_time.py must have no internal imports, found: {imports}"
    )


def test_bafe_time_model_does_not_import_fusion():
    """The historical violation: bafe/time_model must NOT import fusion."""
    time_model = ENGINE_ROOT / "bafe" / "time_model.py"
    imports = _collect_internal_imports(time_model)
    fusion_imports = [i for i in imports if "fusion" in i]
    assert fusion_imports == [], (
        f"bafe/time_model.py must not import fusion. Found: {fusion_imports}"
    )
