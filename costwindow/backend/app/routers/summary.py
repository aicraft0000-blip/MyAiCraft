from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from app.dependencies import get_user_from_jwt
from app.database import get_db
from app.routers.processes import compute_spike_alert

router = APIRouter()


def compute_summary_from_calls(calls: list[dict]) -> dict:
    now         = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    week_start  = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    total_today = total_week = total_month = 0.0
    provider_costs: dict[str, float] = defaultdict(float)
    process_today:  dict[str, float] = defaultdict(float)
    process_counts: dict[str, int]   = defaultdict(int)
    daily:          dict[str, float] = defaultdict(float)

    for c in calls:
        ts   = datetime.fromisoformat(c["called_at"].replace("Z", "+00:00"))
        cost = float(c["cost_usd"])
        lbl  = c.get("process_label", "unknown")
        prov = c.get("provider", "unknown")
        day  = ts.strftime("%Y-%m-%d")
        is_sub = c.get("billing_type") == "subscription"

        if ts >= today_start:
            if not is_sub:
                total_today        += cost
            process_today[lbl] += cost

        if ts >= week_start:
            if not is_sub:
                total_week += cost

        if ts >= month_start:
            process_counts[lbl] += 1
            if not is_sub:
                total_month          += cost
                provider_costs[prov] += cost
                daily[day]           += cost

    most_expensive = None
    if process_today:
        top = max(process_today, key=process_today.get)
        most_expensive = {"label": top, "cost_usd": round(process_today[top], 8)}

    most_active = None
    if process_counts:
        top = max(process_counts, key=process_counts.get)
        most_active = {"label": top, "call_count": process_counts[top]}

    cost_by_day = [
        {
            "date": (now - timedelta(days=29 - i)).strftime("%Y-%m-%d"),
            "cost_usd": round(
                daily.get((now - timedelta(days=29 - i)).strftime("%Y-%m-%d"), 0.0), 8
            ),
        }
        for i in range(30)
    ]

    return {
        "total_cost_today":       round(total_today,  8),
        "total_cost_this_week":   round(total_week,   8),
        "total_cost_this_month":  round(total_month,  8),
        "most_expensive_process": most_expensive,
        "most_active_process":    most_active,
        "cost_by_provider":       {k: round(v, 8) for k, v in provider_costs.items()},
        "cost_by_day":            cost_by_day,
    }


def add_subscription_summary(
    summary: dict,
    subscriptions: list[dict],
    processes_inactive: int,
) -> dict:
    active_subs = [s for s in subscriptions if s.get("is_active", True)]
    inactive_subs = len(subscriptions) - len(active_subs)
    total_monthly = sum(float(s["cost_gbp"]) for s in active_subs)
    summary["subscriptions_monthly_gbp"] = round(total_monthly, 2)
    summary["subscriptions_count"] = len(active_subs)
    summary["kill_switches_active"] = processes_inactive + inactive_subs
    return summary


@router.get("/summary")
def get_summary(user_id: str = Depends(get_user_from_jwt)):
    db  = get_db()
    now = datetime.now(timezone.utc)

    settings_row = db.table("user_settings").select("spike_threshold").eq("user_id", user_id).execute()
    threshold = float(settings_row.data[0]["spike_threshold"]) if settings_row.data else 2.0

    since = (now - timedelta(days=30)).isoformat()
    raw = (
        db.table("api_calls")
        .select("cost_usd, called_at, provider, processes(label, billing_type)")
        .eq("user_id", user_id)
        .gte("called_at", since)
        .execute()
        .data or []
    )
    calls = [
        {
            "cost_usd":      c["cost_usd"],
            "called_at":     c["called_at"],
            "provider":      c["provider"],
            "process_label": (c.get("processes") or {}).get("label", "unknown"),
            "billing_type":  (c.get("processes") or {}).get("billing_type", "api"),
        }
        for c in raw
    ]
    summary = compute_summary_from_calls(calls)

    # Spike list
    procs = db.table("processes").select("id, label").eq("user_id", user_id).execute().data or []
    all_calls = (
        db.table("api_calls")
        .select("process_id, cost_usd, called_at")
        .eq("user_id", user_id)
        .gte("called_at", (now - timedelta(days=35)).isoformat())
        .execute()
        .data or []
    )
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

    spike_list = []
    for p in procs:
        pid = p["id"]

        def _ts(c, _ts=today_start):
            return datetime.fromisoformat(c["called_at"].replace("Z", "+00:00"))

        today_cost   = sum(float(c["cost_usd"]) for c in all_calls if c["process_id"] == pid and _ts(c) >= today_start)
        history_cost = sum(float(c["cost_usd"]) for c in all_calls if c["process_id"] == pid and today_start - timedelta(days=7) <= _ts(c) < today_start)
        seven_day_avg = history_cost / 7.0

        if compute_spike_alert(today=today_cost, seven_day_avg=seven_day_avg, threshold=threshold):
            spike_list.append(p["label"])

    summary["any_spikes"] = len(spike_list) > 0
    summary["spike_list"] = spike_list

    # Subscription totals
    subs = (
        db.table("subscriptions")
        .select("cost_gbp, is_active")
        .eq("user_id", user_id)
        .execute()
        .data or []
    )
    inactive_processes = sum(
        1 for p in (db.table("processes").select("is_active").eq("user_id", user_id).execute().data or [])
        if not p.get("is_active", True)
    )
    summary = add_subscription_summary(summary, subs, inactive_processes)

    # Unpriced calls in the last 30 days — models we have no price for are
    # recorded at $0 and flagged, so a runaway on an unknown model is visible
    # rather than silently free.
    unpriced = (
        db.table("api_calls")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .contains("metadata", {"unpriced": True})
        .gte("called_at", since)
        .execute()
    )
    summary["unpriced_calls_30d"] = unpriced.count or 0

    return summary
