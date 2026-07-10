"""Pydantic schemas for API responses. One schema per route keeps the
contract explicit and lets OpenAPI generate accurate types for the frontend.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TemplateSummary(BaseModel):
    """Lightweight summary returned by GET /api/templates."""

    name: str
    description: str
    filename: str


class TemplateDetail(BaseModel):
    """Detailed view returned by GET /api/templates/{filename}.
    Includes the markdown body and the list of placeholder field names so
    the frontend can render a form without an extra round-trip.
    """

    name: str
    description: str
    filename: str
    body: str = Field(description="Markdown source of the template")
    fields: list[str] = Field(
        default_factory=list,
        description="Placeholder display names in document order",
    )
