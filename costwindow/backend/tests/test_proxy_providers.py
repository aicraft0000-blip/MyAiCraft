"""Tests for the multi-provider proxy: Bedrock usage parsing, dynamic-host
resolution (with SSRF guards), and pricing for the added providers."""
import pytest
from fastapi import HTTPException

from app.proxy_usage import extract_bedrock_usage, bedrock_model_from_path
from app.routers.proxy import _resolve_upstream, PROVIDERS
from app.pricing import calculate_cost, is_priced


# --- Bedrock Converse usage -------------------------------------------------

def test_bedrock_converse_usage():
    payload = {"usage": {"inputTokens": 1200, "outputTokens": 300, "totalTokens": 1500}}
    usage = extract_bedrock_usage(payload, model="anthropic.claude-3-5-sonnet-20241022-v2:0")
    assert usage["input_tokens"] == 1200
    assert usage["output_tokens"] == 300
    assert usage["model"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"


def test_bedrock_usage_with_cache_tokens():
    payload = {"usage": {"inputTokens": 10, "outputTokens": 5,
                         "cacheReadInputTokens": 40, "cacheWriteInputTokens": 20}}
    usage = extract_bedrock_usage(payload, model="anthropic.claude-sonnet-4")
    assert usage["cached_tokens"] == 40
    assert usage["cache_write_tokens"] == 20


def test_bedrock_no_usage_returns_none():
    assert extract_bedrock_usage({"output": {}}, "m") is None
    assert extract_bedrock_usage(None, "m") is None


def test_bedrock_model_from_path():
    assert bedrock_model_from_path("model/anthropic.claude-3-5-sonnet-20241022-v2:0/converse") \
        == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    assert bedrock_model_from_path("no-model-here") is None


# --- Dynamic host resolution + SSRF guards ----------------------------------

def test_static_provider_upstream_unchanged():
    base, path = _resolve_upstream("groq", "openai/v1/chat/completions")
    assert base == "https://api.groq.com"
    assert path == "openai/v1/chat/completions"


def test_azure_resolves_resource_host():
    base, path = _resolve_upstream("azure", "my-resource/openai/deployments/gpt-4o/chat/completions")
    assert base == "https://my-resource.openai.azure.com"
    assert path == "openai/deployments/gpt-4o/chat/completions"


def test_bedrock_resolves_region_host():
    base, path = _resolve_upstream("bedrock", "us-east-1/model/anthropic.claude-sonnet-4/converse")
    assert base == "https://bedrock-runtime.us-east-1.amazonaws.com"
    assert path == "model/anthropic.claude-sonnet-4/converse"


@pytest.mark.parametrize("bad", [
    "evil.com/x",              # dot in resource -> would escape the azure domain
    "a@evil.com/x",            # userinfo injection in the host segment
    "res:8080/x",             # port injection
    "/openai/only",            # empty resource
    "resource",                # no trailing path
])
def test_azure_rejects_malformed_resource(bad):
    with pytest.raises(HTTPException):
        _resolve_upstream("azure", bad)


@pytest.mark.parametrize("bad", [
    "evil.com/model/x/converse",   # not a region shape
    "us_east_1/model/x",           # underscore, not a real region
    "us-east-1",                   # no trailing path
])
def test_bedrock_rejects_malformed_region(bad):
    with pytest.raises(HTTPException):
        _resolve_upstream("bedrock", bad)


def test_all_suggested_providers_registered():
    for p in ("azure", "bedrock", "groq", "replicate", "openai", "anthropic", "google"):
        assert p in PROVIDERS


# --- Pricing for the new providers ------------------------------------------

def test_azure_uses_openai_prices():
    # Same model, same price whether called via openai or azure.
    assert calculate_cost("azure", "gpt-4o", 1_000_000, 0) == calculate_cost("openai", "gpt-4o", 1_000_000, 0)
    assert is_priced("azure", "gpt-4.1-mini")


def test_bedrock_claude_priced_with_and_without_geo_prefix():
    assert is_priced("bedrock", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    assert is_priced("bedrock", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    # 1M input tokens of Sonnet on Bedrock = $3.00 (Anthropic list).
    assert calculate_cost("bedrock", "us.anthropic.claude-3-5-sonnet-20241022-v2:0", 1_000_000, 0) == pytest.approx(3.0)


def test_hosted_inference_flagships_priced():
    assert is_priced("groq", "llama-3.3-70b-versatile")   # prefix match
    assert is_priced("mistral", "mistral-large-2411")
    assert is_priced("xai", "grok-4")
    assert is_priced("perplexity", "sonar-pro")


def test_unknown_hosted_model_is_unpriced_not_crash():
    # Long-tail models track tokens but are flagged unpriced (cost 0.0), never error.
    assert is_priced("together", "some/exotic-model") is False
    assert calculate_cost("together", "some/exotic-model", 500, 100) == 0.0
