"""Tests for synthesis parsing helpers — the bits that turn model output into
storable Posts. The X-thread-as-list bug (Claude returning a list instead of a
string) broke a real run, so it's pinned here."""
from __future__ import annotations

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("BLOTATO_API_KEY", "test")
os.environ.setdefault("SUPABASE_URL", "http://test")
os.environ.setdefault("SUPABASE_KEY", "test")
os.environ.setdefault("RADARWINDOW_USER_ID", "test")


def _to_str(val) -> str:
    # Mirror of synthesis._to_str (kept inline to test the contract).
    if isinstance(val, list):
        return "\n\n".join(str(v) for v in val)
    return str(val) if val else ""


def test_list_joined_to_string():
    assert _to_str(["tweet one", "tweet two"]) == "tweet one\n\ntweet two"


def test_string_passthrough():
    assert _to_str("hello") == "hello"


def test_none_becomes_empty():
    assert _to_str(None) == ""


def test_empty_list():
    assert _to_str([]) == ""


# --- _load_json robustness (the parser that stopped a real run crashing) ---

from radarwindow.synthesis import _load_json  # noqa: E402


def test_load_clean_json():
    assert _load_json('{"a": 1}') == {"a": 1}


def test_load_strips_code_fences():
    assert _load_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_load_strips_trailing_comma():
    assert _load_json('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_load_isolates_object_from_prose():
    assert _load_json('Here you go:\n{"a": 1}\nHope that helps') == {"a": 1}


def test_load_repairs_truncation():
    # Unterminated string + missing braces (model hit max_tokens mid-output).
    out = _load_json('{"brief": "headline", "posts": {"x": "tweet')
    assert out["brief"] == "headline"


def test_load_raises_on_garbage():
    import pytest
    with pytest.raises(ValueError):
        _load_json("not json at all")


# --- prompt caching invariants (2026-08-23) ---
# The shared system prompt is the cache key: it must be deterministic, marked
# ephemeral, and big enough to clear Anthropic's 1024-token caching minimum
# (~4 chars/token). If an edit breaks any of these, caching silently stops.

from radarwindow.synthesis import _system_blocks  # noqa: E402


def test_system_block_is_deterministic():
    assert _system_blocks() == _system_blocks()


def test_system_block_is_cacheable():
    blocks = _system_blocks()
    assert len(blocks) == 1
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert len(blocks[0]["text"]) > 4300  # ≈1024 tokens — the Opus/Sonnet cache floor


def test_system_block_names_all_three_roles():
    text = _system_blocks()[0]["text"]
    for role in ("WRITER-GENERATE", "EDITOR", "WRITER-REVISE"):
        assert f"ROLE: {role}" in text
