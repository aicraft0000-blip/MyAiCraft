from app.routers.summary import compute_summary_from_calls
from datetime import datetime, timezone, timedelta


def _call(cost: float, days_ago: float, provider: str = "anthropic", label: str = "test", billing_type: str = "api"):
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {"cost_usd": str(cost), "called_at": ts, "provider": provider, "process_label": label, "billing_type": billing_type}


def test_today_cost():
    calls = [_call(0.10, 0), _call(0.05, 1)]
    s = compute_summary_from_calls(calls)
    assert abs(s["total_cost_today"] - 0.10) < 0.0001


def test_weekly_cost_last_7_days():
    calls = [_call(0.10, i) for i in range(7)]   # 7 calls within the 7-day window
    s = compute_summary_from_calls(calls)
    assert abs(s["total_cost_this_week"] - 0.70) < 0.0001


def test_monthly_cost_last_30_days():
    calls = [_call(0.10, i) for i in range(30)]  # 30 calls within the 30-day window
    s = compute_summary_from_calls(calls)
    assert abs(s["total_cost_this_month"] - 3.00) < 0.0001


def test_most_expensive_process_today():
    calls = [
        _call(0.10, 0, label="cheap"),
        _call(0.50, 0, label="pricey"),
        _call(0.20, 0, label="cheap"),
    ]
    s = compute_summary_from_calls(calls)
    assert s["most_expensive_process"]["label"] == "pricey"


def test_cost_by_provider_split():
    calls = [_call(0.30, 0, provider="anthropic"), _call(0.20, 0, provider="openai")]
    s = compute_summary_from_calls(calls)
    assert abs(s["cost_by_provider"]["anthropic"] - 0.30) < 0.0001
    assert abs(s["cost_by_provider"]["openai"]    - 0.20) < 0.0001


def test_cost_by_day_has_30_entries():
    s = compute_summary_from_calls([])
    assert len(s["cost_by_day"]) == 30


def test_summary_includes_subscription_fields():
    """compute_summary_from_calls does not include subscriptions — they come from DB.
    Test that the dict keys are present when subscriptions are provided."""
    from app.routers.summary import add_subscription_summary
    result = add_subscription_summary(
        summary={},
        subscriptions=[
            {"cost_gbp": 18.00, "is_active": True},
            {"cost_gbp": 29.00, "is_active": True},
            {"cost_gbp": 11.00, "is_active": False},  # flagged — excluded from total
        ],
        processes_inactive=1,
    )
    assert result["subscriptions_monthly_gbp"] == 47.00  # only active ones
    assert result["subscriptions_count"] == 2
    assert result["kill_switches_active"] == 2  # 1 process + 1 subscription flagged

def test_subscription_billed_calls_excluded_from_totals():
    """Subscription-billed calls (e.g. Claude Code on Claude Max) must not add to monetary totals."""
    calls = [
        _call(0.50, 0, label="api-process",     billing_type="api"),
        _call(1.20, 0, label="claude-code",      billing_type="subscription"),
        _call(0.30, 5, label="claude-code",      billing_type="subscription"),
    ]
    s = compute_summary_from_calls(calls)
    assert abs(s["total_cost_today"]      - 0.50) < 0.0001  # only the api call
    assert abs(s["total_cost_this_month"] - 0.50) < 0.0001
    assert abs(s["total_cost_this_week"]  - 0.50) < 0.0001
    # subscription call still appears in most_expensive / process_today tracking
    assert s["most_expensive_process"]["label"] == "claude-code"


def test_add_subscription_summary_empty():
    from app.routers.summary import add_subscription_summary
    result = add_subscription_summary(summary={}, subscriptions=[], processes_inactive=0)
    assert result["subscriptions_monthly_gbp"] == 0.0
    assert result["kill_switches_active"] == 0
