import httpx
import pytest

from src.secrets import fetch_vault_secret


def test_fetch_vault_secret_returns_inner_data(monkeypatch):
    payload = {"data": {"data": {"database_url": "postgres://example"}}}

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))

    class DummyClient(httpx.Client):
        def __init__(self, timeout=5.0):
            super().__init__(transport=transport, timeout=timeout)

    monkeypatch.setattr(httpx, "Client", DummyClient)
    secret = fetch_vault_secret(addr="http://vault", token="t", mount="kv", path="books-api/config")
    assert secret["database_url"] == "postgres://example"


def test_fetch_vault_secret_raises_on_error(monkeypatch):
    transport = httpx.MockTransport(lambda request: httpx.Response(403, json={"errors": ["denied"]}))

    class DummyClient(httpx.Client):
        def __init__(self, timeout=5.0):
            super().__init__(transport=transport, timeout=timeout)

    monkeypatch.setattr(httpx, "Client", DummyClient)
    with pytest.raises(httpx.HTTPStatusError):
        fetch_vault_secret(addr="http://vault", token="bad", mount="kv", path="books-api/config")
