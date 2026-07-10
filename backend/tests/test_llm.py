"""Tests for the Anthropic client wrapper.

We do NOT make live API calls — these tests replay recorded tool-use
payloads (the SDK response shapes documented by Anthropic) through the
parser. When the wrapper is finally wired into a route, integration
tests will mock the SDK client.
"""

from __future__ import annotations

import pytest

from app import llm
from app.config import Settings

# ── parse_extract_fields_response ─────────────────────────────────────────────


def test_parse_handles_dict_input() -> None:
    result = llm.parse_extract_fields_response(
        {"fields": {"Party A": "Acme", "Purpose": "evaluating"}}
    )
    assert result.fields == {"Party A": "Acme", "Purpose": "evaluating"}


def test_parse_handles_json_string_input() -> None:
    import json

    payload = json.dumps({"fields": {"Purpose": "evaluation"}})
    result = llm.parse_extract_fields_response(payload)
    assert result.fields == {"Purpose": "evaluation"}


def test_parse_coerces_values_to_str() -> None:
    """Models sometimes emit non-string values; the parser normalises."""
    result = llm.parse_extract_fields_response({"fields": {"Year": 2026}})
    assert result.fields == {"Year": "2026"}


def test_parse_rejects_missing_fields_object() -> None:
    with pytest.raises(ValueError, match="missing a 'fields' object"):
        llm.parse_extract_fields_response({"unrelated": "x"})


def test_parse_rejects_invalid_json_string() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        llm.parse_extract_fields_response("{not json")


def test_parse_rejects_none_input() -> None:
    with pytest.raises(ValueError, match="no input"):
        llm.parse_extract_fields_response(None)


# ── AnthropicNotConfigured on missing key ─────────────────────────────────────


def test_get_client_raises_when_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The wrapper must fail fast — never silently send 401s forever."""
    # Reset cached client from any prior test.
    llm.reset_client()
    # Force Settings to read an empty key regardless of the surrounding env.
    fake = Settings(anthropic_api_key="")
    monkeypatch.setattr(llm, "get_settings", lambda: fake)
    with pytest.raises(llm.AnthropicNotConfigured, match="ANTHROPIC_API_KEY"):
        llm.get_anthropic_client()
    llm.reset_client()


# ── extract_fields_from_user_input ────────────────────────────────────────────


def test_extract_fields_uses_recorded_tool_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replay a recorded Anthropic tool-use block through the wrapper."""

    class FakeToolBlock:
        type = "tool_use"
        name = "extract_fields"

        def __init__(self, payload: dict) -> None:
            self.input = payload

    class FakeTextBlock:
        type = "text"
        text = "Sure!"

    class FakeMessages:
        def __init__(self, payload: dict) -> None:
            self.content = [FakeTextBlock(), FakeToolBlock(payload)]

    class FakeClient:
        class messages:
            @staticmethod
            def create(**_kwargs: object) -> FakeMessages:
                return FakeMessages({"fields": {"Party A": "Acme", "Purpose": "evaluation"}})

    monkeypatch.setattr(llm, "_client", FakeClient())  # bypass lazy init
    llm.reset_client()  # but also let the wrapper accept our pre-built client
    monkeypatch.setattr(llm, "get_anthropic_client", lambda: FakeClient())

    result = llm.extract_fields_from_user_input(
        template_body='Hello <span class="coverpage_link">Party A</span>.',
        placeholder_names=["Party A", "Purpose"],
        user_request="The party is Acme; purpose is evaluation.",
    )
    assert result.fields == {"Party A": "Acme", "Purpose": "evaluation"}


def test_extract_fields_raises_when_no_tool_block(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the model replies with prose instead of the tool call, fail loud."""

    class BadMessages:
        content = [{"type": "text", "text": "I can't help with that."}]

    class FakeClient:
        class messages:
            @staticmethod
            def create(**_kwargs: object) -> BadMessages:
                return BadMessages()

    monkeypatch.setattr(llm, "get_anthropic_client", lambda: FakeClient())

    with pytest.raises(ValueError, match="did not include the extract_fields"):
        llm.extract_fields_from_user_input(
            template_body="X",
            placeholder_names=["A"],
            user_request="Y",
        )
