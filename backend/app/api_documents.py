"""Document fill + render endpoints.

POST /api/documents/{filename}        — pure substitution, returns markdown
POST /api/documents/{filename}/pdf    — same fill + PDF render (step-06)

The fill service is deliberately simple (no Jinja, no template engine): we
parse the literal `<span class="coverpage_link">Name</span>` tags CommonPaper
uses and replace them with the user-supplied values via regex substitution.
This keeps the dependency surface stdlib-only until step-06 needs weasyprint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from .templates_loader import _placeholder_names, get_template

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Same pattern as the loader, kept here too so this module is self-contained.
_SPAN_RE = re.compile(
    r'<span\s+class="coverpage_link"\s*>([^<]+)</span>',
    re.IGNORECASE,
)


class FillRequest(BaseModel):
    """Body for POST /api/documents/{filename}."""

    fields: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of placeholder display name -> user-supplied value",
    )


@dataclass(frozen=True, slots=True)
class FillResult:
    """Internal result of substituting fields into a template body."""

    markdown: str
    missing: list[str]


def fill_markdown(body: str, values: dict[str, str]) -> FillResult:
    """Replace every `<span class="coverpage_link">Name</span>` with `values[Name]`.

    Placeholders whose name is not in `values` are left in place so the UI can
    highlight them and the user can see what's still missing. The `missing`
    list returns their names in document order.
    """
    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        if name in values and values[name]:
            return values[name]
        if name not in missing:
            missing.append(name)
        return match.group(0)

    rendered = _SPAN_RE.sub(_replace, body)
    return FillResult(markdown=rendered, missing=missing)


@router.post("/{filename}")
def api_fill_document(filename: str, payload: FillRequest) -> dict[str, object]:
    """Substitute fields into a template body. Returns markdown + missing fields.

    The contract is forgiving: unrecognised keys in `fields` are ignored,
    missing keys are listed in `missing`. The frontend uses `missing` to
    render the form's red-outlined inputs.
    """
    template = get_template(filename)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"template not in catalog: {filename}",
        )

    result = fill_markdown(template.body, payload.fields)

    # Cross-check: a value was supplied under a name the template does not
    # reference. We do NOT 400 — the frontend might send all known fields
    # upfront. Surface the extras so the UI can ignore them cleanly.
    declared_fields = set(template.fields)
    extras = sorted(set(payload.fields) - declared_fields)

    return {
        "filename": filename,
        "markdown": result.markdown,
        "missing": result.missing,
        "extras": extras,
        # Sanity: every declared field that wasn't supplied also lands in `missing`.
        "fields": declared_fields,
    }


def _extract_field_names(body: str) -> list[str]:
    """Re-exported for tests that want to assert placeholder ordering."""
    return _placeholder_names(body)
