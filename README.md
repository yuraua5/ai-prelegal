# ai-prelegal

A SaaS that lets users draft legal agreements from templates in `templates/`.

See `CLAUDE.md` for the full project brief (scope, stack, AI rules, color palette).

## Quick start

Requires Docker (Docker Desktop on Mac/Windows, Docker Engine on Linux).

```bash
# macOS
bash scripts/start-mac.sh           # build + run; waits for /healthz at :8000
bash scripts/stop-mac.sh

# Linux
bash scripts/start-linux.sh
bash scripts/stop-linux.sh

# Windows (PowerShell)
.\scripts\start-windows.ps1
.\scripts\stop-windows.ps1
```

The image is `prelegal:dev`. Templates and `catalog.json` are bind-mounted
from the repo so edits show up on restart without rebuilding.

## Local development

### Backend

Requires [uv](https://docs.astral.sh/uv/) (Python 3.12).

```bash
cd backend
uv sync --extra dev         # install deps
uv run dev                  # uvicorn --reload on :8000
uv run test                 # pytest
uv run lint                 # ruff check .
uv run typecheck            # mypy
```

### Frontend

Requires Node 20 (see `.nvmrc`).

```bash
cd frontend
npm install
npm run dev                 # vite dev server on :5173, proxies /api -> :8000
npm test                    # vitest
npm run lint                # eslint
npm run format              # prettier --write
npm run build               # vite build -> dist/
```

## Layout

```
backend/      FastAPI service (uv + pydantic-settings)
frontend/     React + Vite + TS
templates/    Markdown legal templates (curated, CC BY 4.0)   — added in step-01
scripts/      OS start/stop scripts                            — added in step-02
catalog.json  Template catalog                                 — added in step-01
.github/      CI workflows
Dockerfile, docker-compose.yml                                — added in step-02
```
