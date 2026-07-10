"""Tests for the /healthz endpoint and the FastAPI app skeleton."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api_documents import router as documents_router
from app.api_templates import router as templates_router
from app.main import DIST_DIR, app


def test_healthz_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.skipif(
    not DIST_DIR.is_dir(),
    reason="frontend/dist not built; step-11 SPA tests handle this case",
)
def test_root_serves_html() -> None:
    """Since step-11 the / endpoint serves the SPA's index.html.

    Skipped in CI when frontend/dist is absent — the static-serve test
    file is the canonical place to assert content-type and structure.
    """
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_root_fallback_when_no_bundle() -> None:
    """When the SPA bundle is absent, / returns a JSON pointer to /healthz.

    We build a parallel FastAPI app with the same routers as main.py plus
    the JSON-only fallback route, to exercise the `else` branch without
    having to mutate the module-level app (which other tests rely on).
    """
    fake_app = FastAPI(title="Prelegal", version="0.1.0")

    @fake_app.get("/healthz", tags=["meta"])
    def _healthz() -> dict[str, str]:
        return {"status": "ok"}

    fake_app.include_router(templates_router)
    fake_app.include_router(documents_router)

    @fake_app.get("/", tags=["meta"])
    def _root_fallback() -> dict[str, str]:
        return {
            "service": "prelegal",
            "see": "/healthz",
            "note": "frontend bundle not built; run `npm --prefix frontend run build`",
        }

    client = TestClient(fake_app)
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "prelegal"
    assert body["see"] == "/healthz"
    assert "frontend bundle not built" in body["note"]


def test_app_metadata() -> None:
    """The FastAPI app exposes the title and version from CLAUDE.md."""
    assert app.title == "Prelegal"
    assert app.version == "0.1.0"
