import asyncio

import httpx

from app.main import app


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_info_returns_service_metadata() -> None:
    response = asyncio.run(_get("/info"))
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "api-platform"
    assert "version" in body
    assert "environment" in body


def test_info_never_leaks_secret_looking_keys() -> None:
    response = asyncio.run(_get("/info"))
    body = response.json()
    forbidden = {"password", "secret", "token", "key", "credential"}
    assert not (set(k.lower() for k in body) & forbidden)
