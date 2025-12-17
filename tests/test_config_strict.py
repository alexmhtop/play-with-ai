import os

import pytest

from src.config import get_settings


def test_strict_security_rejects_default_db(monkeypatch):
    monkeypatch.setenv("APP_STRICT_SECURITY", "true")
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres")
    with pytest.raises(RuntimeError):
        get_settings()


def test_strict_security_rejects_root_vault_token(monkeypatch):
    monkeypatch.setenv("APP_STRICT_SECURITY", "true")
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/db")
    monkeypatch.setenv("APP_VAULT_TOKEN", "root")
    with pytest.raises(RuntimeError):
        get_settings()


def test_strict_security_accepts_hardened_values(monkeypatch):
    monkeypatch.setenv("APP_STRICT_SECURITY", "true")
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+psycopg://user:strong@host:5432/db")
    monkeypatch.setenv("APP_KEYCLOAK_CLIENT_SECRET", "supersecret")
    settings = get_settings()
    assert settings.database_url.startswith("postgresql+psycopg://user:strong")
