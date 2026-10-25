from app.pricing import calculate_cost, PRICING


def test_all_required_models_present():
    assert "claude-opus-4-6" in PRICING["anthropic"]
    assert "claude-sonnet-4-6" in PRICING["anthropic"]
    assert "claude-haiku-4-5" in PRICING["anthropic"]
    assert "gpt-4o" in PRICING["openai"]
    assert "gpt-4o-mini" in PRICING["openai"]
    assert "gpt-4-turbo" in PRICING["openai"]


def test_sonnet_one_million_tokens_each():
    # $3.00 input + $15.00 output = $18.00 per MTok each
    cost = calculate_cost("anthropic", "claude-sonnet-4-6", 1_000_000, 1_000_000)
    assert abs(cost - 18.0) < 0.0001


def test_sonnet_small_horoscope_call():
    # 450 input, 180 output
    # input:  450 * (3.00 / 1_000_000)  = 0.00135
    # output: 180 * (15.00 / 1_000_000) = 0.00270
    # total = 0.00405
    cost = calculate_cost("anthropic", "claude-sonnet-4-6", 450, 180)
    assert abs(cost - 0.00405) < 1e-7


def test_cached_tokens_90_percent_discount():
    # 1000 input, 500 cached, 200 output, claude-sonnet-4-6
    # non-cached input: 500 * (3.00/1e6)        = 0.0015
    # cached input:     500 * (3.00/1e6) * 0.10 = 0.00015
    # output:           200 * (15.00/1e6)        = 0.0030
    # total = 0.00465
    cost = calculate_cost("anthropic", "claude-sonnet-4-6", 1000, 200, cached_tokens=500)
    assert abs(cost - 0.00465) < 1e-7


def test_gpt4o_cost():
    # $2.50 input + $10.00 output = $12.50 per MTok each
    cost = calculate_cost("openai", "gpt-4o", 1_000_000, 1_000_000)
    assert abs(cost - 12.5) < 0.0001


def test_gpt4o_mini_cost():
    # $0.15 + $0.60 = $0.75 per MTok each
    cost = calculate_cost("openai", "gpt-4o-mini", 1_000_000, 1_000_000)
    assert abs(cost - 0.75) < 0.0001


def test_opus_cost():
    # $5.00 + $25.00 = $30.00 per MTok each
    cost = calculate_cost("anthropic", "claude-opus-4-6", 1_000_000, 1_000_000)
    assert abs(cost - 30.0) < 0.0001


def test_haiku_cost():
    # $1.00 + $5.00 = $6.00 per MTok each
    cost = calculate_cost("anthropic", "claude-haiku-4-5", 1_000_000, 1_000_000)
    assert abs(cost - 6.0) < 0.0001


def test_unknown_model_returns_zero():
    cost = calculate_cost("anthropic", "nonexistent-model", 1000, 1000)
    assert cost == 0.0


def test_zero_tokens_returns_zero():
    cost = calculate_cost("anthropic", "claude-sonnet-4-6", 0, 0)
    assert cost == 0.0


def test_gemini_pricing_exists():
    from app.pricing import PRICING, calculate_cost
    assert "google" in PRICING
    cost = calculate_cost("google", "gemini-1.5-pro", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost > 0


def test_gemini_flash_pricing():
    import pytest
    from app.pricing import calculate_cost
    cost = calculate_cost("google", "gemini-1.5-flash", input_tokens=1_000_000, output_tokens=0)
    assert cost == pytest.approx(0.075, rel=0.01)


def test_cache_write_tokens_priced_at_premium():
    # Opus 4.6: input $5/MTok, cache writes at 1.25x = $6.25/MTok
    cost = calculate_cost("anthropic", "claude-opus-4-6", 0, 0, 0, cache_write_tokens=1_000_000)
    assert cost == 6.25


def test_cache_write_default_zero_keeps_old_behaviour():
    a = calculate_cost("anthropic", "claude-sonnet-4-6", 1000, 500)
    b = calculate_cost("anthropic", "claude-sonnet-4-6", 1000, 500, 0, 0)
    assert a == b


def test_full_agent_call_with_cache_read_and_write():
    # 100 fresh input, 10k cache read, 5k cache write, 1k output on Sonnet
    cost = calculate_cost("anthropic", "claude-sonnet-4-6", 100, 1000, cached_tokens=0,
                          cache_write_tokens=5000)
    expected = 100 * 3e-6 + 5000 * 3e-6 * 1.25 + 1000 * 15e-6
    assert abs(cost - expected) < 1e-9


# --- 2026-07 additions: unpriced flag + per-provider cache discount ---

from app.pricing import is_priced, CACHE_DISCOUNT


def test_is_priced_known_and_unknown():
    assert is_priced("anthropic", "claude-opus-4-8") is True
    assert is_priced("openai", "gpt-5") is True
    assert is_priced("google", "gemini-2.5-pro") is True
    assert is_priced("openai", "some-future-model-x") is False
    assert is_priced("nonprovider", "whatever") is False


def test_prefix_match_still_priced():
    assert is_priced("anthropic", "claude-sonnet-4-6-20251114") is True


def test_openai_cache_discount_higher_than_anthropic():
    # OpenAI cached tokens must not be undercounted with Anthropic's 0.10.
    assert CACHE_DISCOUNT["openai"] > CACHE_DISCOUNT["anthropic"]


def test_openai_current_models_priced():
    for m in ("gpt-5", "gpt-4.1", "o3", "gpt-4o"):
        assert is_priced("openai", m), m
