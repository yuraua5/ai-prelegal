"""HTTP routes for browsing the template catalog."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .schemas import TemplateDetail, TemplateSummary
from .templates_loader import get_template, list_templates

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateSummary])
def api_list_templates() -> list[TemplateSummary]:
    """List every template in catalog.json (no body, just metadata).

    The frontend uses this to render the template picker.
    """
    return [
        TemplateSummary(name=t.name, description=t.description, filename=t.filename)
        for t in list_templates()
    ]


@router.get("/{filename}", response_model=TemplateDetail)
def api_get_template(filename: str) -> TemplateDetail:
    """Return one template's body + extracted field list.

    Raises 404 if the filename is not in catalog.json. Catalogued filenames
    always have a backing file on disk by virtue of scripts/check_templates.py.
    """
    template = get_template(filename)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"template not in catalog: {filename}",
        )
    return TemplateDetail(
        name=template.name,
        description=template.description,
        filename=template.filename,
        body=template.body,
        fields=template.fields,
    )
