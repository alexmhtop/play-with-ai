# play-with-ai

[![CI](https://github.com/moderation-is-good/play-with-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/moderation-is-good/play-with-ai/actions/workflows/ci.yml)
[![Quality and Safety](https://github.com/moderation-is-good/play-with-ai/actions/workflows/quality.yml/badge.svg)](https://github.com/moderation-is-good/play-with-ai/actions/workflows/quality.yml)
[![CodeQL](https://github.com/moderation-is-good/play-with-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/moderation-is-good/play-with-ai/actions/workflows/codeql.yml)

FastAPI + Keycloak–secured books API with Postgres, Vault, and a full observability stack (OTel/Tempo/Loki/VictoriaMetrics/Grafana/Pyroscope). Built with uv, instrumented for traces/logs/metrics, and hardened CI/CD (lint, tests, security scans, SBOM).

## Running locally
- Install deps + venv: `make setup` (uv venv + pip install pinned requirements).
- Start stack: `docker compose up -d` to boot Postgres/Keycloak/Vault/observability.
- Run app: `make dev` (uvicorn with APP_DATABASE_URL fallback to localhost Postgres).
- Fast checks: `make lint` (ruff format/check + mypy) then `make unit` (pytest -m "not integration").
- Targeted test: `make test-one TEST=tests/test_api.py::test_health` (honors extra `PYTEST_ARGS`).

## CI/CD summary
- **CI**: unit tests with coverage on a Postgres service, SBOM via Syft, multi-arch image build to GHCR.
- **Quality and Safety**: ruff/bandit/mypy, pip-audit, coverage upload, integration smoke (Keycloak/Tempo/Loki).
- **Security**: gitleaks secret scan, CodeQL static analysis.

See `AGENTS.md` for deeper operational notes.
