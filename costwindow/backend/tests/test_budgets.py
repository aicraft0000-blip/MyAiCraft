from datetime import datetime, timezone, timedelta

from app.budgets import (
    compute_price_tag,
    budget_state,
    should_block,
    budget_block_expired,
    runway_days,
    reconcile,
    month_start,
    WEEKS_PER_MONTH,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def _call(days_ago: float, cost: float) -> dict:
    return {
        "called_at": (NOW - timedelta(days=days_ago)).isoformat(),
        "cost_usd": cost,
    }


# ── compute_price_tag ────────────────────────────────────────────────

def test_price_tag_empty_calls():
    tag = compute_price_tag([], NOW)
    assert tag == {"cost_per_run_usd": 0.0, "runs_per_week": 0.0, "projected_month_usd": 0.0}


def test_price_tag_basic_math():
    # 30 calls of $0.01 over 30 days = 1/day = 7/week
    calls = [_call(d, 0.01) for d in range(30)]
    tag = compute_price_tag(calls, NOW)
    assert tag["cost_per_run_usd"] == 0.01
    assert tag["runs_per_week"] == 7.0
    assert tag["projected_month_usd"] == round(0.01 * 7.0 * WEEKS_PER_MONTH, 4)


def test_price_tag_ignores_old_calls():
    calls = [_call(2, 0.01), _call(45, 99.0)]
    tag = compute_price_tag(calls, NOW)
    assert tag["cost_per_run_usd"] == 0.01


# ── budget_state ─────────────────────────────────────────────────────

def test_budget_state_none_when_unset():
    assert budget_state(5.0, None)["state"] == "none"
    assert budget_state(5.0, 0)["state"] == "none"


def test_budget_state_ok_warning_exceeded():
    assert budget_state(0.50, 1.00) == {"state": "ok", "used_pct": 50.0}
    assert budget_state(0.80, 1.00) == {"state": "warning", "used_pct": 80.0}
    assert budget_state(1.00, 1.00) == {"state": "exceeded", "used_pct": 100.0}
    assert budget_state(2.50, 1.00) == {"state": "exceeded", "used_pct": 250.0}


# ── should_block ─────────────────────────────────────────────────────

def test_warn_action_never_blocks():
    assert should_block(99.0, 1.0, "warn") is False


def test_block_action_blocks_only_when_exceeded():
    assert should_block(0.99, 1.0, "block") is False
    assert should_block(1.00, 1.0, "block") is True


def test_no_budget_never_blocks():
    assert should_block(99.0, None, "block") is False


# ── budget_block_expired (monthly auto-reset) ────────────────────────

def test_block_from_last_month_expires():
    blocked = datetime(2026, 5, 28, tzinfo=timezone.utc)
    assert budget_block_expired(blocked, NOW) is True


def test_block_from_this_month_holds():
    blocked = datetime(2026, 6, 2, tzinfo=timezone.utc)
    assert budget_block_expired(blocked, NOW) is False


def test_no_blocked_at_never_expires():
    assert budget_block_expired(None, NOW) is False


def test_month_start():
    assert month_start(NOW) == datetime(2026, 6, 1, tzinfo=timezone.utc)


# ── runway_days ──────────────────────────────────────────────────────

def test_runway_basic():
    assert runway_days(10.0, 2.0) == 5.0


def test_runway_zero_balance():
    assert runway_days(0.0, 2.0) == 0.0


def test_runway_no_burn_capped():
    assert runway_days(10.0, 0.0) == 999.0


def test_runway_no_balance_recorded():
    assert runway_days(None, 2.0) is None


# ── reconcile (the honesty gap) ──────────────────────────────────────

def test_reconcile_all_tracked():
    r = reconcile(prev_balance_usd=10.0, latest_balance_usd=9.0, tracked_spend_between_usd=1.0)
    assert r["balance_drop_usd"] == 1.0
    assert r["untracked_spend_usd"] == 0.0
    assert r["alert"] is False


def test_reconcile_untracked_spend_alerts():
    # The June 2026 incident in miniature: balance dropped $30, tracked $0.12
    r = reconcile(prev_balance_usd=30.12, latest_balance_usd=0.0, tracked_spend_between_usd=0.12)
    assert r["untracked_spend_usd"] == 30.0
    assert r["alert"] is True


def test_reconcile_small_drift_within_tolerance():
    r = reconcile(prev_balance_usd=10.0, latest_balance_usd=9.6, tracked_spend_between_usd=0.05)
    assert r["alert"] is False


def test_reconcile_topup_between_snapshots_skipped():
    r = reconcile(prev_balance_usd=1.0, latest_balance_usd=20.0, tracked_spend_between_usd=0.5)
    assert r["untracked_spend_usd"] is None
    assert r["alert"] is False
