"""Drop-in proxy for Anthropic and OpenAI.

Point a provider SDK's base URL at CostWindow and every call is tracked
automatically — no SDK, no code changes — and blocked processes / exceeded
budgets are refused *before* the provider is called (a hard kill switch,
not a cooperative one).

    Anthropic:  base_url = https://<backend>/proxy/anthropic/<cw_live_key>
    OpenAI:     base_url = https://<backend>/proxy/openai/<cw_live_key>/v1

Optional header `X-CostWindow-Label` names the process (defaults to
'proxy-anthropic' / 'proxy-openai'). The customer's own provider API key is
forwarded untouched; CostWindow never stores it.
"""

import hashlib
import json
import re
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.pricing import calculate_cost, is_priced
from app.budgets import budget_state, should_block, budget_block_expired
from app.plans import resolve_user_plan, can_add_process, count_processes
from app.proxy_usage import (
    SSEUsageAccumulator, extract_json_usage, extract_google_usage,
    extract_bedrock_usage, google_model_from_path, bedrock_model_from_path,
    blocked_error_body,
)
from app.routers.ingest import check_process_active, _month_to_date_cost

router = APIRouter()

# Each provider maps to an upstream host and a "wire" format — the response
# shape used to read token usage. Most hosted-inference providers speak the
# OpenAI wire format, so they share one parser. `dynamic` providers derive
# their host from the first path segment (Azure resource / AWS region) because
# the host is per-customer; those segments are strictly validated below to keep
# the authenticated proxy from being used as an open relay.
PROVIDERS: dict[str, dict] = {
    "anthropic":  {"upstream": "https://api.anthropic.com",                  "wire": "anthropic"},
    "openai":     {"upstream": "https://api.openai.com",                     "wire": "openai"},
    "google":     {"upstream": "https://generativelanguage.googleapis.com",  "wire": "google"},
    # OpenAI-compatible hosted inference — same wire format, own hosts.
    "groq":       {"upstream": "https://api.groq.com",                       "wire": "openai"},
    "together":   {"upstream": "https://api.together.xyz",                   "wire": "openai"},
    "openrouter": {"upstream": "https://openrouter.ai",                      "wire": "openai"},
    "fireworks":  {"upstream": "https://api.fireworks.ai",                   "wire": "openai"},
    "deepinfra":  {"upstream": "https://api.deepinfra.com",                  "wire": "openai"},
    "perplexity": {"upstream": "https://api.perplexity.ai",                  "wire": "openai"},
    "mistral":    {"upstream": "https://api.mistral.ai",                     "wire": "openai"},
    "xai":        {"upstream": "https://api.x.ai",                           "wire": "openai"},
    # Per-customer host: first path segment is the Azure resource / AWS region.
    "azure":      {"upstream": None, "wire": "openai",  "dynamic": "azure"},
    "bedrock":    {"upstream": None, "wire": "bedrock", "dynamic": "bedrock"},
    # Compute-billed: proxied for the kill switch + pass-through. Token cost is
    # flagged unpriced (Replicate bills by run time, not tokens).
    "replicate":  {"upstream": "https://api.replicate.com",                  "wire": None},
}

# Azure resource names: letters/digits/hyphens. AWS regions: e.g. us-east-1.
_AZURE_RESOURCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,62}$")
_AWS_REGION_RE = re.compile(r"^[a-z]{2}-[a-z-]+-\d{1,2}$")


