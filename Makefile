UV ?= uv
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
APP_DATABASE_URL ?= postgresql+psycopg://postgres:postgres@localhost:5432/postgres

.PHONY: setup dev test check migrate migrate-stamp test-integration audit security-scan

setup:
	$(UV) venv $(VENV)
	$(UV) pip install -r requirements.txt

dev: setup
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

test: setup
	$(PYTHON) -m pytest

check: test

migrate:
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m alembic upgrade head

migrate-stamp:
	APP_DATABASE_URL=$(APP_DATABASE_URL) $(PYTHON) -m alembic stamp head

test-integration: setup
	$(PYTHON) -m pytest -m integration

audit: setup
	$(UV) pip audit -r requirements.txt || true

security-scan: setup
	$(PYTHON) -m bandit -q -r src || true
