# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
make setup              # Install dependencies (uses uv + .venv)
make dev                # Run local dev server on port 8000
make test               # Run pytest suite
make test-integration   # Run integration tests only (marked with @pytest.mark.integration)
make migrate            # Run Alembic migrations
make audit              # Dependency vulnerability scan
make security-scan      # Bandit static analysis
```

To run a single test: `.venv/bin/python -m pytest tests/test_api.py::test_function_name -v`

## Architecture Overview

This is a FastAPI Books API with Keycloak authentication, Postgres persistence, and OpenTelemetry observability.

### Source Code (`src/`)
- **app.py**: FastAPI application with v1/v2 API routers, middleware stack (security headers, rate limiting, request logging, CORS)
- **auth.py**: JWT verification using PyJWT with JWKS caching; `AuthVerifier` validates tokens against Keycloak; `require_scope()` enforces realm roles
- **service.py**: `BookService` handles CRUD operations using SQLAlchemy ORM
- **entities.py**: SQLAlchemy `BookRecord` model
- **models.py**: Pydantic schemas (`Book`, `CreateBook`, `UpdateBook`)
- **config.py**: `Settings` via pydantic-settings with Vault secret injection support
- **secrets.py**: Vault KV v2 secret fetching
- **otel.py**: OpenTelemetry setup (traces, metrics, logs to OTLP collector)
- **ratelimit.py**: Token bucket rate limiter per IP+token

### Infrastructure (`infra/terraform/`)
- **keycloak/**: Terraform for Keycloak realm, clients, roles, users (source of truth for auth config)
- **vault/**: Terraform for Vault KV secrets

### Observability Stack (docker-compose)
- OTEL Collector → Tempo (traces), Loki (logs), VictoriaMetrics (metrics)
- Grafana with provisioned datasources and dashboards
- Pyroscope for continuous profiling

## CI/CD Workflows

### Core Workflows
| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR | Unit tests (Python 3.11/3.12/3.13 matrix), Docker build |
| `quality.yml` | Push/PR | Lint, security scans, integration tests, coverage |
| `release.yml` | Tags `v*` | Build, sign with Cosign, SBOM, SLSA attestation, GitHub release |
| `deploy.yml` | Manual/Push | Deploy to staging (auto) or production (manual) |
| `rollback.yml` | Manual | Quick rollback with incident tracking |
| `merge-queue.yml` | Merge queue | Validates PRs in merge queue |

### Security Workflows
| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `security-scan.yml` | Weekly | Comprehensive security scans (Trivy, tfsec, Bandit, Semgrep) |
| `scorecard.yml` | Weekly | OpenSSF Scorecard security metrics |
| `codeql.yml` | Push/PR | GitHub CodeQL analysis |
| `license-scan.yml` | PR/Weekly | License compliance checking |

### PR Workflows
| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `pr-preview.yml` | PR open/sync | Deploy PR preview environment |
| `api-breaking-change.yml` | PR | Detect API breaking changes via OpenAPI diff |
| `migration-safety.yml` | PR | Analyze database migrations for dangerous operations |
| `changelog-preview.yml` | PR | Preview changelog entries from conventional commits |
| `labeler.yml` | PR | Auto-label PRs by changed files |
| `pr-size.yml` | PR | Label PRs by size (XS/S/M/L/XL) |

### Release & Versioning Workflows
| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `version-bump.yml` | Push to main | Auto-bump version based on conventional commits |
| `hotfix.yml` | Manual | Create hotfix branch from release tag |
| `backport.yml` | PR merged | Auto-backport to maintenance branches |
| `canary-deploy.yml` | Manual | Canary deployment with traffic shifting |

### Automation Workflows
| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `auto-merge-dependabot.yml` | Dependabot PRs | Auto-merge patch/minor updates |
| `stale.yml` | Daily | Auto-close stale issues (60d) and PRs (30d) |
| `welcome.yml` | First PR/Issue | Welcome message for new contributors |
| `notify.yml` | CI failure | Slack/Discord notifications |
| `benchmark.yml` | Push/PR | Performance benchmarks with Locust |
| `api-docs.yml` | Push | Generate OpenAPI spec and Redoc docs |
| `cache-cleanup.yml` | PR closed/Weekly | Clean up stale and orphaned caches |

### Reusable Workflows
- `_reusable-python-test.yml`: Parameterized Python testing
- `_reusable-docker-build.yml`: Parameterized Docker builds

### Composite Actions
| Action | Purpose |
|--------|---------|
| `setup-python-env` | Python setup with optimized caching |
| `docker-build` | Docker build with Buildx and layer caching |
| `notify-status` | Send Slack/Discord notifications |

## Key Configuration

Environment prefix: `APP_` (e.g., `APP_DATABASE_URL`, `APP_KEYCLOAK_ISSUER`)

Important env vars:
- `APP_DATABASE_URL`: Postgres connection string
- `APP_KEYCLOAK_ISSUER`: JWT issuer (must match Keycloak's advertised issuer exactly)
- `APP_VAULT_ADDR` / `APP_VAULT_TOKEN`: Enable Vault secret injection
- `APP_STRICT_SECURITY=true`: Reject default credentials
- `APP_REQUIRE_HTTPS=true`: Enforce HTTPS via x-forwarded-proto

## Testing

Tests are in `tests/` mirroring `src/` structure. Integration tests require Postgres and are marked with `@pytest.mark.integration`.

CI matrix tests on Python 3.11, 3.12, and 3.13.

## Code Quality

Linting and formatting configured in `pyproject.toml`:
```bash
ruff check src tests      # Lint
ruff format src tests     # Format
mypy src                  # Type check
```

CI runs coverage with 70% minimum threshold.

## Security Features

- **Container signing**: Cosign keyless signing on releases
- **SBOM**: Generated for every release (SPDX format)
- **SLSA provenance**: Build attestation for supply chain security
- **Dependency scanning**: Dependabot, pip-audit, Safety
- **Secret scanning**: Gitleaks, TruffleHog
- **SAST**: Bandit, Semgrep, CodeQL
- **Container scanning**: Trivy
- **Terraform scanning**: tfsec, Checkov

## GitHub Repository Setup

### Required Secrets/Variables
- `CODECOV_TOKEN`: For coverage reporting (optional)
- `SLACK_WEBHOOK_URL`: For Slack notifications (optional, set as variable)
- `DISCORD_WEBHOOK_URL`: For Discord notifications (optional, set as variable)

### Recommended Settings
See `docs/BRANCH_PROTECTION.md` for branch protection configuration.

### Environments
- **staging**: Auto-deploy on main push
- **production**: Manual deploy with required reviewers

## Coding Conventions

- Python: 4-space indent, Ruff-formatted (120 char line length)
- camelCase for variables/functions, PascalCase for classes
- Conventional Commits (`feat:`, `fix:`, `chore:`, etc.) - enforced on PRs

## Project Structure

```
├── src/                    # Application source code
├── tests/                  # Test suite (mirrors src/)
├── alembic/                # Database migrations
├── infra/terraform/        # Infrastructure as code
│   ├── keycloak/           # Auth configuration
│   └── vault/              # Secrets management
├── observability/          # Grafana dashboards, OTEL config
├── docs/                   # Documentation
├── .github/
│   ├── workflows/          # CI/CD workflows (31 total)
│   ├── actions/            # Composite actions
│   │   ├── setup-python-env/  # Python setup with caching
│   │   ├── docker-build/      # Docker build with Buildx
│   │   └── notify-status/     # Slack/Discord notifications
│   ├── ISSUE_TEMPLATE/     # Bug report, feature request templates
│   ├── CODEOWNERS          # Code ownership for reviews
│   ├── dependabot.yml      # Dependency update config
│   ├── labeler.yml         # PR auto-labeling config
│   └── pull_request_template.md
├── pyproject.toml          # Python tooling config (ruff, mypy, pytest)
├── cliff.toml              # Changelog generation config
├── Dockerfile              # Container image
└── docker-compose.yml      # Local development stack
```
