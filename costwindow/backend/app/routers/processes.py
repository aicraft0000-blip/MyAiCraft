from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from app.dependencies import get_user_from_jwt, get_user_from_api_key_or_jwt
from app.database import get_db
from app.budgets import compute_price_tag, budget_state
from app.plans import resolve_user_plan, can_add_process, count_processes, FREE_PROCESS_LIMIT
from app.models import ProcessToggleRequest, AddProcessRequest, ProcessLinkRequest

router = APIRouter()


def compute_spike_alert(today: float, seven_day_avg: float, threshold: float = 2.0) -> bool:
    if seven_day_avg <= 0 or today <= 0:
        return False
    return today >= threshold * seven_day_avg


def _build_stats(calls: list[dict], process_id: str, now: datetime, threshold: float) -> dict:
    today_start  = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    month_start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    week_ago     = today_start - timedelta(days=7)

    mine = [c for c in calls if c["process_id"] == process_id]

    def _ts(c):
        return datetime.fromisoformat(c["called_at"].replace("Z", "+00:00"))

    today_calls   = [c for c in mine if _ts(c) >= today_start]
    month_calls   = [c for c in mine if _ts(c) >= month_start]
    history_calls = [c for c in mine if week_ago <= _ts(c) < today_start]

    today_cost    = sum(float(c["cost_usd"]) for c in today_calls)
    month_cost    = sum(float(c["cost_usd"]) for c in month_calls)
    total_cost    = sum(float(c["cost_usd"]) for c in mine)
    seven_day_avg = sum(float(c["cost_usd"]) for c in history_calls) / 7.0

    last_called = max((_ts(c) for c in mine), default=None)
    last_model  = mine[-1]["model"] if mine else None

    tokens_today  = sum(c.get("input_tokens", 0) + c.get("output_tokens", 0) for c in today_calls)
    tokens_month  = sum(c.get("input_tokens", 0) + c.get("output_tokens", 0) for c in month_calls)

    return {
        "today_cost_usd":      round(today_cost,  8),
        "this_month_cost_usd": round(month_cost,  8),
        "total_cost_usd":      round(total_cost,  8),
        "call_count_today":    len(today_calls),
        "call_count_month":    len(month_calls),
        "tokens_today":        tokens_today,
        "tokens_month":        tokens_month,
        "last_called_at":      last_called.isoformat() if last_called else None,
        "last_model":          last_model,
        "spike_alert":         compute_spike_alert(today_cost, seven_day_avg, threshold),
    }


