from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from app.models import IngestRequest, IngestResponse
from app.dependencies import get_user_from_api_key
from app.database import get_db
from app.pricing import calculate_cost, is_priced
from app.budgets import budget_state, should_block, budget_block_expired, month_start
from app.plans import resolve_user_plan, can_add_process, count_processes

router = APIRouter()


def check_process_active(process: dict) -> bool:
    return process.get("is_active", True)


def _month_to_date_cost(db, process_id: str, now: datetime) -> float:
    rows = (
        db.table("api_calls")
        .select("cost_usd")
        .eq("process_id", process_id)
        .gte("called_at", month_start(now).isoformat())
        .execute()
        .data or []
    )
    return sum(float(r["cost_usd"]) for r in rows)


@router.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest, user_id: str = Depends(get_user_from_api_key)):
    db = get_db()
    now = datetime.now(timezone.utc)

    existing = (
        db.table("processes")
        .select("id, is_active, billing_type, budget_usd_month, budget_action, blocked_reason, blocked_at")
        .eq("user_id", user_id)
        .eq("label", req.label)
        .execute()
    )

    billing_type = req.billing_type if req.billing_type in ('api', 'subscription') else 'api'

    if existing.data:
        process = existing.data[0]
        # Update billing_type if the hook sends a more accurate value
        if req.billing_type and process.get("billing_type") != billing_type:
            db.table("processes").update({"billing_type": billing_type}).eq("id", process["id"]).execute()
            process["billing_type"] = billing_type
    else:
        # Free tier: existing processes always keep ingesting; the cap only
        # gates auto-creation of new ones.
        plan = resolve_user_plan(db, user_id)
        if not can_add_process(plan, count_processes(db, user_id)):
            return IngestResponse(status="blocked", reason="free_plan_limit")
        created = db.table("processes").insert({
            "user_id": user_id,
            "label": req.label,
            "provider": req.provider,
            "billing_type": billing_type,
        }).execute()
        process = created.data[0]

    # Budget blocks auto-lift on the 1st of the month; manual kill switches don't.
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
            return IngestResponse(status="blocked", reason=process.get("blocked_reason") or "process_disabled")

    cost = calculate_cost(
        req.provider, req.model,
        req.input_tokens, req.output_tokens, req.cached_tokens,
        req.cache_write_tokens,
    )
    # Flag unpriced calls so a $0 cost is never silent — the dashboard surfaces
    # these so a runaway agent on a model we don't have a price for still shows up.
    metadata = dict(req.metadata) if req.metadata else {}
    if not is_priced(req.provider, req.model):
        metadata["unpriced"] = True

    called_at = req.called_at or now
    db.table("api_calls").insert({
        "process_id": process["id"],
        "user_id": user_id,
        "model": req.model,
        "input_tokens": req.input_tokens,
        "output_tokens": req.output_tokens,
        "cached_tokens": req.cached_tokens,
        "cache_write_tokens": req.cache_write_tokens,
        "cost_usd": cost,
        "provider": req.provider,
        "called_at": called_at.isoformat(),
        "metadata": metadata or None,
    }).execute()

    # Budget check — this call is recorded either way; a 'block' budget refuses the NEXT run.
    budget = float(process["budget_usd_month"]) if process.get("budget_usd_month") else None
    state = {"state": None, "used_pct": None}
    if budget:
        month_cost = _month_to_date_cost(db, process["id"], now)
        state = budget_state(month_cost, budget)
        if (
            process.get("billing_type", "api") == "api"
            and should_block(month_cost, budget, process.get("budget_action", "warn"))
        ):
            db.table("processes").update({
                "is_active": False,
                "blocked_reason": "budget_exceeded",
                "blocked_at": now.isoformat(),
            }).eq("id", process["id"]).execute()

    return IngestResponse(
        status="ok", cost_usd=cost, process_id=process["id"],
        budget_state=state["state"], budget_used_pct=state["used_pct"],
    )
