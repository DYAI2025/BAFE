# Changelog

## 1.0.0-rc0

BaZodiac / BAFE integration (contract-first).

Added:
- spec/ SSOT bundle:
  - JSON Schemas Draft-07 for /validate
  - canonical ruleset standard_bazi_2026
  - acceptance tests TV1-TV7 + property tests PT1-PT4
- New /validate endpoint (contract-first, schema self-checked).
- RefData policy checks (no-network guard, manifest checks, hash/signature/expiry checks).
- Canonical mapping helpers (SHIFT_BOUNDARIES / SHIFT_LONGITUDES), TLST hour rule, kernel + harmonics utilities.
- Deterministic config fingerprint (sha256 over canonical JSON).

Changed:
- Removed implicit Swiss Ephemeris downloads at startup and runtime (must be provisioned explicitly).
- CI workflows no longer download ephemeris files.

Notes:
- Legacy compute endpoints (/calculate/*) now require Swiss Ephemeris files to be provided via SE_EPHE_PATH or ephe_path.
