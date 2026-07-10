# Stop Prelegal locally on Windows.

$ErrorActionPreference = 'Stop'

Set-Location -Path (Join-Path $PSScriptRoot '..')

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: docker is not installed or not on PATH."
    exit 1
}

Write-Host "Stopping Prelegal (docker compose down)..."
docker compose down

Write-Host "Prelegal stopped."