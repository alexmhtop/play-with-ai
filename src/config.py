from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Books API"
    version: str = "1.0.0"
    keycloak_realm: str = "books"
    keycloak_audience: str = "books-api"
    keycloak_issuer: str = "https://localhost/realms/books"
    jwks_url: str = "http://localhost:8080/realms/books/protocol/openid-connect/certs"

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", case_sensitive=False)


def get_settings() -> Settings:
    return Settings()
