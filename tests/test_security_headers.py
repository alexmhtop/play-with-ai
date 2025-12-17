import httpx
import pytest

from src.app import app


@pytest.mark.anyio
async def test_security_headers_present():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/health")
    headers = resp.headers
    assert headers["Strict-Transport-Security"].startswith("max-age")
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "Permissions-Policy" in headers
    assert headers["Content-Security-Policy"].startswith("default-src 'none'")
    assert headers["Cross-Origin-Resource-Policy"] == "same-origin"
