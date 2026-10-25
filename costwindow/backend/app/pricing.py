# Pricing per million tokens (MTok) in USD.
# To update prices: change the values in PRICING below and redeploy.
# Last reviewed: 2026-08-09.
PRICING: dict[str, dict[str, dict[str, float]]] = {
    "anthropic": {
        "claude-fable-5":             {"input": 10.00, "output": 50.00},
        "claude-mythos-5":            {"input": 10.00, "output": 50.00},
        "claude-opus-5":              {"input":  5.00, "output": 25.00},
        # Sonnet 5 is $2/$10 on an introductory rate through 2026-08-31, then
        # $3/$15. We track the standard rate: it slightly over-counts until the
        # intro expires, and under-counting a live budget is the worse failure.
        "claude-sonnet-5":            {"input":  3.00, "output": 15.00},
        "claude-opus-4-8":            {"input":  5.00, "output": 25.00},
        "claude-opus-4-7":            {"input":  5.00, "output": 25.00},
        "claude-opus-4-6":            {"input":  5.00, "output": 25.00},
        "claude-opus-4-5":            {"input":  5.00, "output": 25.00},
        "claude-sonnet-4-6":          {"input":  3.00, "output": 15.00},
        "claude-sonnet-4-5":          {"input":  3.00, "output": 15.00},
        "claude-haiku-4-5":           {"input":  1.00, "output":  5.00},
        "claude-haiku-4-5-20251001":  {"input":  1.00, "output":  5.00},
    },
    "openai": {
        # GPT-5 family (July 2026)
        "gpt-5.6-sol":    {"input":  5.00, "output": 30.00},
        "gpt-5.6-terra":  {"input":  2.50, "output": 15.00},
        "gpt-5.6-luna":   {"input":  1.00, "output":  6.00},
        "gpt-5.5":        {"input":  5.00, "output": 30.00},
        "gpt-5":          {"input":  1.25, "output": 10.00},
        # GPT-4.1 family
        "gpt-4.1":        {"input":  2.00, "output":  8.00},
        "gpt-4.1-mini":   {"input":  0.40, "output":  1.60},
        "gpt-4.1-nano":   {"input":  0.10, "output":  0.40},
        # Reasoning
        "o3":             {"input":  2.00, "output":  8.00},
        "o4-mini":        {"input":  1.10, "output":  4.40},
        # 4o (legacy but still served)
        "gpt-4o":         {"input":  2.50, "output": 10.00},
        "gpt-4o-mini":    {"input":  0.15, "output":  0.60},
        "gpt-4-turbo":    {"input": 10.00, "output": 30.00},
    },
    "google": {
        "gemini-2.5-pro":     {"input":  1.25,  "output": 10.00},
        "gemini-2.5-flash":   {"input":  0.30,  "output":  2.50},
        "gemini-2.0-flash":   {"input":  0.10,  "output":  0.40},
        "gemini-1.5-pro":     {"input":  3.50,  "output": 10.50},
        "gemini-1.5-flash":   {"input":  0.075, "output":  0.30},
    },
    # AWS Bedrock — keyed by the model-id prefix (region inference-profile
    # prefixes like "us."/"eu." are stripped in _rates). Claude-on-Bedrock
    # tracks Anthropic list prices; add others as you use them.
    "bedrock": {
        "anthropic.claude-opus-4":     {"input":  5.00, "output": 25.00},
        "anthropic.claude-sonnet-4":   {"input":  3.00, "output": 15.00},
        "anthropic.claude-3-5-sonnet": {"input":  3.00, "output": 15.00},
        "anthropic.claude-3-5-haiku":  {"input":  0.80, "output":  4.00},
        "anthropic.claude-3-haiku":    {"input":  0.25, "output":  1.25},
        "meta.llama3-3-70b":           {"input":  0.72, "output":  0.72},
        "meta.llama3-1-8b":            {"input":  0.22, "output":  0.22},
        "amazon.nova-pro":             {"input":  0.80, "output":  3.20},
        "amazon.nova-lite":            {"input":  0.06, "output":  0.24},
        "amazon.nova-micro":           {"input":  0.035, "output": 0.14},
    },
    # OpenAI-compatible hosted inference. Flagship rates only — verify against
    # each provider's current rate card; unlisted models track tokens and are
    # flagged 'unpriced' until added here.
    "groq": {
        "llama-3.3-70b":  {"input": 0.59, "output": 0.79},
        "llama-3.1-8b":   {"input": 0.05, "output": 0.08},
        "llama-3.1-70b":  {"input": 0.59, "output": 0.79},
        "mixtral-8x7b":   {"input": 0.24, "output": 0.24},
        "gemma2-9b":      {"input": 0.20, "output": 0.20},
    },
    "mistral": {
        "mistral-large":  {"input": 2.00, "output": 6.00},
        "mistral-small":  {"input": 0.20, "output": 0.60},
        "codestral":      {"input": 0.30, "output": 0.90},
        "ministral-8b":   {"input": 0.10, "output": 0.10},
        "ministral-3b":   {"input": 0.04, "output": 0.04},
    },
    "xai": {
        "grok-4":         {"input": 3.00, "output": 15.00},
        "grok-3":         {"input": 3.00, "output": 15.00},
        "grok-3-mini":    {"input": 0.30, "output": 0.50},
        "grok-2":         {"input": 2.00, "output": 10.00},
    },
    "perplexity": {
        "sonar-pro":        {"input": 3.00, "output": 15.00},
        "sonar-reasoning":  {"input": 1.00, "output":  5.00},
        "sonar":            {"input": 1.00, "output":  1.00},
    },
}

