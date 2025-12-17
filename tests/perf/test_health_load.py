import asyncio

import httpx
import pytest

from src.app import app


@pytest.mark.anyio
async def test_health_under_load():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        results = await asyncio.gather(*[client.get("/api/v1/health") for _ in range(20)])
    assert all(r.status_code == 200 for r in results)
