"""Unit + integration tests for the document fill endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import templates_loader as loader
from app.api_documents import fill_markdown
from app.main import app


@pytest.fixture(autouse=True)
def _clear_loader_cache() -> None:
    loader.reset_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── unit: fill_markdown ──────────────────────────────────────────────────────


def test_fill_replaces_known_placeholders() -> None:
    body = (
        'Hello <span class="coverpage_link">Party A</span>, '
        'purpose: <span class="coverpage_link">Purpose</span>.'
    )
    result = fill_markdown(body, {"Party A": "Acme", "Purpose": "evaluation"})
    assert result.markdown == "Hello Acme, purpose: evaluation."
    assert result.missing == []


def test_fill_lists_missing_fields() -> None:
    body = (
        'Hello <span class="coverpage_link">Party A</span>, '
        'purpose: <span class="coverpage_link">Purpose</span>.'
    )
    result = fill_markdown(body, {"Party A": "Acme"})
    assert result.markdown == 'Hello Acme, purpose: <span class="coverpage_link">Purpose</span>.'
    assert result.missing == ["Purpose"]


def test_fill_empty_value_treated_as_missing() -> None:
    body = 'Hello <span class="coverpage_link">Party A</span>.'
    result = fill_markdown(body, {"Party A": ""})
    assert result.missing == ["Party A"]
    assert "<span" in result.markdown


def test_fill_ignores_extra_keys() -> None:
    body = 'Hello <span class="coverpage_link">Party A</span>.'
    result = fill_markdown(body, {"Party A": "Acme", "NotInTemplate": "x"})
    assert result.missing == []


def test_fill_preserves_whitespace_inside_placeholder() -> None:
    body = 'X: <span class="coverpage_link">  Trim Me  </span>'
    result = fill_markdown(body, {"Trim Me": "ok"})
    assert result.markdown == "X: ok"


# ── integration: POST /api/documents/{filename} ─────────────────────────────


def test_endpoint_fills_mutual_nda_completely(client: TestClient) -> None:
    response = client.post(
        "/api/documents/Mutual-NDA.md",
        json={
            "fields": {
                "Purpose": "evaluating a potential partnership",
                "Effective Date": "2026-01-01",
                "MNDA Term": "2 years",
                "Term of Confidentiality": "3 years",
                "Governing Law": "Delaware",
                "Jurisdiction": "New Castle County, Delaware",
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["missing"] == []
    assert body["extras"] == []
    assert "evaluating a potential partnership" in body["markdown"]
    assert "Delaware" in body["markdown"]
    # No leftover <span class="coverpage_link"> tags in the rendered body.
    assert "coverpage_link" not in body["markdown"]


def test_endpoint_reports_missing_fields(client: TestClient) -> None:
    response = client.post(
        "/api/documents/Mutual-NDA.md",
        json={"fields": {"Purpose": "evaluating"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Purpose" not in body["missing"]
    assert "Governing Law" in body["missing"]
    assert "Jurisdiction" in body["missing"]
    # Leftover placeholders are still visible in the rendered markdown.
    assert "coverpage_link" in body["markdown"]


def test_endpoint_reports_extras(client: TestClient) -> None:
    response = client.post(
        "/api/documents/Mutual-NDA.md",
        json={"fields": {"Purpose": "x", "SurpriseField": "y"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["extras"] == ["SurpriseField"]


def test_endpoint_unknown_filename_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/documents/NotARealTemplate.md",
        json={"fields": {}},
    )
    assert response.status_code == 404


def test_endpoint_empty_body_is_ok(client: TestClient) -> None:
    """An empty `fields` map is valid — the response simply reports every
    declared field as missing and renders the original template unchanged.
    """
    response = client.post(
        "/api/documents/Mutual-NDA.md",
        json={"fields": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["missing"]) == set(body["fields"])
    assert "coverpage_link" in body["markdown"]
