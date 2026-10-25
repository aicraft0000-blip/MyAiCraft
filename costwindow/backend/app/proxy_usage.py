"""Pure helpers for the drop-in proxy: extract token usage from provider
responses (JSON bodies and SSE streams). No I/O — unit-testable.

Normalised usage dict shape:
    {"model": str | None, "input_tokens": int, "output_tokens": int,
     "cached_tokens": int, "cache_write_tokens": int}
"""

import json


def _usage_dict(model=None, input_tokens=0, output_tokens=0,
                cached_tokens=0, cache_write_tokens=0) -> dict:
    return {
        "model": model,
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "cached_tokens": int(cached_tokens or 0),
        "cache_write_tokens": int(cache_write_tokens or 0),
    }


def extract_json_usage(provider: str, payload: dict) -> dict | None:
    """Extract usage from a non-streaming provider response body."""
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None

    if provider == "anthropic":
        # Anthropic's input_tokens excludes cache reads/writes — same
        # convention as the SDK wrapper and /ingest.
        return _usage_dict(
            model=payload.get("model"),
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            cached_tokens=usage.get("cache_read_input_tokens"),
            cache_write_tokens=usage.get("cache_creation_input_tokens"),
        )

    if provider == "openai":
        details = usage.get("prompt_tokens_details") or {}
        cached = details.get("cached_tokens") or 0
        prompt = usage.get("prompt_tokens") or 0
        # OpenAI's prompt_tokens INCLUDES cached tokens; store the split.
        return _usage_dict(
            model=payload.get("model"),
            input_tokens=max(prompt - cached, 0),
            output_tokens=usage.get("completion_tokens"),
            cached_tokens=cached,
        )

    return None


def extract_google_usage(payload: dict, model: str | None = None) -> dict | None:
    """Gemini uses `usageMetadata` and carries the model in the URL, not the
    body — so the model is passed in from the request path."""
    if not isinstance(payload, dict):
        return None
    meta = payload.get("usageMetadata")
    if not isinstance(meta, dict):
        return None
    prompt = int(meta.get("promptTokenCount") or 0)
    cached = int(meta.get("cachedContentTokenCount") or 0)
    return _usage_dict(
        model=model,
        input_tokens=max(prompt - cached, 0),
        output_tokens=meta.get("candidatesTokenCount"),
        cached_tokens=cached,
    )


def google_model_from_path(path: str) -> str | None:
    """Pull the model id out of a Gemini path like
    'v1beta/models/gemini-2.5-pro:generateContent'."""
    if "models/" not in path:
        return None
    tail = path.split("models/", 1)[1]
    return tail.split(":", 1)[0].split("/", 1)[0] or None


def extract_bedrock_usage(payload: dict, model: str | None = None) -> dict | None:
    """AWS Bedrock Converse API returns a normalised `usage` block
    (`inputTokens`/`outputTokens`) regardless of the underlying model. The
    model id lives in the URL path, not the body — so it's passed in."""
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    # Bedrock's cache token fields vary by API version; accept either spelling.
    cached = usage.get("cacheReadInputTokens", usage.get("cacheReadInputTokenCount")) or 0
    cache_write = usage.get("cacheWriteInputTokens", usage.get("cacheWriteInputTokenCount")) or 0
    return _usage_dict(
        model=model,
        input_tokens=usage.get("inputTokens"),
        output_tokens=usage.get("outputTokens"),
        cached_tokens=cached,
        cache_write_tokens=cache_write,
    )


def bedrock_model_from_path(path: str) -> str | None:
    """Pull the model id out of a Bedrock Converse/Invoke path like
    'model/anthropic.claude-3-5-sonnet-20241022-v2:0/converse'."""
    if "model/" not in path:
        return None
    tail = path.split("model/", 1)[1]
    return tail.split("/", 1)[0] or None


