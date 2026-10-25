from app.models import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse

def test_subscription_create_valid():
    s = SubscriptionCreate(name="Blotato", cost_gbp=29.00, renewal_day=1,
                           cancel_url="https://blotato.com/billing")
    assert s.name == "Blotato"
    assert s.cost_gbp == 29.00

def test_subscription_create_no_cancel_url():
    s = SubscriptionCreate(name="Claude Pro", cost_gbp=18.00, renewal_day=28)
    assert s.cancel_url is None

def test_subscription_update_partial():
    u = SubscriptionUpdate(cost_gbp=35.00)
    assert u.cost_gbp == 35.00
    assert u.name is None

from app.routers.subscriptions import (
    _next_renewal_date,
    _days_until_renewal,
)
import datetime

def test_next_renewal_day_this_month():
    # renewal_day=15, today=Jun 3 → Jun 15
    result = _next_renewal_date(renewal_day=15, from_date=datetime.date(2026, 6, 3))
    assert result == datetime.date(2026, 6, 15)

def test_next_renewal_day_past_this_month():
    # renewal_day=1, today=Jun 3 → Jul 1
    result = _next_renewal_date(renewal_day=1, from_date=datetime.date(2026, 6, 3))
    assert result == datetime.date(2026, 7, 1)

def test_next_renewal_day_none():
    result = _next_renewal_date(renewal_day=None, from_date=datetime.date(2026, 6, 3))
    assert result is None
