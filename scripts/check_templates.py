"""Consistency check between catalog.json and the templates/ directory.

Run from the repo root:
    python scripts/check_templates.py
or as a script:
    python -m scripts.check_templates

Exits 0 if everything is consistent, 1 otherwise. Suitable for CI and for the
step-01 test suite (see tests/test_check_templates.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Resolve paths relative to the repo root (the parent of this script's parent).
REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
CATALOG_PATH = REPO_ROOT / "catalog.json"
LICENSE_NOTICE_PATH = TEMPLATES_DIR / "LICENSE-NOTICE.md"

REQUIRED_FIELDS = {"name", "description", "filename"}


def _read_catalog() -> list[dict[str, object]]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"catalog.json not found at {CATALOG_PATH}")
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("catalog.json must be a JSON array")
    return data


def _check_catalog_schema(entries: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"catalog[{i}] is not an object")
            continue
        missing = REQUIRED_FIELDS - entry.keys()
        if missing:
            errors.append(f"catalog[{i}] missing fields: {sorted(missing)}")
        filename = entry.get("filename")
        if filename and not isinstance(filename, str):
            errors.append(f"catalog[{i}].filename must be a string")
    return errors


def _list_template_files() -> set[str]:
    return {p.name for p in TEMPLATES_DIR.glob("*.md")}


def check() -> list[str]:
    """Run all checks and return a list of human-readable error messages."""
    errors: list[str] = []

    # The license notice is a real markdown file in templates/ but it is not a
    # legal-agreement template — it must be excluded from the catalog cross-check.
    expected_non_template_markdown = {"LICENSE-NOTICE.md"}

    # 1. License notice must be present.
    if not LICENSE_NOTICE_PATH.exists():
        errors.append(f"missing license notice at {LICENSE_NOTICE_PATH}")
    else:
        text = LICENSE_NOTICE_PATH.read_text(encoding="utf-8").lower()
        if "cc by 4.0" not in text and "creative commons" not in text:
            errors.append("license notice does not mention CC BY 4.0 / Creative Commons")

    # 2. catalog.json must be valid and complete.
    try:
        entries = _read_catalog()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        return [f"catalog.json: {exc}"]
    errors.extend(_check_catalog_schema(entries))

    # 3. Cross-check catalog ↔ disk.
    catalog_filenames: set[str] = {
        str(e["filename"])
        for e in entries
        if isinstance(e, dict) and "filename" in e and isinstance(e.get("filename"), str)
    }
    on_disk = _list_template_files()

    missing_on_disk = sorted(catalog_filenames - on_disk)
    if missing_on_disk:
        errors.append(
            "catalog references files not present in templates/: " + ", ".join(missing_on_disk)
        )

    orphans = sorted((on_disk - catalog_filenames) - expected_non_template_markdown)
    if orphans:
        errors.append(
            "templates/ contains markdown files not listed in catalog.json: " + ", ".join(orphans)
        )

    # 4. No duplicate filenames in catalog.
    seen: set[str] = set()
    duplicates: list[str] = []
    for e in entries:
        fn = e.get("filename")
        if isinstance(fn, str):
            if fn in seen:
                duplicates.append(fn)
            seen.add(fn)
    if duplicates:
        errors.append(f"catalog.json has duplicate filenames: {duplicates}")

    return errors


def main(argv: list[str] | None = None) -> int:
    errors = check()
    if errors:
        print("templates check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("templates check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