class SSEUsageAccumulator:
    """Feed raw SSE bytes as they stream through; read usage at the end.

    Anthropic: `message_start` carries model + input/cache tokens,
    `message_delta` carries cumulative output_tokens (last one wins).
    OpenAI: chunks carry the model; the final chunk carries `usage` when the
    caller set stream_options.include_usage (otherwise usage stays None).
    """

    def __init__(self, provider: str, model_hint: str | None = None):
        self.provider = provider
        self._buffer = b""
        self._model = model_hint
        self._input = 0
        self._output = 0
        self._cached = 0
        self._cache_write = 0
        self._saw_usage = False

    def feed(self, chunk: bytes) -> None:
        self._buffer += chunk
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            self._feed_line(line.strip())

    def _feed_line(self, line: bytes) -> None:
        if not line.startswith(b"data:"):
            return
        data = line[5:].strip()
        if not data or data == b"[DONE]":
            return
        try:
            event = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(event, dict):
            return
        if self.provider == "anthropic":
            self._feed_anthropic(event)
        elif self.provider == "openai":
            self._feed_openai(event)
        elif self.provider == "google":
            self._feed_google(event)

    def _feed_anthropic(self, event: dict) -> None:
        etype = event.get("type")
        if etype == "message_start":
            message = event.get("message") or {}
            usage = message.get("usage") or {}
            self._model = message.get("model") or self._model
            self._input = int(usage.get("input_tokens") or 0)
            self._cached = int(usage.get("cache_read_input_tokens") or 0)
            self._cache_write = int(usage.get("cache_creation_input_tokens") or 0)
            self._output = int(usage.get("output_tokens") or 0)
            self._saw_usage = True
        elif etype == "message_delta":
            usage = event.get("usage") or {}
            if usage.get("output_tokens") is not None:
                self._output = int(usage["output_tokens"])
                self._saw_usage = True

    def _feed_openai(self, event: dict) -> None:
        if event.get("model"):
            self._model = event["model"]
        usage = event.get("usage")
        if isinstance(usage, dict):
            details = usage.get("prompt_tokens_details") or {}
            cached = int(details.get("cached_tokens") or 0)
            prompt = int(usage.get("prompt_tokens") or 0)
            self._cached = cached
            self._input = max(prompt - cached, 0)
            self._output = int(usage.get("completion_tokens") or 0)
            self._saw_usage = True

    def _feed_google(self, event: dict) -> None:
        # Gemini streamGenerateContent emits usageMetadata on chunks; the last
        # one is cumulative. Model comes from the path (model_hint), not the body.
        meta = event.get("usageMetadata")
        if isinstance(meta, dict):
            prompt = int(meta.get("promptTokenCount") or 0)
            cached = int(meta.get("cachedContentTokenCount") or 0)
            self._cached = cached
            self._input = max(prompt - cached, 0)
            self._output = int(meta.get("candidatesTokenCount") or 0)
            self._saw_usage = True

    def result(self) -> dict | None:
        """Usage dict once the stream is finished, or None if the stream
        never carried usage data."""
        if not self._saw_usage:
            return None
        return _usage_dict(
            model=self._model,
            input_tokens=self._input,
            output_tokens=self._output,
            cached_tokens=self._cached,
            cache_write_tokens=self._cache_write,
        )


def blocked_error_body(provider: str, label: str, reason: str) -> dict:
    """Provider-shaped 403 body so official SDKs surface a clear error."""
    if reason == "free_plan_limit":
        # Cap gate — not a kill switch. Point at upgrade, never "re-enable".
        message = (
            f"CostWindow: cannot create process '{label}' — free plan is limited "
            "to 2 processes. Upgrade at costwindow.com for unlimited processes."
        )
    else:
        message = (
            f"CostWindow: process '{label}' is blocked ({reason}). "
            "Re-enable it in your dashboard at costwindow.com."
        )
    if provider == "anthropic":
        return {"type": "error", "error": {"type": "forbidden", "message": message}}
    return {"error": {"message": message, "type": "costwindow_blocked", "code": "process_blocked"}}
