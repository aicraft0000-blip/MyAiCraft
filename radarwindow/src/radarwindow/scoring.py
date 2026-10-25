from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from .models import Item, ScoredItem, SourceName

_VOLUME_WEIGHT = 0.6
_VELOCITY_WEIGHT = 0.4
# Items older than this many hours get velocity = 0
_MAX_AGE_HOURS = 168  # 7 days

# Per-source weighting applied AFTER within-source normalisation.
# Reddit + HN are discussion signals (where pain points live) — weighted up.
# GitHub stars are cumulative and slow-moving — weighted down so a mature repo
# can't dominate a batch on raw star count alone.
_SOURCE_WEIGHT: dict[SourceName, float] = {
    SourceName.REDDIT: 1.15,
    SourceName.HACKERNEWS: 1.10,
    SourceName.WEBSEARCH: 1.05,
    SourceName.RSS: 1.05,  # user-picked feeds — hand-curated, trusted like websearch
    SourceName.POLYMARKET: 0.95,
    SourceName.GITHUB: 0.80,
}


def score(items: list[Item]) -> list[ScoredItem]:
    """
    Rank items by combined velocity + volume.

    Critical fix over the naive approach: volume and velocity are normalised
    *within each source first*, so GitHub star-counts (cumulative, ~hundreds of
    thousands) never swamp HN points (~hundreds) or Polymarket USDC in a single
    global min-max. A repo that's #1 on GitHub and a post that's #1 on Reddit
    both land near 1.0 in their own source, then a per-source weight decides
    how much that source matters. This keeps the brief from collapsing into
    "GitHub trending".
    """
    if not items:
        return []

    now = datetime.now(timezone.utc)

    # Bucket by source so normalisation happens within-source.
    buckets: dict[SourceName, list[Item]] = defaultdict(list)
    for item in items:
        buckets[item.source].append(item)

    scored: list[ScoredItem] = []
    for source, group in buckets.items():
        weight = _SOURCE_WEIGHT.get(source, 1.0)
        raw_volumes = [it.raw_score for it in group]
        velocities = [_velocity(it, now) for it in group]
        norm_volumes = _normalise(raw_volumes)
        norm_velocities = _normalise(velocities)

        for it, vol, vel in zip(group, norm_volumes, norm_velocities):
            base = _VOLUME_WEIGHT * vol + _VELOCITY_WEIGHT * vel
            combined = min(base * weight, 1.0)
            scored.append(
                ScoredItem(
                    item=it,
                    volume_score=vol,
                    velocity_score=vel,
                    combined_score=combined,
                )
            )

    scored.sort(key=lambda s: s.combined_score, reverse=True)
    return scored


def _velocity(item: Item, now: datetime) -> float:
    """Engagement per hour since published. Zero if no published_at or too old."""
    if item.published_at is None:
        return 0.0
    age_hours = (now - item.published_at).total_seconds() / 3600
    if age_hours <= 0 or age_hours > _MAX_AGE_HOURS:
        return 0.0
    return item.raw_score / age_hours


def _normalise(values: list[float]) -> list[float]:
    """Min-max normalisation to [0, 1]. All-zero input returns all zeros."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        # Single item or all-equal: give full credit rather than zero, so a
        # source with one strong signal isn't erased.
        return [1.0 if hi > 0 else 0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]
