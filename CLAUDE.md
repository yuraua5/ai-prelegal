# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Prelegal Project

## Overview

SaaS product that lets users draft legal agreements from templates in `templates/`. The user interacts with an AI chat to determine which document to draft and how to populate its fields. The available documents are described in `catalog.json` at the project root.

The current scope is a **frontend-only prototype** supporting only the Mutual NDA document, with no AI chat yet.

## One-Time Data Curation (must be done before feature work)

Prepare the `templates/` data:

1. Browse the [CommonPaper](https://github.com/CommonPaper) GitHub account (e.g. [Mutual-NDA](https://github.com/CommonPaper/Mutual-NDA)). Review all of CommonPaper's repos and retrieve all markdown legal-agreement templates.
2. Place all markdown files in `templates/` in the project root.
3. Create `catalog.json` in the project root with `name`, `description`, and `filename` for each markdown file in `templates/`.
4. Add a text file in `templates/` stating that everything in that directory is under the **CC BY 4.0** license.

## Development Process

When asked to build a feature:

1. Read the feature instructions from Jira via Atlassian tools.
2. Develop the feature — do not skip any step of the feature-dev 7-step process.
3. Write unit and integration tests; fix issues until they pass.
4. Submit a PR using GitHub tools.

## AI / LLM Usage

- Call LLMs via the **Anthropic Claude API directly** — no OpenRouter, no Cerebras.
- Use a current Claude model (e.g. `claude-sonnet-4-6`).
- Use Anthropic structured output / tool use so results can be reliably parsed to populate legal-document fields.

## Technical Design

- The entire project is packaged into a **Docker container**.
- **Backend:** `backend/` — a `uv` project using FastAPI.
- **Frontend:** `frontend/`.
- Prefer statically building the frontend and serving it via FastAPI when feasible.
- **Scripts in `scripts/`:**

  ```
  # Mac
  scripts/start-mac.sh
  scripts/stop-mac.sh

  # Linux
  scripts/start-linux.sh
  scripts/stop-linux.sh

  # Windows
  scripts/start-windows.ps1
  scripts/stop-windows.ps1
  ```

- Backend available at http://localhost:8000

## Color Scheme

| Role | Hex |
|---|---|
| Accent Yellow | `#ecad0a` |
| Blue Primary | `#209dd7` |
| Purple Secondary (submit buttons) | `#753991` |
| Dark Navy (headings) | `#032147` |
| Gray Text | `#888888` |
