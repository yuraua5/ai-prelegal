# Start Prelegal locally on Windows using Docker Compose.
# Usage: .\scripts\start-windows.ps1 [-Rebuild]
#
# Requires Docker Desktop for Windows with the WSL 2 backend (recommended).
# Run from PowerShell in the repo root.

[CmdletBinding()]
param(
    [switch]$Rebuild
)

$ErrorActionPreference = 'Stop'

Set-Location -Path (Join-Path $PSScriptRoot '..')

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: docker is not installed or not on PATH. Install Docker Desktop for Windows first."
    exit 1
}

$rebuildFlag = ''
if ($Rebuild) { $rebuildFlag = '--build' }

Write-Host "Starting Prelegal (docker compose up -d $rebuildFlag)..."
docker compose up -d @rebuildFlag

Write-Host "Waiting for /healthz..."
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri 'http://localhost:8000/healthz' -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            Write-Host "Prelegal is up at http://localhost:8000"
            exit 0
        }
    } catch {
        # not ready yet, keep waiting
    }
    Start-Sleep -Seconds 1
}

Write-Error "ERROR: Prelegal did not become healthy in 30s. Recent logs:"
docker compose logs --tail=80 app
exit 1