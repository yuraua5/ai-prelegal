"""Tests for the /healthz endpoint and the FastAPI app skeleton."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_healthz_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_returns_service_info() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "prelegal"
    assert body["see"] == "/healthz"


def test_app_metadata() -> None:
    """The FastAPI app exposes the title and version from CLAUDE.md."""
    assert app.title == "Prelegal"
    assert app.version == "0.1.0"
