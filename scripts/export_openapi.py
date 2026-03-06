#!/usr/bin/env python3
"""Export the current OpenAPI spec from the FastAPI app to spec/openapi/.

Usage:
    python scripts/export_openapi.py          # write JSON
    python scripts/export_openapi.py --check  # CI mode: fail if spec drifted
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "spec" / "openapi" / "openapi.json"


def _current_spec_json() -> str:
    # Inline import so the script works without activated venv in PATH
    sys.path.insert(0, str(ROOT))
    from bazi_engine.app import app
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    check_mode = "--check" in sys.argv
    fresh = _current_spec_json()

    if check_mode:
        if not SPEC_PATH.exists():
            print(f"FAIL: {SPEC_PATH} does not exist. Run: python scripts/export_openapi.py")
            sys.exit(1)
        existing = SPEC_PATH.read_text(encoding="utf-8")
        if existing != fresh:
            print("FAIL: OpenAPI spec drifted. Run: python scripts/export_openapi.py")
            sys.exit(1)
        print("OK: OpenAPI spec is up-to-date.")
    else:
        SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
        SPEC_PATH.write_text(fresh, encoding="utf-8")
        print(f"Written: {SPEC_PATH}")


if __name__ == "__main__":
    main()
