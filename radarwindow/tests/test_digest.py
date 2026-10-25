"""Tests for the daily digest renderer — pure markdown from radar + scoring
output, no LLM. If this breaks, the daily signals email/dashboard breaks."""
from __future__ import annotations

from datetime import datetime, timezone

from radarwindow.digest import render_digest
from radarwindow.models import Item, ScoredItem, SourceName

_DATE = datetime(2026, 7, 5, 7, 0, tzinfo=timezone.utc)


def _signal(title: str, source: SourceName, combined: float, velocity: float = 0.5) -> ScoredItem:
    return ScoredItem(
        item=Item(source=source, title=title, url=f"https://example.com/{source.value}", raw_score=100),
        volume_score=0.5,
        velocity_score=velocity,
        combined_score=combined,
    )


_SIGNALS = [
    _signal("HN top story", SourceName.HACKERNEWS, 0.91, velocity=0.8),
    _signal("Rising repo", SourceName.GITHUB, 0.74),
]


def test_title_line_carries_date():
    md = render_digest(_SIGNALS, _DATE)
    assert md.startswith("# Daily signals — 2026-07-05")


def test_signals_ranked_with_source_score_and_url():
    md = render_digest(_SIGNALS, _DATE)
    assert "1. **[HN top story](https://example.com/hackernews)** — hackernews · score 0.91 · velocity 0.80" in md
    assert "2. **[Rising repo](" in md
    assert "github · score 0.74" in md


def test_source_health_section_when_provided():
    md = render_digest(_SIGNALS, _DATE, health={"hackernews": 12, "reddit": 0})
    assert "## Source health" in md
    assert "| hackernews | 12 |" in md
    assert "| reddit | 0 |" in md


def test_no_health_section_when_absent():
    assert "Source health" not in render_digest(_SIGNALS, _DATE)


def test_empty_signals_still_renders():
    md = render_digest([], _DATE)
    assert "No signals cleared the radar today." in md
