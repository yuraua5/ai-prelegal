"""Loads catalog.json + templates/*.md and exposes them to FastAPI routes.

Templates are CommonPaper markdown documents whose placeholders look like:

    <span class="coverpage_link">Field Display Name</span>

This module extracts placeholder names in document order (uniqueness preserved
by insertion order in a dict, so the JSON response field list is stable). The
regex is deliberately conservative — only matches the literal tag form CommonPaper
emits, so it won't accidentally pick up random `<span>` references in body text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# Resolve paths relative to repo root; works both inside Docker (/app) and
# local dev (repo root). The Docker image binds ./templates and ./catalog.json
# to these exact paths (see docker-compose.yml).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_PATH = REPO_ROOT / "catalog.json"
TEMPLATES_DIR = REPO_ROOT / "templates"

# Match exactly the coverpage_link span used by CommonPaper. Display name is a
# #1-3 #6 capture so we can warn (but not fail) on unexpected text inside.
_PLACEHOLDER_RE = re.compile(
    r'<span\s+class="coverpage_link"\s*>([^<]+)</span>',
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One row from catalog.json."""

    name: str
    description: str
    filename: str


@dataclass(frozen=True, slots=True)
class Template:
    """A loaded template: metadata + body + the list of placeholder names."""

    name: str
    description: str
    filename: str
    body: str
    fields: list[str] = field(default_factory=list)


def _read_catalog() -> list[CatalogEntry]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"catalog.json not found at {CATALOG_PATH}")
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("catalog.json must be a JSON array")
    entries: list[CatalogEntry] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"catalog[{i}] must be an object")
        try:
            entries.append(
                CatalogEntry(
                    name=str(item["name"]),
                    description=str(item["description"]),
                    filename=str(item["filename"]),
                )
            )
        except KeyError as exc:
            raise ValueError(f"catalog[{i}] missing required key: {exc}") from exc
    return entries


def _placeholder_names(body: str) -> list[str]:
    """Return placeholder display names in document order, deduplicated."""
    seen: set[str] = set()
    out: list[str] = []
    for match in _PLACEHOLDER_RE.finditer(body):
        name = match.group(1).strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _load_template_body(filename: str) -> str:
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"template file missing: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_templates() -> tuple[Template, ...]:
    """Load all templates once at startup; cache for the process lifetime."""
    entries = _read_catalog()
    out: list[Template] = []
    for entry in entries:
        body = _load_template_body(entry.filename)
        out.append(
            Template(
                name=entry.name,
                description=entry.description,
                filename=entry.filename,
                body=body,
                fields=_placeholder_names(body),
            )
        )
    return tuple(out)


def list_templates() -> list[Template]:
    """Public view of all loaded templates (metadata + body + fields)."""
    return list(_load_templates())


def get_template(filename: str) -> Template | None:
    """Return one template by filename, or None if not in the catalog."""
    for t in _load_templates():
        if t.filename == filename:
            return t
    return None


def reset_cache() -> None:
    """Clear the template cache. Tests use this after monkeypatching paths."""
    _load_templates.cache_clear()
