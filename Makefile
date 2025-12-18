UV ?= uv
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
APP_DATABASE_URL ?= postgresql+psycopg://postgres:postgres@localhost:5432/postgres
PYTEST_ARGS ?=

.PHONY: setup dev test unit test-one lint check migrate migrate-stamp test-integration audit security-scan

setup:
	$(UV) venv $(VENV)
	$(UV) pip install -r requirements.txt

dev: setup
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

test: setup
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m pytest $(PYTEST_ARGS)

unit: setup
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m pytest -m "not integration" $(PYTEST_ARGS)

lint: setup
	$(UV) run ruff format --check src tests
	$(UV) run ruff check src tests
	$(UV) run mypy src

# TEST must be passed, e.g. make test-one TEST=tests/test_api.py::test_health
test-one: setup
	@if [ -z "$(TEST)" ]; then echo "TEST=tests/...::TestCase is required"; exit 1; fi
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m pytest $(TEST)

check: lint test

migrate:
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m alembic upgrade head

migrate-stamp:
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m alembic stamp head

test-integration: setup
	$(PYTHON) -m pytest -m integration $(PYTEST_ARGS)

audit: setup
	$(UV) run pip-audit -r requirements.txt

security-scan: setup
	$(UV) run bandit -q -r src
