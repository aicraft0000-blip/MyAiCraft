from app.routers.processes import compute_spike_alert


def test_spike_fires_at_exactly_2x():
    assert compute_spike_alert(today=0.08, seven_day_avg=0.04, threshold=2.0) is True


def test_spike_fires_above_2x():
    assert compute_spike_alert(today=0.10, seven_day_avg=0.04, threshold=2.0) is True


def test_no_spike_below_threshold():
    assert compute_spike_alert(today=0.07, seven_day_avg=0.04, threshold=2.0) is False


def test_no_spike_when_no_history():
    assert compute_spike_alert(today=0.10, seven_day_avg=0.0, threshold=2.0) is False


def test_no_spike_when_today_zero():
    assert compute_spike_alert(today=0.0, seven_day_avg=0.05, threshold=2.0) is False


def test_custom_threshold_3x():
    assert compute_spike_alert(today=0.12, seven_day_avg=0.04, threshold=3.0) is True
    assert compute_spike_alert(today=0.11, seven_day_avg=0.04, threshold=3.0) is False


def test_process_status_unknown_label():
    """Unknown label returns is_active=True (fail open — don't stop unknown crons)."""
    from app.routers.processes import get_process_status_by_label
    result = get_process_status_by_label(label="nonexistent", processes=[])
    assert result is True


def test_process_status_active():
    processes = [{"label": "my-cron", "is_active": True}]
    from app.routers.processes import get_process_status_by_label
    assert get_process_status_by_label("my-cron", processes) is True


def test_process_status_inactive():
    processes = [{"label": "my-cron", "is_active": False}]
    from app.routers.processes import get_process_status_by_label
    assert get_process_status_by_label("my-cron", processes) is False
