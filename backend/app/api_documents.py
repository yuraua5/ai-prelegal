"""Document fill + render endpoints.

POST /api/documents/{filename}        — pure substitution, returns markdown
POST /api/documents/{filename}/pdf    — same fill + PDF render (step-06)

The fill service is deliberately simple (no Jinja, no template engine): we
parse the literal `<span class="coverpage_link">Name</span>` tags CommonPaper
uses and replace them with the user-supplied values via regex substitution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import markdown as markdown_lib
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from weasyprint import HTML

from .templates_loader import _placeholder_names, get_template

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Same pattern as the loader, kept here too so this module is self-contained.
_SPAN_RE = re.compile(
    r'<span\s+class="coverpage_link"\s*>([^<]+)</span>',
    re.IGNORECASE,
)

# Inline CSS for the PDF — kept simple because the templates are basic
# markdown. Brand-accurate typography is not a step-06 requirement.
_PDF_CSS = """
@page {
    size: Letter;
    margin: 0.75in;
}
body {
    font-family: 'Liberation Sans', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #000;
}
h1, h2, h3 { color: #032147; }
h1 { font-size: 18pt; }
h2 { font-size: 14pt; }
h3 { font-size: 12pt; }
strong { font-weight: bold; }
em { font-style: italic; }
p { margin: 0.5em 0; }
ol, ul { margin: 0.5em 0; padding-left: 1.5em; }
"""


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


def _render_markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    """Convert a CommonPaper-flavoured markdown body to a PDF byte string.

    Steps:
      1. markdown -> HTML (with fenced code, tables, common extensions)
      2. inline `<style>` block with print-friendly rules
      3. WeasyPrint -> bytes

    WeasyPrint is synchronous and CPU-bound; for a real production app we'd
    push it onto a threadpool. For the prototype the request volume is low
    and a blocking render is acceptable.
    """
    html_body = markdown_lib.markdown(
        markdown_text,
        extensions=["extra", "sane_lists"],
    )
    html_doc = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{_PDF_CSS}</style></head><body>{html_body}</body></html>"
    )
    pdf_bytes: bytes = HTML(string=html_doc, base_url=".").write_pdf()
    return pdf_bytes


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


@router.post("/{filename}/pdf")
def api_fill_document_pdf(filename: str, payload: FillRequest) -> Response:
    """Same fill logic as /api/documents/{filename}, but returns a PDF.

    The PDF is rendered even when fields are missing — the unfilled
    placeholders stay as `<span>` tags inside the HTML, which become
    bracketed placeholders in the rendered output. The frontend should
    ideally block the call when fields are missing, but we don't 400 here
    so users can still preview partial output.
    """
    template = get_template(filename)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"template not in catalog: {filename}",
        )

    result = fill_markdown(template.body, payload.fields)
    pdf_bytes = _render_markdown_to_pdf_bytes(result.markdown)

    # Strip the .md extension for a friendlier download filename.
    download_name = filename.removesuffix(".md") + ".pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


def _extract_field_names(body: str) -> list[str]:
    """Re-exported for tests that want to assert placeholder ordering."""
    return _placeholder_names(body)
