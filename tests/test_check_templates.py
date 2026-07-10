"""Tests for scripts/check_templates.py.

These run from the repo root (pytest is invoked from there in CI). They use
the real catalog.json and templates/ to confirm production state, plus a small
fixture-based roundtrip to confirm negative paths.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_templates.py"
TEMPLATES_DIR = REPO_ROOT / "templates"
CATALOG_PATH = REPO_ROOT / "catalog.json"
LICENSE_NOTICE_PATH = TEMPLATES_DIR / "LICENSE-NOTICE.md"


def test_check_templates_passes_on_real_tree() -> None:
    """The committed catalog.json + templates/ must satisfy the check."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"check failed:\nstdout:{result.stdout}\nstderr:{result.stderr}"
    assert "templates check OK" in result.stdout


def test_catalog_json_well_formed() -> None:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data, "catalog.json must list at least one template"
    for entry in data:
        assert set(entry.keys()) >= {"name", "description", "filename"}


def test_every_catalog_filename_is_a_real_file() -> None:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    on_disk = {p.name for p in TEMPLATES_DIR.glob("*.md")}
    catalog_filenames = {entry["filename"] for entry in data}
    missing = catalog_filenames - on_disk - {"LICENSE-NOTICE.md"}
    assert not missing, f"files referenced in catalog.json but missing on disk: {missing}"


def test_every_md_file_is_listed_in_catalog() -> None:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog_filenames = {entry["filename"] for entry in data}
    md_files = {p.name for p in TEMPLATES_DIR.glob("*.md")}
    orphans = (md_files - catalog_filenames) - {"LICENSE-NOTICE.md"}
    assert not orphans, f"templates/ files not listed in catalog.json: {orphans}"


def test_license_notice_present_and_mentions_cc() -> None:
    assert LICENSE_NOTICE_PATH.exists(), "LICENSE-NOTICE.md must exist in templates/"
    text = LICENSE_NOTICE_PATH.read_text(encoding="utf-8").lower()
    assert "cc by 4.0" in text or "creative commons" in text, (
        "license notice must mention CC BY 4.0 / Creative Commons"
    )


def test_check_fails_when_template_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A catalog referencing a file that doesn't exist must fail the check.

    We point the script at a tmp tree by monkeypatching module-level paths,
    invoking check() directly so we don't disturb the real repo.
    """
    import importlib

    mod = importlib.import_module("scripts.check_templates")
    importlib.reload(mod)

    fake_root = tmp_path
    (fake_root / "templates").mkdir()
    (fake_root / "templates" / "LICENSE-NOTICE.md").write_text("CC BY 4.0 applies.")
    (fake_root / "templates" / "Real.md").write_text("# Real\n\nok")
    (fake_root / "catalog.json").write_text(
        json.dumps(
            [
                {"name": "Real", "description": "exists", "filename": "Real.md"},
                {"name": "Ghost", "description": "missing", "filename": "Ghost.md"},
            ]
        )
    )

    monkeypatch.setattr(mod, "REPO_ROOT", fake_root)
    monkeypatch.setattr(mod, "TEMPLATES_DIR", fake_root / "templates")
    monkeypatch.setattr(mod, "CATALOG_PATH", fake_root / "catalog.json")
    monkeypatch.setattr(mod, "LICENSE_NOTICE_PATH", fake_root / "templates" / "LICENSE-NOTICE.md")

    errors = mod.check()
    assert errors, "expected at least one error when catalog references missing file"
    assert any("Ghost.md" in e for e in errors), (
        f"expected error to reference the missing Ghost.md file; got {errors}"
    )
