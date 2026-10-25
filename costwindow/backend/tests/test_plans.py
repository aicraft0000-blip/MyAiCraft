from app.plans import (
    FREE_PROCESS_LIMIT,
    can_add_process,
    is_paid,
    plan_from_customer_row,
)


def test_free_process_limit_is_two():
    assert FREE_PROCESS_LIMIT == 2


def test_is_paid():
    assert is_paid("monthly")
    assert is_paid("yearly")
    assert not is_paid("free")
    assert not is_paid(None)
    assert not is_paid("enterprise")


def test_free_plan_capped_at_limit():
    assert can_add_process("free", 0)
    assert can_add_process("free", 1)
    assert not can_add_process("free", 2)
    assert not can_add_process("free", 9)


def test_none_plan_treated_as_free():
    assert can_add_process(None, 1)
    assert not can_add_process(None, 2)


def test_paid_plans_uncapped():
    assert can_add_process("monthly", 500)
    assert can_add_process("yearly", 500)


def test_plan_from_customer_row_active_monthly():
    assert plan_from_customer_row({"plan": "monthly", "status": "active"}) == "monthly"


def test_plan_from_customer_row_active_yearly():
    assert plan_from_customer_row({"plan": "yearly", "status": "active"}) == "yearly"


def test_plan_from_customer_row_missing():
    assert plan_from_customer_row(None) == "free"


def test_plan_from_customer_row_inactive():
    assert plan_from_customer_row({"plan": "monthly", "status": "canceled"}) == "free"


def test_plan_from_customer_row_unknown_plan_defaults_monthly():
    # An active subscriber with an unrecognised plan string must never be capped.
    assert plan_from_customer_row({"plan": "something-new", "status": "active"}) == "monthly"
