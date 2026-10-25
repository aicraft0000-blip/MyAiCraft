"""Provider balances — manual snapshots + reconciliation and runway.

These are hand-entered: the customer types their current provider console
balance after topping up, and CostWindow computes an estimated live balance
(snapshot minus tracked spend), runway at the trailing burn rate, and the
"honesty gap" between snapshots. There is deliberately no auto-fetch — no
provider offers a reliable public balance API (OpenAI removed theirs), so
pretending to auto-refresh would be dishonest. Every row is scoped to the
owning user.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.dependencies import get_user_from_jwt
from app.budgets import runway_days, reconcile
from app.models import BalanceEntryRequest

router = APIRouter()


def _api_spend_between(db, user_id: str, provider: str, start_iso: str, end_iso: str | None = None) -> float:
    """Tracked spend on pay-per-token (billing_type='api') processes for one provider."""
    q = (
        db.table("api_calls")
        .select("cost_usd, provider, processes(billing_type)")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .gte("called_at", start_iso)
    )
    if end_iso:
        q = q.lt("called_at", end_iso)
    rows = q.execute().data or []
    return sum(
        float(r["cost_usd"]) for r in rows
        if (r.get("processes") or {}).get("billing_type", "api") != "subscription"
    )


@router.post("/provider-balances/manual")
def record_manual_balance(req: BalanceEntryRequest, user_id: str = Depends(get_user_from_jwt)):
    """Type in your current provider balance after checking the console or
    topping up. Each entry is a snapshot — reconciliation and runway are
    computed against these in /provider-balances/latest."""
    if req.balance_usd < 0:
        raise HTTPException(status_code=400, detail="Balance cannot be negative")
    db = get_db()
    row = db.table("provider_balances").insert({
        "provider":    req.provider.lower(),
        "balance_usd": req.balance_usd,
        "user_id":     user_id,
        "source":      "manual",
    }).execute()
    return row.data[0]


@router.get("/provider-balances/latest")
def get_latest_balances(user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    now = datetime.now(timezone.utc)

    # Scoped to THIS user — the missing filter here was a cross-tenant leak.
    rows = (
        db.table("provider_balances")
        .select("*")
        .eq("user_id", user_id)
        .order("fetched_at", desc=True)
        .limit(100)
        .execute()
        .data or []
    )

    # Latest + previous snapshot per provider
    latest: dict[str, dict] = {}
    previous: dict[str, dict] = {}
    for row in rows:
        p = row["provider"]
        if p not in latest:
            latest[p] = row
        elif p not in previous:
            previous[p] = row

    balances = []
    for p, snap in latest.items():
        entry = dict(snap)
        snap_balance = float(snap["balance_usd"]) if snap.get("balance_usd") is not None else None

        # Spend tracked since the snapshot → estimated balance right now
        spent_since = _api_spend_between(db, user_id, p, snap["fetched_at"])
        est_balance = round(snap_balance - spent_since, 4) if snap_balance is not None else None
        entry["estimated_balance_usd"] = est_balance

        # Runway at the trailing 7-day burn rate
        week_ago = (now - timedelta(days=7)).isoformat()
        daily_burn = _api_spend_between(db, user_id, p, week_ago) / 7.0
        entry["daily_burn_usd"] = round(daily_burn, 4)
        entry["runway_days"] = runway_days(est_balance, daily_burn)

        # Honesty gap vs the previous snapshot
        prev = previous.get(p)
        if prev and prev.get("balance_usd") is not None and snap_balance is not None:
            tracked_between = _api_spend_between(
                db, user_id, p, prev["fetched_at"], snap["fetched_at"]
            )
            entry["reconciliation"] = reconcile(
                float(prev["balance_usd"]), snap_balance, tracked_between
            )
        else:
            entry["reconciliation"] = None

        balances.append(entry)

    return {"balances": balances}
