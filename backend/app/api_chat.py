"""Chat / AI routes.

POST /api/chat/{filename}  — disabled in the prototype. CLAUDE.md scopes
step-12 to "Anthropic client wrapper + disabled /api/chat stub". The
endpoint exists so the API surface is honest and the frontend can wire
it up later, but every call returns 501 Not Implemented.

The wrapper itself (backend/app/llm.py) is fully implemented and tested
with recorded fixtures, so flipping the switch is a one-line change.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{filename}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def api_chat(filename: str) -> dict[str, str]:
    """AI-assisted document drafting — disabled in the prototype scope.

    Returns 501 with a stable JSON shape so the frontend can render a
    friendly error and the contract is documented in OpenAPI.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            f"AI chat is not enabled for {filename} in this prototype. "
            "See CLAUDE.md and step-12 — the LLM wrapper is wired but the "
            "/chat endpoint is intentionally disabled until the AI scope is "
            "approved."
        ),
    )
