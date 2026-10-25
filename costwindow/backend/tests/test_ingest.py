from app.routers.ingest import check_process_active


def test_active_process_passes():
    assert check_process_active({"is_active": True}) is True


def test_inactive_process_blocked():
    assert check_process_active({"is_active": False}) is False


def test_missing_is_active_defaults_to_active():
    assert check_process_active({}) is True


def test_cost_calculated_on_ingest():
    from app.pricing import calculate_cost
    cost = calculate_cost("anthropic", "claude-sonnet-4-6", 450, 180)
    assert cost > 0
    assert cost < 0.01  # sanity: small call is cheap
