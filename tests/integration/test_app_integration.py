import os
import time

import httpx
import pytest


def _required_env(names):
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        pytest.skip(f"integration env missing: {', '.join(missing)}")


@pytest.fixture(scope="session")
def integration_env():
    required = ["TOKEN_ENDPOINT", "CLIENT_ID", "CLIENT_SECRET", "DEMO_USER_PASSWORD"]
    _required_env(required)
    return {
        "base_url": os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        "token_endpoint": os.getenv("TOKEN_ENDPOINT"),
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "demo_password": os.getenv("DEMO_USER_PASSWORD"),
    }


async def _get_token(env, grant_type: str, username: str | None = None, password: str | None = None) -> str:
    data = {
        "grant_type": grant_type,
        "client_id": env["client_id"],
        "client_secret": env["client_secret"],
    }
    if username:
        data["username"] = username
    if password:
        data["password"] = password

    async with httpx.AsyncClient() as client:
        resp = await client.post(env["token_endpoint"], data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_health_endpoint(integration_env):
    async with httpx.AsyncClient(base_url=integration_env["base_url"]) as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.integration
@pytest.mark.anyio
async def test_client_credentials_crud(integration_env):
    token = await _get_token(integration_env, "client_credentials")
    headers = {"Authorization": f"Bearer {token}"}
    title = f"Integration-{int(time.time())}"
    payload = {"title": title, "author": "Bot", "price": 1.23, "in_stock": True}

    async with httpx.AsyncClient(base_url=integration_env["base_url"]) as client:
        created = await client.post("/api/v1/books", json=payload, headers=headers)
        assert created.status_code == 201, created.text
        book_id = created.json()["id"]

        fetched = await client.get(f"/api/v1/books/{book_id}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["title"] == title

        deleted = await client.delete(f"/api/v1/books/{book_id}", headers=headers)
        assert deleted.status_code == 204


@pytest.mark.integration
@pytest.mark.anyio
async def test_password_grant_can_list(integration_env):
    token = await _get_token(
        integration_env,
        "password",
        username="demo",
        password=integration_env["demo_password"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=integration_env["base_url"]) as client:
        resp = await client.get("/api/v1/books", headers=headers)
    assert resp.status_code == 200
