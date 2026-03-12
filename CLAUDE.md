# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FuFirE — Fusion Firmament Engine** (v1.0.0-rc0) is a deterministic astronomical calculation engine for Chinese astrology (Four Pillars of Destiny / BaZi) with Western astrology integration. Calculates Year/Month/Day/Hour pillars based on precise solar-term boundaries using Swiss Ephemeris.

**Key Characteristics:**
- Deterministic: No randomness, purely astronomical calculations
- Immutable: All dataclasses use `frozen=True`
- Type-safe: Complete type hint coverage (Python 3.10+)
- Functional: Pure functions with no side effects
- Contract-first: JSON Schema (Draft-07) validation for `/validate` endpoint

## Development Commands

```bash
# Setup
python3.10 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -q                                     # Quick run
pytest -v                                     # Verbose
pytest tests/test_golden.py                   # Golden vectors only
pytest -k "test_name"                         # Pattern matching

# Lint & typecheck (CI uses these)
ruff check bazi_engine/ --output-format=github
mypy bazi_engine --ignore-missing-imports

# Start API server
uvicorn bazi_engine.app:app --reload

# CLI usage
python -m bazi_engine.cli 2024-02-10T14:30:00 --tz Europe/Berlin --lon 13.405 --lat 52.52
python -m bazi_engine.cli 2024-02-10T14:30:00 --json   # JSON output

# OpenAPI contract
python scripts/export_openapi.py              # Regenerate after endpoint changes
python scripts/export_openapi.py --check      # CI drift check

# Docker
docker build -t bazi_engine . && docker run -p 8080:8080 bazi_engine

# Deploy
flyctl deploy                                 # Fly.io (app: bafe-2u0e2a, region: ams)
```

## Architecture

### Module Hierarchy (import direction: top → bottom only)

```
Level 0: constants.py              # STEMS, BRANCHES, DAY_OFFSET=49
Level 1: types.py                  # Pillar, FourPillars, BaziInput, BaziResult (frozen)
         exc.py                    # BaziEngineError, EphemerisUnavailableError
Level 2: ephemeris.py              # SwissEphBackend, EphemerisBackend protocol
         time_utils.py             # parse_local_iso, LocalTimeError
         solar_time.py             # True Solar Time calculations
Level 3: jieqi.py                  # Solar term calculations, find_crossing() bisection
Level 4: bazi.py                   # compute_bazi() — main 9-step pipeline
         western.py                # compute_western_chart() — planetary positions
         fusion.py                 # Wu-Xing vectors, Harmony Index, equation of time
         transit.py                # Real-time planetary transit (TTLCache per hour)
         aspects.py                # Aspect calculations between planets
         narrative.py              # Text generation from transit state
         provenance.py             # Calculation provenance/audit trail
         wuxing/                   # Wu-Xing subpackage (constants, vector, analysis, calibration, zones)
         phases/                   # Lunar/Jieqi phase calculations
         research/                 # Dataset generator and pattern analysis
Level 5: app.py                    # FastAPI factory — mounts all routers
         cli.py                    # Command-line interface
         routers/                  # One router module per domain (see below)
         services/                 # auth.py, geocoding.py
         bafe/                     # Contract-first validation subpackage
```

**Critical Rule:** Lower-level modules must never import higher-level modules.

### Router Structure (`bazi_engine/routers/`)

`app.py` is now a thin factory that mounts routers — no business logic lives in it.

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| `bazi.py` | `/calculate` | `/calculate/bazi`, `/calculate/tst` |
| `western.py` | `/calculate` | `/calculate/western`, `/calculate/wuxing` |
| `fusion.py` | `/calculate` | `/calculate/fusion` |
| `transit.py` | `/transit` | `/transit/now`, `/transit/timeline`, `/transit/state`, `/transit/narrative` |
| `validate.py` | — | `/validate` |
| `chart.py` | — | `/api/chart` |
| `webhooks.py` | `/api/webhooks` | `/api/webhooks/chart` (ElevenLabs) |
| `info.py` | — | `/health`, `/api` |
| `shared.py` | — | Shared Pydantic models/deps |

