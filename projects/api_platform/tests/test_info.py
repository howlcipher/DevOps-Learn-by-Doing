from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_info_returns_service_metadata() -> None:
    response = client.get("/info")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "api-platform"
    assert "version" in body
    assert "environment" in body


def test_info_never_leaks_secret_looking_keys() -> None:
    response = client.get("/info")
    body = response.json()
    forbidden = {"password", "secret", "token", "key", "credential"}
    assert not (set(k.lower() for k in body) & forbidden)
