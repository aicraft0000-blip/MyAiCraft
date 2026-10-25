"""Pure helpers for v2 price tags, budgets and balance reconciliation.

No database access here — everything takes plain dicts/numbers so it can be
unit-tested like pricing.py and compute_spike_alert().
"""
from datetime import datetime, timezone, timedelta

WEEKS_PER_MONTH = 4.345


def month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def compute_price_tag(calls: list[dict], now: datetime, window_days: int = 30) -> dict:
    """Price tag for one process from its recent calls.

    Returns cost_per_run (trailing average), runs_per_week (observed frequency)
    and projected_month_usd (the number a budget holder actually needs).
    """
    since = now - timedelta(days=window_days)
    recent = [
        c for c in calls
        if datetime.fromisoformat(c["called_at"].replace("Z", "+00:00")) >= since
    ]
    if not recent:
        return {"cost_per_run_usd": 0.0, "runs_per_week": 0.0, "projected_month_usd": 0.0}

    total = sum(float(c["cost_usd"]) for c in recent)
    cost_per_run = total / len(recent)
    runs_per_week = len(recent) / (window_days / 7.0)
    return {
        "cost_per_run_usd":    round(cost_per_run, 6),
        "runs_per_week":       round(runs_per_week, 2),
        "projected_month_usd": round(cost_per_run * runs_per_week * WEEKS_PER_MONTH, 4),
    }


def budget_state(month_cost_usd: float, budget_usd_month: float | None) -> dict:
    """Where a process sits against its monthly budget.

    state: 'none' (no budget set) | 'ok' | 'warning' (>=80%) | 'exceeded' (>=100%)
    """
    if not budget_usd_month or budget_usd_month <= 0:
        return {"state": "none", "used_pct": None}
    pct = (month_cost_usd / budget_usd_month) * 100.0
    if pct >= 100.0:
        state = "exceeded"
    elif pct >= 80.0:
        state = "warning"
    else:
        state = "ok"
    return {"state": state, "used_pct": round(pct, 1)}


def should_block(month_cost_usd: float, budget_usd_month: float | None, budget_action: str) -> bool:
    if budget_action != "block":
        return False
    return budget_state(month_cost_usd, budget_usd_month)["state"] == "exceeded"


def budget_block_expired(blocked_at: datetime | None, now: datetime) -> bool:
    """Budget blocks auto-lift on the 1st of the next month."""
    if blocked_at is None:
        return False
    return blocked_at < month_start(now)


def runway_days(balance_usd: float | None, daily_burn_usd: float) -> float | None:
    """How many days the current balance lasts at the recent burn rate.

    None means 'no balance recorded'; float('inf')-style answers are capped at 999
    so the dashboard never shows nonsense.
    """
    if balance_usd is None:
        return None
    if balance_usd <= 0:
        return 0.0
    if daily_burn_usd <= 0:
        return 999.0
    return min(round(balance_usd / daily_burn_usd, 1), 999.0)


def reconcile(prev_balance_usd: float, latest_balance_usd: float,
              tracked_spend_between_usd: float, tolerance_usd: float = 0.50) -> dict:
    """The honesty gap: real balance drop vs what CostWindow tracked.

    A top-up between snapshots shows as a negative drop — reconciliation is
    skipped (untracked None) because the gap can't be computed across a top-up.
    """
    drop = prev_balance_usd - latest_balance_usd
    if drop < 0:
        return {"balance_drop_usd": round(drop, 4), "untracked_spend_usd": None, "alert": False}
    untracked = drop - tracked_spend_between_usd
    return {
        "balance_drop_usd":    round(drop, 4),
        "untracked_spend_usd": round(max(0.0, untracked), 4),
        "alert":               untracked > tolerance_usd,
    }
