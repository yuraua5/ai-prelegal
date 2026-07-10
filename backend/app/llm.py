"""Anthropic client wrapper.

This module is the seam where AI features (step-12+) plug in. The actual
/chat endpoint is intentionally disabled in the prototype scope
(CLAUDE.md says "frontend-only prototype, no AI yet"), but the wrapper
below is fully implemented so future steps can flip the switch without
restructuring.

Design notes:
- The model is hard-pinned to claude-sonnet-4-6 per CLAUDE.md.
- We use Anthropic tool-use / structured output so the assistant's
  response is a JSON object we can validate into field values directly.
- Fail fast at construction time if ANTHROPIC_API_KEY is missing — we'd
  rather crash on first request than silently send 401s forever.
- The client is created lazily and cached in the module, mirroring
  how templates_loader exposes a single source of truth.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from .config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"

# Tool-use schema for the "extract fields" intent: the model receives a
# CommonPaper template body + an optional user request, and returns a
# {fields: {Display Name: value, ...}} object.
EXTRACT_FIELDS_TOOL: dict[str, Any] = {
    "name": "extract_fields",
    "description": (
        "Populate the placeholders of a CommonPaper legal template. "
        "Given the markdown body (with <span class='coverpage_link'>Name</span> "
        "placeholders) and any user context, return the values for each "
        "placeholder. Leave unknown placeholders out of the map."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fields": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Mapping of placeholder display name -> user value",
            }
        },
        "required": ["fields"],
    },
}


class AnthropicNotConfigured(RuntimeError):
    """Raised when the wrapper is asked to talk to Anthropic but the API
    key is not configured."""


@dataclass(frozen=True, slots=True)
class ExtractFieldsResult:
    """Tool-use result, validated."""

    fields: dict[str, str]
    raw: dict[str, Any]


_client: Any = None


def _set_client(client: Any) -> None:
    """Module-level setter — keeps the singleton in globals() without a `global` decl."""
    globals()["_client"] = client


def get_anthropic_client() -> Any:
    """Lazily build a singleton Anthropic client. Raises if the key is empty."""
    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise AnthropicNotConfigured(
            "ANTHROPIC_API_KEY is not set; copy .env.example to .env or export the "
            "variable before starting the backend."
        )

    # Imported lazily so that tests can construct the module without pulling
    # anthropic's network client during import time.
    from anthropic import Anthropic

    new_client = Anthropic(api_key=settings.anthropic_api_key)
    _set_client(new_client)
    return new_client


def reset_client() -> None:
    """Drop the cached client (tests use this after monkeypatching settings)."""
    _set_client(None)


def parse_extract_fields_response(tool_input: dict[str, Any] | str | None) -> ExtractFieldsResult:
    """Normalise Anthropic's tool-use payload into an ExtractFieldsResult.

    The SDK returns `input` either as a dict (when the model produced JSON)
    or as a JSON-encoded string. Tests replay recorded responses, so we
    handle both shapes.
    """
    if tool_input is None:
        raise ValueError("Anthropic tool-use response has no input")
    if isinstance(tool_input, str):
        try:
            parsed = json.loads(tool_input)
        except json.JSONDecodeError as exc:
            raise ValueError(f"tool input is not valid JSON: {exc}") from exc
    else:
        parsed = tool_input

    fields_obj = parsed.get("fields")
    if not isinstance(fields_obj, dict):
        raise ValueError("tool input is missing a 'fields' object")
    fields = {str(k): str(v) for k, v in fields_obj.items()}
    return ExtractFieldsResult(fields=fields, raw=parsed)


def extract_fields_from_user_input(
    template_body: str,
    placeholder_names: list[str],
    user_request: str,
    *,
    model: str = DEFAULT_MODEL,
) -> ExtractFieldsResult:
    """Ask the model to fill placeholders given the user request.

    Caller is responsible for passing the rendered template body and the
    list of placeholder display names so the model sees exactly what it
    needs to fill. The function returns the parsed result.
    """
    client = get_anthropic_client()
    placeholder_list = ", ".join(repr(n) for n in placeholder_names)
    prompt = (
        "You are assisting with a legal document drafting tool. The template "
        "below contains placeholders wrapped as "
        '<span class="coverpage_link">Display Name</span>.\n\n'
        f"Available placeholders (in document order): {placeholder_list}.\n\n"
        f"Template body:\n\n```markdown\n{template_body}\n```\n\n"
        f"User request:\n\n{user_request}\n\n"
        "Use the extract_fields tool to fill in every placeholder the user "
        "provided a value for. Leave out placeholders the user did not mention."
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        tools=[EXTRACT_FIELDS_TOOL],
        tool_choice={"type": "tool", "name": "extract_fields"},
        messages=[{"role": "user", "content": prompt}],
    )

    # Walk the response's content blocks looking for the tool use block.
    tool_input: dict[str, Any] | str | None = None
    for block in response.content:
        # duck-type the tool-use block to avoid importing the SDK type just for this
        if (
            getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == "extract_fields"
        ):
            tool_input = getattr(block, "input", None)
            break

    if tool_input is None:
        raise ValueError("Anthropic response did not include the extract_fields tool call")
    return parse_extract_fields_response(tool_input)
