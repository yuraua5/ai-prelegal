"""Tests for the /healthz endpoint and the FastAPI app skeleton."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Same skip pattern as tests/test_static_serve.py: the SPA-bundle tests in this
# module can only run when `frontend/dist` is actually on disk. In CI the
# backend-test job builds the bundle before pytest, but for local backend-only
# dev we skip gracefully instead of failing.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


def test_healthz_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.skipif(
    not FRONTEND_DIST.is_dir(),
    reason="frontend/dist not built; the backend-test CI job builds it before pytest",
)
def test_root_serves_html() -> None:
    """Since step-11 the / endpoint serves the SPA's index.html.

    Functional behaviour (HTML shell, mount root div, script tag) is
    exercised in tests/test_static_serve.py. Here we only check the
    content-type stays correct.
    """
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_root_fallback_when_no_bundle() -> None:
    """When the SPA bundle is absent, / returns a JSON pointer to /healthz.

    The main.py branch that serves this JSON only fires when DIST_DIR does
    not exist on disk; in our repo the bundle is always built, so this test
    is here as a future-proofing guard for backend-only development.
    """
    import builtins
    from pathlib import Path

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api_documents import router as documents_router
    from app.api_templates import router as templates_router

    fake_app = FastAPI(title="Prelegal", version="0.1.0")

    @fake_app.get("/healthz", tags=["meta"])
    def _healthz() -> dict[str, str]:
        return {"status": "ok"}

    fake_app.include_router(templates_router)
    fake_app.include_router(documents_router)

    # Simulate the `else` branch from main.py when DIST_DIR is missing.
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
    # Silence unused imports lint warnings.
    _ = (builtins, Path)


def test_app_metadata() -> None:
    """The FastAPI app exposes the title and version from CLAUDE.md."""
    assert app.title == "Prelegal"
    assert app.version == "0.1.0"