# Providers whose wire format and model catalogue mirror another provider's
# price sheet. Azure OpenAI serves the same models at the same list prices.
_PRICING_ALIAS: dict[str, str] = {
    "azure": "openai",
}

# Cached-input discount is provider-specific. A cached input token costs this
# fraction of the regular input price. Anthropic cache reads are ~0.10; OpenAI
# and Google discount less, so a single flat 0.10 undercounted non-Anthropic
# cached workloads. We err toward the higher (more conservative) multiplier —
# for a spend-control tool, over-counting is far safer than under-counting.
CACHE_DISCOUNT: dict[str, float] = {
    "anthropic": 0.10,
    "openai":    0.25,
    "google":    0.25,
}
DEFAULT_CACHE_DISCOUNT = 0.25

# Writing to the cache costs 25% MORE than regular input (Anthropic 5m-TTL rate).
# Agents that resend long conversations (Hermes, Claude Code) pay this constantly.
CACHE_WRITE_PREMIUM = 1.25


_BEDROCK_GEO_PREFIXES = ("us-gov.", "us.", "eu.", "apac.", "ap.")


def _rates(provider: str, model: str) -> dict | None:
    """Exact match, then longest known-prefix match (dated/suffixed ids)."""
    provider = _PRICING_ALIAS.get(provider, provider)
    provider_rates = PRICING.get(provider, {})
    if provider == "bedrock" and model:
        # Cross-region inference profiles prefix the id, e.g.
        # "us.anthropic.claude-3-5-sonnet-...". Strip it before matching.
        for geo in _BEDROCK_GEO_PREFIXES:
            if model.startswith(geo):
                model = model[len(geo):]
                break
    rates = provider_rates.get(model)
    if rates is None and model:
        prefixes = [known for known in provider_rates if model.startswith(known)]
        if prefixes:
            rates = provider_rates[max(prefixes, key=len)]
    return rates


def is_priced(provider: str, model: str) -> bool:
    """Whether we have a price for this provider/model — callers use this to
    flag an api_call as 'unpriced' so a $0 cost is visible, not silent."""
    return _rates(provider, model) is not None


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Return cost in USD. Returns 0.0 for unknown provider/model combinations
    (check is_priced() to detect and flag those — see the routers)."""
    rates = _rates(provider, model)
    if rates is None:
        print(f"[PRICING] Unknown model '{provider}/{model}' — recorded at $0 and FLAGGED unpriced. Add it to PRICING in pricing.py.")
        return 0.0

    per_token_in  = rates["input"]  / 1_000_000
    per_token_out = rates["output"] / 1_000_000
    cache_mult = CACHE_DISCOUNT.get(provider, DEFAULT_CACHE_DISCOUNT)

    non_cached = max(0, input_tokens - cached_tokens)
    cost = (
        non_cached           * per_token_in
        + cached_tokens      * per_token_in * cache_mult
        + cache_write_tokens * per_token_in * CACHE_WRITE_PREMIUM
        + output_tokens      * per_token_out
    )
    return round(cost, 10)
