# Repository Guidelines

This repo is intentionally lightweight; add new code using the structure below so growth stays predictable.

## Project Structure & Module Organization
- Keep runtime code in `src/` (grouped by domain, e.g., `src/auth/`, `src/api/`, `src/ui/`).
- Place automated tests in `tests/`, mirroring the `src/` path; sample data and fixtures live in `tests/fixtures/`.
- Long-form docs and decision notes go in `docs/`; reusable scripts belong in `scripts/`; static assets in `assets/`.
- Keep configuration at the repo root (`Makefile`, `.env.example`, dependency manifests) and favor small, cohesive modules over monolith files.

## Build, Test, and Development Commands
- Prefer a `Makefile` (or `justfile`) as a single entrypoint; add/update these targets when tooling is added:
  - `make setup` installs dependencies; `make dev` runs the local server/watcher; `make lint` and `make format` enforce style; `make test` runs the suite; `make check` chains lint + tests.
- If the stack is Node, expose `npm run dev|test|lint`; for Python, mirror with `pip install -r requirements.txt` and `pytest`.

## Coding Style & Naming Conventions
- JavaScript/TypeScript: 2-space indent, single quotes, trailing commas where allowed, semicolons on; Python: 4-space indent, Black-compatible.
- Use camelCase for variables/functions, PascalCase for components/classes, SCREAMING_SNAKE_CASE for env vars.
- Run formatters via `make format`; lint before commits to keep diffs small.

## Testing Guidelines
- Name tests after the unit under test (`tests/api/test_users.py`, `tests/ui/Button.spec.ts`); prefer table-driven cases for edge coverage.
- Add a regression test with every bug fix; aim for ≥85% coverage on critical modules.
- Run `make test` (or the language-specific equivalent) before opening a PR.

## Commit & Pull Request Guidelines
- Use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`) with concise scopes; group large refactors under `refactor:`.
- PRs should include: scope/intent, a short summary of changes, tests executed, and screenshots for UI work; keep PRs small and link related issues.
- Run `make check` before pushing; avoid committing generated files and secrets.

## Security & Configuration Tips
- Never commit secrets; add placeholders to `.env.example` and keep `.env*` ignored.
- Pin dependencies and document required versions; note any system packages in `docs/setup.md`.
- Prefer local configuration files over global machine state; surface breaking changes in the changelog or PR description.

## Agent Notes (Keycloak/Terraform)
- `docker-compose.yml` now uses a named network `play-with-ai` (not the default compose network).
- Keycloak container runs `/opt/keycloak/bin/kc.sh build` before `kc.sh start --optimized` so Postgres settings are applied correctly.
- Keycloak healthcheck no longer uses `curl` (the upstream image doesn’t include it); it uses a lightweight `kc.sh` command instead.
- Terraform config lives in `infra/terraform/keycloak/` and is intended to be the only way we configure realms/clients/roles/users.
- `infra/terraform/keycloak/main.tf` changes made in this session:
  - `keycloak_openid_client.api`: `direct_access_grants_enabled = true`, `service_accounts_enabled = true`
  - `keycloak_user.demo`: initial password is no longer temporary (`temporary = false`)
- Expected verification after `terraform apply`:
  - OIDC discovery works: `GET http://127.0.0.1:8080/realms/books/.well-known/openid-configuration`
  - Client credentials token works for `books-api` and includes `aud=books-api` and realm roles `books:read`/`books:write`.
  - Password grant should work for `demo` (using `demo_user_password`) without “Account is not fully set up”.
  - Note: Keycloak may advertise `issuer` as `https://localhost/realms/books`; API JWT validation must use the same issuer value.

## Agent Notes (Vault/Secrets)
- Vault dev service added to docker-compose on port 8200 (IPC_LOCK enabled, healthcheck). Terraform in `infra/terraform/vault/` mounts KV v2 and seeds `kv/books-api/config` with `database_url` and `client_secret` (see `terraform.tfvars.example`).
- App can pull `database_url` and Keycloak client secret from Vault when `APP_VAULT_ADDR`/`APP_VAULT_TOKEN` (and `APP_VAULT_KV_MOUNT`/`APP_VAULT_SECRET_PATH`) are set.
- Strict security flags: `APP_STRICT_SECURITY=true` rejects obvious default creds; `APP_REQUIRE_HTTPS=true` enforces forwarded-proto/HTTPS.

## Agent Notes (Security/Runtime)
- JWT verifier enforces typ/alg whitelist, clock skew; JWKS fetched at startup. Security headers include HSTS, CSP, CORP, nosniff, frame-deny, referrer policy; auth responses add `Cache-Control: no-store`.
- Rate limiting (token bucket per IP+token suffix), request IDs on responses, CORS restricted via `APP_CORS_ORIGINS`.
- Input bounds: title/author length capped; price >0 and bounded; DB schema matches constraints.
- Make targets: `make audit` (uv pip audit) and `make security-scan` (bandit). `.gitignore` covers tfvars; `.dockerignore` excludes tests/alembic/terraform from images.

## Agent Notes (Observability)
- OpenTelemetry instrumentation added (FastAPI/HTTPX/urllib/logging); OTLP endpoint default `http://otel-collector:4318` (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`). Logs include `trace_id`/`span_id` via a log hook; request middleware emits start/end events.
- Observability stack in docker-compose: otel-collector (routes traces->Tempo, metrics->VictoriaMetrics via prom RW, logs->Loki), Tempo, Loki, VictoriaMetrics, Grafana (provisioned datasources/dashboards), Pyroscope for profiling (port 4040).
- Tempo single-node config with local WAL/blocks; metrics-generator enabled via inline overrides; span-metrics and service-graph metrics are forwarded to VictoriaMetrics (series like `traces_spanmetrics_calls_total` present).
- Grafana provisioning under `observability/grafana/` (datasource.yml, dashboard) includes traces→logs/metrics drilldowns; Loki derived fields match `traceid`/`trace_id`. Ports: Grafana 3000, Loki 3100, Tempo 3200/4317/4318, VM 8428, Keycloak 8080, Vault 8200, OTLP 4318, Pyroscope 4040.
- App profiling: set `PYROSCOPE_SERVER_ADDRESS`/`PYROSCOPE_APP_NAME` (defaults to `books-api`) to send profiles to Pyroscope. Logs and traces link in Grafana; Tempo trace fetch via `http://localhost:3200/api/traces/{id}` works.
