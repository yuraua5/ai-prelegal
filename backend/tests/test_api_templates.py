"""Integration tests for /api/templates endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import templates_loader as loader
from app.main import app


@pytest.fixture(autouse=True)
def _clear_loader_cache() -> None:
    loader.reset_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_templates_returns_200_and_array(client: TestClient) -> None:
    response = client.get("/api/templates")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0, "catalog.json should expose at least one template"


def test_list_templates_includes_mutual_nda(client: TestClient) -> None:
    body = client.get("/api/templates").json()
    filenames = {entry["filename"] for entry in body}
    assert "Mutual-NDA.md" in filenames


def test_list_templates_entries_have_required_keys(client: TestClient) -> None:
    body = client.get("/api/templates").json()
    for entry in body:
        assert set(entry.keys()) >= {"name", "description", "filename"}


def test_get_template_returns_full_detail(client: TestClient) -> None:
    response = client.get("/api/templates/Mutual-NDA.md")
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "Mutual-NDA.md"
    assert "name" in body
    assert "description" in body
    assert "body" in body
    assert "fields" in body
    assert isinstance(body["fields"], list)
    assert "Purpose" in body["fields"], "Mutual NDA must include 'Purpose' as a field"


def test_get_template_unknown_filename_returns_404(client: TestClient) -> None:
    response = client.get("/api/templates/NotARealTemplate.md")
    assert response.status_code == 404
    assert "NotARealTemplate.md" in response.text
