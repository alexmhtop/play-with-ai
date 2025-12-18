# AGENTS GUIDE
Agent-facing checklist for FastAPI books-api; treat as canonical.
- Layout: runtime code stays in src/, mirrored tests in tests/, docs/ for ADRs, infra/terraform/* for IaC.
- Config & tooling live at repo root (Makefile, docker-compose.yml, .env examples); keep modules cohesive/small.
- docker compose up -d boots Postgres/Keycloak/Vault/observability before integration work.
- make setup (uv venv + pinned requirements) precedes make dev (uvicorn honoring APP_DATABASE_URL env).
- make lint runs ruff format --check, ruff check, and mypy (line-length 120, double quotes, grouped imports enforced).
- make unit executes pytest -m "not integration"; pass PYTEST_ARGS for extra flags/coverage; make test covers full suite; make test-integration runs -m integration.
- make test-one TEST=tests/...::case executes a single test path using the configured DB URL and settings.
- Use snake_case for funcs/modules, PascalCase classes/models, SCREAMING_SNAKE env vars; Pydantic BaseModel + Field constraints for payload validation.
- Annotate FastAPI dependencies (typing.Annotated) and surface errors via HTTPException(status_code=..., detail=...) rather than bare dicts/KeyErrors.
- Routers live under /api/v1 or /api/v2; preserve books:read/books:write guards and TokenBucket limiter + request/logging/request-id middleware stack.
- Settings toggles (APP_REQUIRE_HTTPS, APP_STRICT_SECURITY, APP_CORS_ORIGINS, Vault/OTEL/Pyroscope envs) must continue to short-circuit insecure flows.
- Secrets never land in git; Vault dev service (port 8200) is the source of database_url + client_secret seeded via infra/terraform/vault.
- Keycloak terraform (infra/terraform/keycloak) keeps books-api client direct_access/service_accounts enabled and demo password non-temporary.
- Observability: OTLP -> collector -> Tempo/Loki/VictoriaMetrics/Grafana/Pyroscope; logs/traces share trace_id/span_id; keep instrumentation hooks intact.
- DB changes go through alembic (make migrate / make migrate-stamp); alembic/versions/ retains chronological history.
- Security hygiene: make audit (pip-audit) and make security-scan (bandit) are first-class; Vault secrets job plus terraform fmt/validate guard infra PRs.
- CI: uv version is pinned/cached, lint/unit run before heavier docker/integration stages, security checks run as a parallel matrix, and vault_seed_smoke applies terraform against a dev Vault container.
- No Cursor or Copilot instruction files exist; AGENTS.md is the authoritative playbook.
