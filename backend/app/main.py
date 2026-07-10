"""FastAPI entrypoint.

- Meta routes: /healthz
- API routes: /api/templates, /api/documents (under their own routers)
- Static SPA: frontend/dist is mounted at "/" via StaticFiles; a
  catch-all route returns index.html for any non-API GET that doesn't
  match a real file (so the SPA's history-API routes work after refresh).

The router order matters: include the API routers BEFORE mounting
StaticFiles, otherwise StaticFiles catches /api/* paths first.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api_documents import router as documents_router
from .api_templates import router as templates_router
from .config import get_settings

app = FastAPI(
    title="Prelegal",
    version="0.1.0",
    description="Draft legal agreements from CommonPaper templates.",
)


# ── Meta ─────────────────────────────────────────────────────────────────────


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    """Liveness probe used by Docker HEALTHCHECK and start scripts."""
    return {"status": "ok"}


# ── API routers (must come BEFORE StaticFiles mount) ─────────────────────────

app.include_router(templates_router)
app.include_router(documents_router)


# ── Static SPA ───────────────────────────────────────────────────────────────
#
# Resolved relative to repo root, not the package, because:
#   Docker:  /app/frontend/dist  (Dockerfile copies it there)
#   Local:   <repo>/frontend/dist (vite build output)
# When the directory is missing (e.g. a clean backend checkout before the
# frontend has been built), we skip the mount and let the API-only routes
# stand on their own — better than a startup crash.

DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if DIST_DIR.is_dir():
    # Serve real files (vite-emitted assets live under /assets/...).
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/", include_in_schema=False, response_model=None)
    async def spa_root() -> FileResponse:
        """Serve the SPA bundle at the canonical root URL."""
        return FileResponse(DIST_DIR / "index.html", media_type="text/html")

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def spa_fallback(full_path: str, request: Request) -> FileResponse | JSONResponse:
        """SPA history-API fallback: any GET that's not an API path returns
        index.html so React Router / hash routing works after a refresh.

        We explicitly exclude /api/* so a bad API URL still returns a proper
        404 from FastAPI (rather than getting masked by index.html).
        """
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        # Only fall back for browser-style Accept: text/html — programmatic
        # clients asking for JSON still get 404 from the API guard above.
        accept = request.headers.get("accept", "")
        if "text/html" not in accept and "*/*" not in accept:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(DIST_DIR / "index.html", media_type="text/html")

else:
    # Fallback so curl http://localhost:8000/ still gets something useful
    # when the SPA bundle hasn't been built yet (e.g. backend-only dev).
    @app.get("/", tags=["meta"])
    def root_fallback() -> dict[str, str]:
        return {
            "service": "prelegal",
            "see": "/healthz",
            "note": "frontend bundle not built; run `npm --prefix frontend run build`",
        }


def run() -> None:  # pragma: no cover - exercised via uvicorn CLI in image
    """`python -m backend.app.main` for local dev only."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.prelegal_host,
        port=settings.prelegal_port,
        reload=True,
    )


if __name__ == "__main__":  # pragma: no cover
    run()