def _resolve_upstream(provider: str, path: str) -> tuple[str, str]:
    """Return (upstream_base, forward_path). For dynamic providers the host is
    built from the first path segment, which is strictly validated."""
    cfg = PROVIDERS[provider]
    dyn = cfg.get("dynamic")
    if dyn == "azure":
        resource, _, rest = path.partition("/")
        if not _AZURE_RESOURCE_RE.match(resource) or not rest:
            raise HTTPException(
                status_code=400,
                detail="Azure needs base_url .../proxy/azure/<cw_key>/<resource> (SDK appends /openai/...).",
            )
        return f"https://{resource}.openai.azure.com", rest
    if dyn == "bedrock":
        region, _, rest = path.partition("/")
        if not _AWS_REGION_RE.match(region) or not rest:
            raise HTTPException(
                status_code=400,
                detail="Bedrock needs base_url .../proxy/bedrock/<cw_key>/<aws-region> (then /model/<id>/converse).",
            )
        return f"https://bedrock-runtime.{region}.amazonaws.com", rest
    return cfg["upstream"], path

# Headers never forwarded either direction.
_SKIP_REQUEST_HEADERS = {
    "host", "content-length", "connection", "accept-encoding",
    "x-costwindow-label",
}
_SKIP_RESPONSE_HEADERS = {
    "content-length", "content-encoding", "transfer-encoding", "connection",
}

_TIMEOUT = httpx.Timeout(600.0, connect=10.0)


def _user_from_key(db, cw_key: str) -> str:
    key_hash = hashlib.sha256(cw_key.encode()).hexdigest()
    result = db.table("api_keys").select("user_id").eq("key_hash", key_hash).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid CostWindow API key")
    try:
        db.table("api_keys").update({"last_used_at": "now()"}).eq("key_hash", key_hash).execute()
    except Exception:
        pass
    return result.data[0]["user_id"]


def _resolve_process(db, user_id: str, label: str, provider: str, now: datetime):
    """Find-or-create the process; returns (process, blocked_reason|None).

    Mirrors /ingest: budget blocks auto-lift on the 1st, manual kill
    switches don't; the free-tier cap gates only new-process creation.
    """
    existing = (
        db.table("processes")
        .select("id, is_active, billing_type, budget_usd_month, budget_action, blocked_reason, blocked_at")
        .eq("user_id", user_id)
        .eq("label", label)
        .execute()
    )
    if existing.data:
        process = existing.data[0]
    else:
        plan = resolve_user_plan(db, user_id)
        if not can_add_process(plan, count_processes(db, user_id)):
            return None, "free_plan_limit"
        created = db.table("processes").insert({
            "user_id": user_id,
            "label": label,
            "provider": provider,
            "billing_type": "api",
        }).execute()
        process = created.data[0]

    if not check_process_active(process):
        blocked_at = process.get("blocked_at")
        if process.get("blocked_reason") == "budget_exceeded" and blocked_at:
            blocked_dt = datetime.fromisoformat(blocked_at.replace("Z", "+00:00"))
            if budget_block_expired(blocked_dt, now):
                db.table("processes").update(
                    {"is_active": True, "blocked_reason": None, "blocked_at": None}
                ).eq("id", process["id"]).execute()
                process["is_active"] = True
        if not check_process_active(process):
            return process, process.get("blocked_reason") or "process_disabled"

    return process, None


def _record_usage(user_id: str, process: dict, provider: str, usage: dict) -> None:
    """Insert the api_calls row and enforce the budget (same rules as /ingest)."""
    db = get_db()
    now = datetime.now(timezone.utc)
    model = usage.get("model") or "unknown"
    cost = calculate_cost(
        provider, model,
        usage["input_tokens"], usage["output_tokens"],
        usage["cached_tokens"], usage["cache_write_tokens"],
    )
    metadata = {"via": "proxy"}
    if not is_priced(provider, model):
        metadata["unpriced"] = True
    db.table("api_calls").insert({
        "process_id": process["id"],
        "user_id": user_id,
        "model": model,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cached_tokens": usage["cached_tokens"],
        "cache_write_tokens": usage["cache_write_tokens"],
        "cost_usd": cost,
        "provider": provider,
        "called_at": now.isoformat(),
        "metadata": metadata,
    }).execute()

    budget = float(process["budget_usd_month"]) if process.get("budget_usd_month") else None
    if budget:
        month_cost = _month_to_date_cost(db, process["id"], now)
        if (
            process.get("billing_type", "api") == "api"
            and should_block(month_cost, budget, process.get("budget_action", "warn"))
        ):
            db.table("processes").update({
                "is_active": False,
                "blocked_reason": "budget_exceeded",
                "blocked_at": now.isoformat(),
            }).eq("id", process["id"]).execute()