@router.get("/processes")
def list_processes(user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    now = datetime.now(timezone.utc)

    settings_row = db.table("user_settings").select("spike_threshold").eq("user_id", user_id).execute()
    threshold = float(settings_row.data[0]["spike_threshold"]) if settings_row.data else 2.0

    procs = db.table("processes").select("*").eq("user_id", user_id).execute().data or []
    if not procs:
        return []

    since = (now - timedelta(days=35)).isoformat()
    calls = (
        db.table("api_calls")
        .select("process_id, cost_usd, called_at, model, input_tokens, output_tokens")
        .eq("user_id", user_id)
        .gte("called_at", since)
        .execute()
        .data or []
    )

    out = []
    for p in procs:
        stats = _build_stats(calls, p["id"], now, threshold)
        mine = [c for c in calls if c["process_id"] == p["id"]]
        budget = float(p["budget_usd_month"]) if p.get("budget_usd_month") else None
        out.append(
            {"id": p["id"], "label": p["label"], "provider": p["provider"],
             "description": p.get("description"), "is_active": p["is_active"],
             "billing_type": p.get("billing_type", "api"),
             "subscription_id": p.get("subscription_id"),
             "created_at": p["created_at"],
             "cost_driver": p.get("cost_driver", "scheduled"),
             "budget_usd_month": budget,
             "budget_action": p.get("budget_action", "warn"),
             "blocked_reason": p.get("blocked_reason"),
             "blocked_at": p.get("blocked_at"),
             **compute_price_tag(mine, now),
             "budget": budget_state(stats["this_month_cost_usd"], budget),
             **stats}
        )
    return out


@router.post("/processes")
def create_process(req: AddProcessRequest, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    plan = resolve_user_plan(db, user_id)
    if not can_add_process(plan, count_processes(db, user_id)):
        raise HTTPException(
            status_code=403,
            detail=(
                f"The free plan tracks {FREE_PROCESS_LIMIT} processes (every feature included). "
                "Upgrade at costwindow.com for unlimited processes."
            ),
        )
    row = {
        "user_id": user_id,
        "label": req.label,
        "provider": req.provider,
        "description": req.description,
        "billing_type": req.billing_type or "api",
    }
    if req.subscription_id:
        row["subscription_id"] = req.subscription_id
    result = db.table("processes").insert(row).execute()
    return result.data[0]


@router.patch("/processes/{process_id}/link")
def link_process(
    process_id: str,
    req: ProcessLinkRequest,
    user_id: str = Depends(get_user_from_jwt),
):
    db = get_db()
    existing = db.table("processes").select("id").eq("id", process_id).eq("user_id", user_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Process not found")
    updates: dict = {}
    if req.subscription_id is not None:
        updates["subscription_id"] = req.subscription_id if req.subscription_id else None
        updates["billing_type"] = "subscription" if req.subscription_id else "api"
    if req.billing_type is not None:
        updates["billing_type"] = req.billing_type
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    result = db.table("processes").update(updates).eq("id", process_id).execute()
    return result.data[0]


@router.patch("/processes/{process_id}")
def toggle_process(
    process_id: str,
    req: ProcessToggleRequest,
    user_id: str = Depends(get_user_from_jwt),
):
    if req.is_active is False and not req.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to disable a process")

    updates: dict = {}
    if req.is_active is not None:
        updates["is_active"] = req.is_active
        if req.is_active:
            # Manual re-enable clears any budget block
            updates["blocked_reason"] = None
            updates["blocked_at"] = None
    if req.budget_usd_month is not None:
        updates["budget_usd_month"] = req.budget_usd_month if req.budget_usd_month > 0 else None
    if req.budget_action is not None:
        if req.budget_action not in ("warn", "block"):
            raise HTTPException(status_code=400, detail="budget_action must be 'warn' or 'block'")
        updates["budget_action"] = req.budget_action
    if req.cost_driver is not None:
        if req.cost_driver not in ("scheduled", "demand"):
            raise HTTPException(status_code=400, detail="cost_driver must be 'scheduled' or 'demand'")
        updates["cost_driver"] = req.cost_driver
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    db = get_db()
    result = (
        db.table("processes")
        .update(updates)
        .eq("id", process_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Process not found")
    return result.data[0]


@router.get("/processes/{process_id}/history")
def process_history(process_id: str, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    now   = datetime.now(timezone.utc)
    since = (now - timedelta(days=30)).isoformat()

    calls = (
        db.table("api_calls")
        .select("cost_usd, called_at, is_manual")
        .eq("process_id", process_id)
        .eq("user_id", user_id)
        .gte("called_at", since)
        .execute()
        .data or []
    )

    daily: dict[str, dict] = {}
    for c in calls:
        day = c["called_at"][:10]
        if day not in daily:
            daily[day] = {"date": day, "cost_usd": 0.0, "call_count": 0}
        daily[day]["cost_usd"]   += float(c["cost_usd"])
        daily[day]["call_count"] += 1

    history = []
    for i in range(30):
        day = (now - timedelta(days=29 - i)).strftime("%Y-%m-%d")
        history.append(daily.get(day, {"date": day, "cost_usd": 0.0, "call_count": 0}))

    return {"process_id": process_id, "history": history}


def get_process_status_by_label(label: str, processes: list[dict]) -> bool:
    """Returns True (active) if label not found — fail open."""
    for p in processes:
        if p["label"] == label:
            return bool(p.get("is_active", True))
    return True


@router.get("/processes/status/{label}")
def process_status(label: str, user_id: str = Depends(get_user_from_api_key_or_jwt)):
    db = get_db()
    rows = db.table("processes").select("label, is_active").eq("user_id", user_id).execute().data or []
    return {"label": label, "is_active": get_process_status_by_label(label, rows)}
