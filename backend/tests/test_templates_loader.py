"""Unit tests for the template loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import templates_loader as loader

# Use the real templates/ directory shipped in step-01.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"


@pytest.fixture(autouse=True)
def _clear_loader_cache() -> None:
    loader.reset_cache()


def test_list_templates_returns_all_catalog_entries() -> None:
    import json

    catalog = json.loads((REPO_ROOT / "catalog.json").read_text(encoding="utf-8"))
    expected_filenames = {entry["filename"] for entry in catalog}

    templates = loader.list_templates()
    actual_filenames = {t.filename for t in templates}

    assert actual_filenames == expected_filenames
    assert len(templates) == len(catalog)


def test_template_metadata_matches_catalog() -> None:
    import json

    catalog = json.loads((REPO_ROOT / "catalog.json").read_text(encoding="utf-8"))
    by_filename = {entry["filename"]: entry for entry in catalog}

    for t in loader.list_templates():
        meta = by_filename[t.filename]
        assert t.name == meta["name"]
        assert t.description == meta["description"]


def test_mutual_nda_extracts_expected_fields() -> None:
    """Smoke: a real template should yield at least the canonical MNDA fields."""
    template = loader.get_template("Mutual-NDA.md")
    assert template is not None
    # The exact field list is curated by CommonPaper; assert presence of the
    # well-known fields rather than every one, so the test survives minor
    # upstream edits.
    expected = {"Purpose", "Effective Date", "MNDA Term", "Governing Law", "Jurisdiction"}
    assert expected.issubset(set(template.fields)), (
        f"missing fields: {expected - set(template.fields)}"
    )


def test_get_template_unknown_returns_none() -> None:
    assert loader.get_template("NotARealTemplate.md") is None


def test_placeholder_names_are_unique_and_ordered() -> None:
    template = loader.get_template("Mutual-NDA.md")
    assert template is not None
    fields = template.fields
    assert len(fields) == len(set(fields)), "duplicate field names in template"
    # Ordered by first occurrence in document body.
    import re

    body = template.body
    first_idx: dict[str, int] = {}
    for match in re.finditer(
        r'<span\s+class="coverpage_link"\s*>([^<]+)</span>', body, re.IGNORECASE
    ):
        name = match.group(1).strip()
        if name not in first_idx:
            first_idx[name] = match.start()
    sorted_names = sorted(first_idx, key=lambda n: first_idx[n])
    assert fields == sorted_names


def test_placeholder_extraction_handles_minimal_input() -> None:
    """Pure unit test: loader parses placeholders from a synthetic body."""
    body = (
        "# Title\n"
        'Some intro <span class="coverpage_link">Party A</span> text '
        'and <span class="coverpage_link">Purpose</span> more text.\n'
        'Then <span class="coverpage_link">Party A</span> again.\n'
    )
    fields = loader._placeholder_names(body)
    assert fields == ["Party A", "Purpose"]
