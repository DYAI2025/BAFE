# CONTRACT.md — BaZi Engine API Contract

## Source of Truth

**`spec/openapi/openapi.json`** is the API contract. All integrations (clients, code generators, documentation) derive from this file.

> The implementation must conform to the OpenAPI spec — not the other way around.

## Contract Artifacts

| Artifact | Path | Format |
|----------|------|--------|
| OpenAPI Spec | `spec/openapi/openapi.json` | OpenAPI 3.1 (JSON) |
| ValidateRequest Schema | `spec/schemas/ValidateRequest.schema.json` | JSON Schema Draft-07 |
| ValidateResponse Schema | `spec/schemas/ValidateResponse.schema.json` | JSON Schema Draft-07 |
| BaZi Ruleset | `spec/rulesets/standard_bazi_2026.json` | Custom JSON |

## Versioning

- `info.version` in OpenAPI is coupled to `bazi_engine.__version__`
- Version format: `MAJOR.MINOR.PATCH-prerelease-YYYYMMDD`
- Current: `1.0.0-rc1-20260220`

## CI Drift Prevention

The CI pipeline includes an **OpenAPI drift check**:

```bash
python scripts/export_openapi.py --check
```

This regenerates the spec from `app.openapi()` and fails if it differs from the committed version. Any endpoint or schema change requires an explicit spec update:

```bash
python scripts/export_openapi.py   # Regenerate
git diff spec/openapi/             # Review changes
```

## Endpoints (Frozen)

All 13 endpoints have typed request/response schemas in OpenAPI:

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/` | — | `RootResponse` |
| GET | `/health` | — | `HealthResponse` |
| GET | `/build` | — | `BuildResponse` |
| GET | `/api` | query params | `ApiResponse` |
| GET | `/info/wuxing-mapping` | — | `WuxingMappingResponse` |
| POST | `/validate` | `ValidateRequest` (Draft-07) | `ValidateResponse` (Draft-07) |
| POST | `/calculate/bazi` | `BaziRequest` | `BaziResponse` |
| POST | `/calculate/western` | `WesternRequest` | `WesternResponse` |
| POST | `/calculate/fusion` | `FusionRequest` | `FusionResponse` |
| POST | `/calculate/wuxing` | `WxRequest` | `WxResponse` |
| POST | `/calculate/tst` | `TSTRequest` | `TSTResponse` |
| POST | `/chart` | `ChartRequest` | `ChartResponse` |
| POST | `/api/webhooks/chart` | `ElevenLabsChartRequest` | `WebhookChartResponse` |

## Error Responses

All endpoints use the `ErrorEnvelope` schema for error responses:

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "detail": {}
}
```

Standard HTTP codes: `422` (input), `500` (internal), `503` (ephemeris unavailable), `501` (not supported).

## `/validate` Endpoint — Dual Schema Model

The `/validate` endpoint uses **JSON Schema Draft-07** for runtime validation (via `jsonschema.Draft7Validator`), while the same schemas are **referenced in OpenAPI** for documentation and codegen. This is intentional:

- Runtime: Draft-07 (`spec/schemas/*.schema.json`)
- Documentation: Embedded in OpenAPI `components.schemas` (Draft-07 meta-keys stripped)
- Future: Draft-07 → 2020-12 migration is a Phase 2 concern
