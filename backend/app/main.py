"""FastAPI entrypoint. Step-03 adds /healthz; step-04 adds template routes."""

from __future__ import annotations

from fastapi import FastAPI

from .api_documents import router as documents_router
from .api_templates import router as templates_router
from .config import get_settings

app = FastAPI(
    title="Prelegal",
    version="0.1.0",
    description="Draft legal agreements from CommonPaper templates.",
)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    """Liveness probe used by Docker HEALTHCHECK and start scripts."""
    return {"status": "ok"}


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """Trivial route so curl http://localhost:8000/ is never a 404 before
    the frontend bundle lands (step-11 will replace this with the SPA).
    """
    return {"service": "prelegal", "see": "/healthz"}


app.include_router(templates_router)
app.include_router(documents_router)


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
