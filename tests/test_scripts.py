"""Sanity tests for the OS-specific start/stop scripts.

These tests don't actually invoke docker; they just verify that the shell
scripts are syntactically valid (`bash -n`) and that the Windows PowerShell
scripts can be parsed by PowerShell if pwsh is available. If pwsh is not
installed, the Windows tests are skipped — the macOS/Linux paths are
still exercised on every CI run.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


SHELL_SCRIPTS = [
    "start-mac.sh",
    "stop-mac.sh",
    "start-linux.sh",
    "stop-linux.sh",
]

PS1_SCRIPTS = [
    "start-windows.ps1",
    "stop-windows.ps1",
]


@pytest.mark.parametrize("script_name", SHELL_SCRIPTS)
def test_bash_script_parses(script_name: str) -> None:
    """`bash -n` performs a syntactic check without executing the script."""
    if not shutil.which("bash"):
        pytest.skip("bash not available on PATH")
    script = SCRIPTS_DIR / script_name
    assert script.exists(), f"missing {script_name}"
    result = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"bash syntax error in {script_name}:\nstdout:{result.stdout}\nstderr:{result.stderr}"
    )


@pytest.mark.parametrize("script_name", PS1_SCRIPTS)
def test_powershell_script_present(script_name: str) -> None:
    """PowerShell scripts cannot be syntax-checked without `pwsh`, but at
    minimum we confirm the file exists, is non-empty, and references docker.
    """
    script = SCRIPTS_DIR / script_name
    assert script.exists(), f"missing {script_name}"
    text = script.read_text(encoding="utf-8")
    assert text.strip(), f"{script_name} is empty"
    assert "docker" in text, f"{script_name} should reference docker"


@pytest.mark.parametrize("script_name", PS1_SCRIPTS)
def test_powershell_script_parses(script_name: str) -> None:
    """If `pwsh` is installed, perform a full parse check."""
    if not shutil.which("pwsh"):
        pytest.skip("pwsh not available on PATH")
    script = SCRIPTS_DIR / script_name
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-Command",
            f"$null = [System.Management.Automation.Language.Parser]::ParseFile('{script}', [ref]$null, [ref]$null)",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"PowerShell parse error in {script_name}:\nstdout:{result.stdout}\nstderr:{result.stderr}"
    )


def test_all_shell_scripts_have_shebang() -> None:
    for script_name in SHELL_SCRIPTS:
        first_line = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("#!"), f"{script_name} missing shebang: {first_line!r}"


def test_all_shell_scripts_are_executable() -> None:
    """Shell scripts must be marked executable so `bash scripts/x.sh` works."""
    for script_name in SHELL_SCRIPTS:
        path = SCRIPTS_DIR / script_name
        import stat

        mode = path.stat().st_mode
        assert mode & stat.S_IXUSR, f"{script_name} is not executable (chmod +x needed)"


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not installed")
def test_docker_image_serves_healthz() -> None:
    """End-to-end smoke: build the prelegal:dev image and confirm it can
    serve /healthz from a minimal FastAPI app. This catches Dockerfile
    regressions (missing system packages, wrong Python, etc.) without
    needing the real backend/app/main.py which lands in step-03.
    """
    image = "prelegal:smoke-test"

    smoke_src = """
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
    smoke_path = REPO_ROOT / "tests" / "_smoke_app.py"
    smoke_path.write_text(smoke_src, encoding="utf-8")

    try:
        build = subprocess.run(
            [
                "docker",
                "build",
                "-t",
                image,
                "--target",
                "runtime",
                "-f",
                str(REPO_ROOT / "Dockerfile"),
                str(REPO_ROOT),
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=300,
        )
        assert build.returncode == 0, (
            f"docker build failed:\nstdout:{build.stdout}\nstderr:{build.stderr}"
        )

        container = "prelegal-smoke-test"
        run = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--name",
                container,
                "-p",
                "8001:8000",
                "-v",
                f"{smoke_path}:/app/_smoke_app.py:ro",
                image,
                "python",
                "/app/_smoke_app.py",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert run.returncode == 0, f"docker run failed: {run.stderr}"

        try:
            # Wait up to ~20s for /healthz.
            import time
            import urllib.request

            deadline = time.time() + 20
            last_err: Exception | None = None
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen("http://localhost:8001/healthz", timeout=2) as resp:
                        if resp.status == 200:
                            body = resp.read().decode()
                            assert body.strip() == '{"status":"ok"}', body
                            return
                except Exception as exc:
                    last_err = exc
                    time.sleep(1)
            pytest.fail(f"healthz never came up: {last_err}")
        finally:
            subprocess.run(["docker", "stop", container], capture_output=True, timeout=30)
    finally:
        if smoke_path.exists():
            smoke_path.unlink()