### BAFE Subpackage (Contract-First Core)

`bazi_engine/bafe/` implements JSON Schema Draft-07 validation for `/validate`:
- `service.py` — Main `validate_request()` orchestrator
- `mapping.py` — Branch coordinate conventions (SHIFT_BOUNDARIES, SHIFT_LONGITUDES)
- `refdata.py` — Reference data policy checks
- `time_model.py` — Time evaluation
- `ruleset_loader.py` — Loads rulesets from `spec/rulesets/`
- `canonical_json.py` — Deterministic config fingerprints
- `kernel.py` — Soft branch weights
- `harmonics.py` — Harmonic analysis utilities
- `errors.py` — Contract-bound error codes and issue factory

Schemas: `spec/schemas/ValidateRequest.schema.json`, `ValidateResponse.schema.json`
Ruleset: `spec/rulesets/standard_bazi_2026.json`

### Wu-Xing Subpackage (`bazi_engine/wuxing/`)

Dedicated subpackage for Five Elements calculations:
- `constants.py` — Element constants and mappings
- `vector.py` — Wu-Xing vector computations
- `analysis.py` — Element balance analysis
- `calibration.py` — Calibration data
- `zones.py` — Zone-based analysis

## Critical Domain Concepts

### Year Boundary (LiChun)
- Year changes at 315° solar longitude (~Feb 3-5), not Jan 1
- Birth before LiChun uses previous year's pillar
- Timezone-sensitive: Berlin LiChun ≠ Beijing LiChun

### Day Pillar Calibration
```python
DAY_OFFSET = 49  # in constants.py — DO NOT MODIFY unless recalibrating
```
Formula: `sexagenary_day_index = (JDN + 49) % 60`

### DST Handling
- `LocalTimeError` raised for nonexistent/ambiguous times when `strict_local_time=True`
- Use `fold=0`/`fold=1` for ambiguous fall-back times
- Set `strict_local_time=False` for lenient mode

### Swiss Ephemeris
- Required files: sepl_18.se1, semo_18.se1, seplm06.se1
- Default path: `/usr/local/share/swisseph`
- Set via `SE_EPHE_PATH` env var or `ephe_path` parameter
- Error "SwissEph file not found" = missing ephemeris data
- Transit calculations use `TTLCache` (1-hour TTL) — `ADR-1`

## Testing

CI runs on Python 3.10, 3.11, 3.12. Tests skip gracefully if ephemeris files are missing.

Key test files beyond the basics:
- `test_golden.py`, `test_golden_vectors.py` — Pillar correctness
- `test_transit.py`, `test_transit_golden.py`, `test_transit_validation.py` — Transit API
- `test_wuxing_*.py` — Wu-Xing subpackage
- `test_aspects.py` — Aspect calculations
- `test_phases.py` — Lunar/Jieqi phases
- `test_snapshot_stability.py` — Snapshot regression
- `test_import_hierarchy.py` — Enforces module import rules
- `test_openapi_contract.py` — OpenAPI drift detection
- `test_rebrand.py` — FuFirE name consistency

## OpenAPI Contract

**`spec/openapi/openapi.json`** is the source of truth.
- CI checks for drift: `python scripts/export_openapi.py --check`
- Regenerate after any endpoint/model change: `python scripts/export_openapi.py`
- `bazi_engine.__version__` is the single source for version strings
- **Endpoints are frozen** — do not change paths or response structures (downstream services depend on them)

## Gotchas

1. **Circular imports:** Respect module hierarchy strictly (`test_import_hierarchy.py` enforces this)
2. **Immutability:** Never remove `frozen=True` from dataclasses
3. **DAY_OFFSET:** Changing breaks day pillar accuracy for all historical dates
4. **Router architecture:** Business logic belongs in domain modules, not in `routers/` or `app.py`
5. **DST:** Always handle `LocalTimeError` in API endpoints
6. **Ephemeris:** Tests skip without explicit `SE_EPHE_PATH` setup
7. **OpenAPI drift:** Run `python scripts/export_openapi.py` after any endpoint change
