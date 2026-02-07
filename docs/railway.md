# Railway Deployment (API Service)

This repository ships with a Dockerfile that is ready for Railway.

## Quick start

1. Create a new **Railway Project** and add a **Service** from this GitHub repo.
2. Railway detects the `Dockerfile` and builds the container.
3. Set any optional environment variables (see below) and deploy.

The service listens on `PORT` (default `8080`) and exposes:
- `GET /health` for health checks.

## Optional environment variables

| Variable | Purpose |
| --- | --- |
| `ELEVENLABS_TOOL_SECRET` | Required only for the `/api/webhooks/chart` endpoint. |
| `SE_EPHE_PATH` | Override ephemeris path if you mount custom ephemeris files. |
| `EPHEMERIS_MODE` | `SWIEPH` (file-based) or `MOSEPH` (offline fallback). Defaults to auto. |

## Notes

- The Docker image defaults to `EPHEMERIS_MODE=MOSEPH` for a fully offline ephemeris.
- Health checks can use `/health`.
