import json

from app.proxy_usage import (
    SSEUsageAccumulator,
    blocked_error_body,
    extract_json_usage,
)


# --- extract_json_usage -------------------------------------------------

def test_anthropic_json_usage():
    payload = {
        "model": "claude-sonnet-4-6",
        "usage": {
            "input_tokens": 450,
            "output_tokens": 180,
            "cache_read_input_tokens": 1000,
            "cache_creation_input_tokens": 200,
        },
    }
    usage = extract_json_usage("anthropic", payload)
    assert usage == {
        "model": "claude-sonnet-4-6",
        "input_tokens": 450,
        "output_tokens": 180,
        "cached_tokens": 1000,
        "cache_write_tokens": 200,
    }


def test_openai_json_usage_splits_cached_from_prompt():
    payload = {
        "model": "gpt-4o",
        "usage": {
            "prompt_tokens": 1200,
            "completion_tokens": 90,
            "prompt_tokens_details": {"cached_tokens": 1000},
        },
    }
    usage = extract_json_usage("openai", payload)
    assert usage["input_tokens"] == 200   # prompt minus cached
    assert usage["cached_tokens"] == 1000
    assert usage["output_tokens"] == 90
    assert usage["model"] == "gpt-4o"


def test_openai_json_usage_without_details():
    payload = {"model": "gpt-4o-mini", "usage": {"prompt_tokens": 50, "completion_tokens": 5}}
    usage = extract_json_usage("openai", payload)
    assert usage["input_tokens"] == 50
    assert usage["cached_tokens"] == 0


def test_no_usage_returns_none():
    assert extract_json_usage("anthropic", {"model": "claude-sonnet-4-6"}) is None
    assert extract_json_usage("anthropic", {"usage": "bad"}) is None
    assert extract_json_usage("unknown", {"usage": {"input_tokens": 1}}) is None
    assert extract_json_usage("anthropic", None) is None


# --- SSE accumulator: Anthropic -----------------------------------------

def _sse(event_lines):
    return ("\n".join(event_lines) + "\n").encode()


def test_anthropic_sse_stream():
    acc = SSEUsageAccumulator("anthropic")
    acc.feed(_sse([
        "event: message_start",
        'data: {"type": "message_start", "message": {"model": "claude-sonnet-4-6", '
        '"usage": {"input_tokens": 300, "cache_read_input_tokens": 50, '
        '"cache_creation_input_tokens": 20, "output_tokens": 1}}}',
        "",
        "event: content_block_delta",
        'data: {"type": "content_block_delta", "delta": {"text": "hi"}}',
        "",
        "event: message_delta",
        'data: {"type": "message_delta", "usage": {"output_tokens": 42}}',
        "",
        "event: message_stop",
        'data: {"type": "message_stop"}',
    ]))
    usage = acc.result()
    assert usage["model"] == "claude-sonnet-4-6"
    assert usage["input_tokens"] == 300
    assert usage["cached_tokens"] == 50
    assert usage["cache_write_tokens"] == 20
    assert usage["output_tokens"] == 42  # message_delta wins over message_start


def test_anthropic_sse_split_across_chunks():
    """A data: line split mid-JSON across two network chunks still parses."""
    line = ('data: {"type": "message_start", "message": {"model": "m", '
            '"usage": {"input_tokens": 10, "output_tokens": 1}}}\n')
    acc = SSEUsageAccumulator("anthropic")
    acc.feed(line[:25].encode())
    acc.feed(line[25:].encode())
    acc.feed(b'data: {"type": "message_delta", "usage": {"output_tokens": 7}}\n')
    usage = acc.result()
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 7


# --- SSE accumulator: OpenAI --------------------------------------------

def test_openai_sse_with_include_usage():
    acc = SSEUsageAccumulator("openai")
    chunks = [
        {"model": "gpt-4o", "choices": [{"delta": {"content": "he"}}]},
        {"model": "gpt-4o", "choices": [{"delta": {"content": "llo"}}]},
        {"model": "gpt-4o", "choices": [],
         "usage": {"prompt_tokens": 100, "completion_tokens": 25,
                   "prompt_tokens_details": {"cached_tokens": 40}}},
    ]
    for c in chunks:
        acc.feed(f"data: {json.dumps(c)}\n\n".encode())
    acc.feed(b"data: [DONE]\n\n")
    usage = acc.result()
    assert usage["model"] == "gpt-4o"
    assert usage["input_tokens"] == 60
    assert usage["cached_tokens"] == 40
    assert usage["output_tokens"] == 25


def test_openai_sse_without_usage_returns_none():
    acc = SSEUsageAccumulator("openai")
    acc.feed(b'data: {"model": "gpt-4o", "choices": [{"delta": {"content": "x"}}]}\n\n')
    acc.feed(b"data: [DONE]\n\n")
    assert acc.result() is None


def test_malformed_sse_lines_ignored():
    acc = SSEUsageAccumulator("anthropic")
    acc.feed(b"data: {not json}\n")
    acc.feed(b"random garbage\n")
    acc.feed(b"data:\n")
    assert acc.result() is None


# --- blocked_error_body ---------------------------------------------------

def test_blocked_error_bodies_are_provider_shaped():
    a = blocked_error_body("anthropic", "my-agent", "budget_exceeded")
    assert a["type"] == "error"
    assert "my-agent" in a["error"]["message"]
    assert "budget_exceeded" in a["error"]["message"]
    assert "Re-enable" in a["error"]["message"]

    o = blocked_error_body("openai", "my-agent", "process_disabled")
    assert o["error"]["type"] == "costwindow_blocked"
    assert "my-agent" in o["error"]["message"]
    assert "Re-enable" in o["error"]["message"]

    f = blocked_error_body("anthropic", "third-agent", "free_plan_limit")
    assert "free plan is limited to 2 processes" in f["error"]["message"]
    assert "costwindow.com" in f["error"]["message"]
    assert "Re-enable" not in f["error"]["message"]


# --- 2026-07 additions: Google/Gemini usage + model-from-path ---

from app.proxy_usage import extract_google_usage, google_model_from_path


def test_google_json_usage():
    payload = {"usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 300, "cachedContentTokenCount": 200}}
    u = extract_google_usage(payload, "gemini-2.5-pro")
    assert u["model"] == "gemini-2.5-pro"
    assert u["input_tokens"] == 800   # prompt minus cached
    assert u["cached_tokens"] == 200
    assert u["output_tokens"] == 300


def test_google_no_usage_returns_none():
    assert extract_google_usage({"candidates": []}, "gemini-2.5-pro") is None


def test_google_model_from_path():
    assert google_model_from_path("v1beta/models/gemini-2.5-pro:generateContent") == "gemini-2.5-pro"
    assert google_model_from_path("v1beta/models/gemini-2.0-flash:streamGenerateContent") == "gemini-2.0-flash"
    assert google_model_from_path("v1beta/tunedModels/x") is None


def test_google_sse_accumulator():
    acc = SSEUsageAccumulator("google", model_hint="gemini-2.5-pro")
    acc.feed(b'data: {"usageMetadata":{"promptTokenCount":500,"candidatesTokenCount":120,"cachedContentTokenCount":0}}\n')
    r = acc.result()
    assert r["model"] == "gemini-2.5-pro"
    assert r["input_tokens"] == 500
    assert r["output_tokens"] == 120
