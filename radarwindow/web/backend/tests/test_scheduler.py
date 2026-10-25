from datetime import datetime
from zoneinfo import ZoneInfo

from app.scheduler import LONDON, next_run

UTC = ZoneInfo("UTC")


def test_daily_same_day_when_before_slot():
    # Wed 05:00 London → digest today 07:00
    now = datetime(2026, 7, 8, 5, 0, tzinfo=LONDON)
    at = next_run("digest", 7, 0, None, now)
    assert (at.date(), at.hour) == (now.date(), 7)


def test_daily_rolls_to_tomorrow_after_slot():
    now = datetime(2026, 7, 8, 7, 1, tzinfo=LONDON)
    at = next_run("digest", 7, 0, None, now)
    assert at.day == 9 and at.hour == 7


def test_weekly_lands_on_monday():
    # Sat 2026-07-11 → synthesise Mon 2026-07-13 07:00
    now = datetime(2026, 7, 11, 12, 0, tzinfo=LONDON)
    at = next_run("synthesise", 7, 0, 0, now)
    assert at.weekday() == 0 and at.day == 13 and at.hour == 7


def test_monday_after_slot_waits_a_week():
    now = datetime(2026, 7, 13, 8, 0, tzinfo=LONDON)  # Monday 08:00
    at = next_run("synthesise", 7, 0, 0, now)
    assert at.weekday() == 0 and at.day == 20


def test_utc_now_handled_and_dst_aware():
    # Server clock is UTC; 06:30 UTC in July == 07:30 London → slot passed
    now = datetime(2026, 7, 8, 6, 30, tzinfo=UTC)
    at = next_run("digest", 7, 0, None, now)
    assert at.tzinfo is LONDON and at.day == 9

    # In January (no DST) 06:30 UTC == 06:30 London → today still ahead
    now = datetime(2026, 1, 7, 6, 30, tzinfo=UTC)
    at = next_run("digest", 7, 0, None, now)
    assert at.day == 7 and at.hour == 7
