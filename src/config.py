import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .secrets import fetch_vault_secret

load_dotenv(".env")


def _default_db_url() -> str:
    env_url = os.getenv("APP_DATABASE_URL") or os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db_name = os.getenv("POSTGRES_DB", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"


class Settings(BaseSettings):
    app_name: str = "Books API"
    version: str = "1.0.0"
    keycloak_realm: str = "books"
    keycloak_audience: str = "books-api"
    keycloak_issuer: str = "https://localhost/realms/books"
    jwks_url: str = "http://localhost:8080/realms/books/protocol/openid-connect/certs"
    keycloak_client_secret: str | None = None
    database_url: str = Field(default_factory=_default_db_url)
    require_https: bool = False
    strict_security: bool = False
    vault_addr: str | None = None
    vault_token: str | None = None
    vault_kv_mount: str = "kv"
    vault_secret_path: str = "books-api/config"

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    settings = Settings()
    if settings.vault_addr and settings.vault_token:
        secret = fetch_vault_secret(
            addr=settings.vault_addr,
            token=settings.vault_token,
            mount=settings.vault_kv_mount,
            path=settings.vault_secret_path,
        )
        if secret.get("database_url"):
            settings.database_url = secret["database_url"]
        if secret.get("client_secret"):
            settings.keycloak_client_secret = secret["client_secret"]
    if settings.strict_security:
        insecure_markers = ("postgres:postgres@", "changeme", "change-me", "replace-me", "root@")
        if settings.database_url and any(marker in settings.database_url for marker in insecure_markers):
            raise RuntimeError("Insecure database credentials detected")
        if settings.keycloak_client_secret and any(marker in settings.keycloak_client_secret for marker in insecure_markers):
            raise RuntimeError("Insecure client secret detected")
        if settings.vault_token and settings.vault_token.lower() == "root":
            raise RuntimeError("Insecure Vault token detected")
    return settings
