"""Tests for serving the frontend SPA bundle from FastAPI (step-11).

Requires `frontend/dist/` to exist (built once by `vite build`). The tests
skip cleanly when the bundle is absent so backend-only dev keeps working.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import DIST_DIR, app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


pytestmark = pytest.mark.skipif(
    not FRONTEND_DIST.is_dir(),
    reason="frontend/dist not built; run `npm --prefix frontend run build`",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_spa_bundle_path_resolves(client: TestClient) -> None:
    """Sanity: DIST_DIR points at the actual frontend bundle location."""
    assert DIST_DIR == FRONTEND_DIST
    assert (FRONTEND_DIST / "index.html").is_file()


def test_root_serves_index_html(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    # Vite injects a <script type="module" src="..."> reference; sanity check.
    assert '<div id="root"' in body or 'id="root"' in body
    assert "<script" in body


def test_healthz_still_works(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_templates_still_works(client: TestClient) -> None:
    response = client.get("/api/templates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_spa_fallback_returns_index_for_unknown_routes(client: TestClient) -> None:
    """Hitting any non-API path that isn't a file should return index.html."""
    response = client.get("/some/spa/deep/route")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="root"' in response.text


def test_static_asset_is_served(client: TestClient) -> None:
    """A direct request for a built JS asset returns it with the right mime."""
    import re

    index = (FRONTEND_DIST / "index.html").read_text(encoding="utf-8")
    match = re.search(r'src="(/assets/[^"]+)"', index)
    assert match is not None, f"no asset reference found in index.html:\n{index}"
    js_path = match.group(1)
    response = client.get(js_path)
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert len(response.content) > 1000  # non-trivial JS payload
