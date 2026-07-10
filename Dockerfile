# syntax=docker/dockerfile:1.7

# ─── Stage 1: frontend build ───────────────────────────────────────────────────
FROM node:20-bookworm-slim AS frontend-build

WORKDIR /app/frontend

# Install deps first for better layer caching.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

# Build the static bundle.
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: backend deps ─────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS backend-deps

# uv is the only Python tool we need; installing it system-wide keeps the image
# small and avoids depending on a separate pip-based venv.
RUN pip install --no-cache-dir uv

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock* ./
# `uv sync --no-dev` would not work without a populated lockfile on first build,
# so we `uv pip install --system` the runtime deps directly.
# Dev deps (pytest, ruff, mypy) are not needed at runtime.
RUN uv pip install --system --no-cache \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic-settings>=2.5.0"

# ─── Stage 3: runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

# Curl is used by the start scripts' healthcheck; tini gives us proper signal
# forwarding so uvicorn shuts down cleanly on `docker compose stop`.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl tini \
 && rm -rf /var/lib/apt/lists/*

# Re-install uv + runtime deps in the final image.
RUN pip install --no-cache-dir uv \
 && uv pip install --system --no-cache \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic-settings>=2.5.0"

WORKDIR /app

# Backend code.
COPY backend/app ./backend/app

# Frontend build artefact.
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Repo-level assets the backend reads at runtime: catalog + templates.
COPY catalog.json ./
COPY templates ./templates

# Bind to 0.0.0.0 inside the container so the host can reach :8000.
ENV PYTHONUNBUFFERED=1 \
    PRELEGAL_HOST=0.0.0.0 \
    PRELEGAL_PORT=8000

EXPOSE 8000

# Smoke check that the server actually came up before we accept traffic.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
# Module path: backend/app/__init__.py + main.py (added in step-03).
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]