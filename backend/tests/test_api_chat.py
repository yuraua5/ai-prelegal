"""Tests for /api/chat stub + the Anthropic wrapper parsing."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_chat_endpoint_returns_501(client: TestClient) -> None:
    """The /chat endpoint is intentionally disabled in the prototype.

    CLAUDE.md scopes step-12 to "Anthropic client wrapper + disabled
    /api/chat stub". Verifies the stable 501 contract.
    """
    response = client.post(
        "/api/chat/Mutual-NDA.md",
        json={"messages": [{"role": "user", "content": "Help me fill this"}]},
    )
    assert response.status_code == 501
    body = response.json()
    assert "AI chat is not enabled" in body["detail"]
    assert "Mutual-NDA.md" in body["detail"]


def test_chat_endpoint_ignores_body_shape(client: TestClient) -> None:
    """Even an empty body returns 501 — no UpstreamValidation error."""
    response = client.post(
        "/api/chat/Mutual-NDA.md",
        json={},
    )
    assert response.status_code == 501
