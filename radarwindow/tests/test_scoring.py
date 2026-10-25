"""Tests for the scoring engine — the velocity/volume ranking that decides what
the brief is even about. The critical property is that one high-volume source
(GitHub stars) can't swamp the rest."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

# Minimal env so config import doesn't fail.
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("BLOTATO_API_KEY", "test")
os.environ.setdefault("SUPABASE_URL", "http://test")
os.environ.setdefault("SUPABASE_KEY", "test")
os.environ.setdefault("RADARWINDOW_USER_ID", "test")

from radarwindow.models import Item, SourceName  # noqa: E402
from radarwindow.scoring import score  # noqa: E402


def _item(source, score_val, hours_old=24):
    return Item(
        source=source,
        title=f"{source.value} item {score_val}",
        url=f"https://example.com/{source.value}/{score_val}",
        raw_score=float(score_val),
        published_at=datetime.now(timezone.utc) - timedelta(hours=hours_old),
    )


def test_empty_input_returns_empty():
    assert score([]) == []


def test_github_stars_do_not_swamp_reddit():
    # GitHub repo with 200k stars vs a Reddit post with 500 upvotes. With naive
    # global normalisation, GitHub would dominate. Per-source normalisation +
    # weighting must let the top Reddit item compete.
    items = [
        _item(SourceName.GITHUB, 200_000),
        _item(SourceName.GITHUB, 1_000),
        _item(SourceName.REDDIT, 500),
        _item(SourceName.REDDIT, 10),
    ]
    ranked = score(items)
    top_reddit = next(s for s in ranked if s.item.source == SourceName.REDDIT)
    # The #1 Reddit item should out-rank the #2 GitHub item (1_000 stars),
    # proving Reddit isn't crushed into irrelevance by GitHub's scale.
    second_github = [s for s in ranked if s.item.source == SourceName.GITHUB][1]
    assert top_reddit.combined_score > second_github.combined_score


def test_scores_are_bounded():
    items = [_item(SourceName.HACKERNEWS, 1000, hours_old=1)]
    ranked = score(items)
    assert 0.0 <= ranked[0].combined_score <= 1.0


def test_ranking_is_descending():
    items = [_item(SourceName.HACKERNEWS, v) for v in (10, 500, 100, 900)]
    ranked = score(items)
    scores = [s.combined_score for s in ranked]
    assert scores == sorted(scores, reverse=True)


def test_old_items_get_zero_velocity():
    items = [
        _item(SourceName.HACKERNEWS, 1000, hours_old=500),  # >168h
        _item(SourceName.HACKERNEWS, 1000, hours_old=2),
    ]
    ranked = score(items)
    old = next(s for s in ranked if s.item.published_at < datetime.now(timezone.utc) - timedelta(hours=100))
    assert old.velocity_score == 0.0