async def _record_safely(user_id: str, process: dict, provider: str, usage: dict | None) -> None:
    """Best-effort recording — a tracking failure must never break the call."""
    if not usage:
        return
    try:
        await run_in_threadpool(_record_usage, user_id, process, provider, usage)
    except Exception as e:  # pragma: no cover
        print(f"[PROXY] Failed to record usage: {e}")


_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


@router.api_route(
    "/proxy/{provider}/{cw_key}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def proxy(provider: str, cw_key: str, path: str, request: Request):
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider '{provider}'. Supported: {', '.join(sorted(PROVIDERS))}.",
        )

    wire = PROVIDERS[provider]["wire"]
    # Resolve the upstream host (validates the resource/region for dynamic
    # providers) BEFORE creating a process, so a malformed path 400s cleanly.
    upstream_base, forward_path = _resolve_upstream(provider, path)
    if provider == "google":
        model_hint = google_model_from_path(forward_path)
    elif provider == "bedrock":
        model_hint = bedrock_model_from_path(forward_path)
    else:
        model_hint = None

    db = get_db()
    now = datetime.now(timezone.utc)
    user_id = await run_in_threadpool(_user_from_key, db, cw_key)
    label = request.headers.get("x-costwindow-label") or f"proxy-{provider}"

    process, blocked_reason = await run_in_threadpool(
        _resolve_process, db, user_id, label, provider, now
    )
    if blocked_reason:
        # The hard stop: refuse before the provider is ever called.
        return Response(
            content=json.dumps(blocked_error_body(wire, label, blocked_reason)),
            status_code=403,
            media_type="application/json",
        )

    upstream_url = f"{upstream_base}/{forward_path}"
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _SKIP_REQUEST_HEADERS
    }

    client = httpx.AsyncClient(timeout=_TIMEOUT)
    upstream_request = client.build_request(
        request.method, upstream_url,
        content=body if request.method in _MUTATING else None,
        headers=headers,
        params=dict(request.query_params),
    )
    try:
        upstream = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as e:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Upstream {provider} unreachable: {e}")

    response_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in _SKIP_RESPONSE_HEADERS
    }
    content_type = upstream.headers.get("content-type", "")
    # Track token-consuming calls only (POST/PUT that generate output); a
    # DELETE (e.g. cancel a batch) forwards but produces no usage row.
    track = request.method in {"POST", "PUT"} and upstream.status_code < 400

    if "text/event-stream" in content_type:
        accumulator = SSEUsageAccumulator(wire, model_hint=model_hint)

        async def stream():
            try:
                async for chunk in upstream.aiter_bytes():
                    if track:
                        accumulator.feed(chunk)
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()
                if track:
                    await _record_safely(user_id, process, provider, accumulator.result())

        return StreamingResponse(
            stream(),
            status_code=upstream.status_code,
            headers=response_headers,
            media_type="text/event-stream",
        )

    payload = await upstream.aread()
    await upstream.aclose()
    if track:
        try:
            parsed = json.loads(payload)
            if provider == "google":
                usage = extract_google_usage(parsed, model_hint)
            elif provider == "bedrock":
                usage = extract_bedrock_usage(parsed, model_hint)
            elif wire in ("anthropic", "openai"):
                usage = extract_json_usage(wire, parsed)
            else:
                usage = None  # compute-billed / non-token provider (e.g. replicate)
        except (ValueError, UnicodeDecodeError):
            usage = None
        await _record_safely(user_id, process, provider, usage)

    return Response(
        content=payload,
        status_code=upstream.status_code,
        headers=response_headers,
        background=BackgroundTask(client.aclose),
    )
