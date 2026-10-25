from __future__ import annotations

import logging

import httpx

from .config import settings

log = logging.getLogger(__name__)

# The feedback loop — what turns RadarWindow from a content generator into a
# product that compounds. After posts go live, engagement is ingested and the
# next synthesis is told what actually worked for THIS account: which platform,
# which angle, which length. The brief gets sharper every week, which is exactly
# the thing a competitor copying the surface features can't replicate without
# the accumulated per-account history.
#
# Activation: needs engagement data flowing in (via the publisher's
# get_engagement, fed from Blotato/Zernio analytics). Until then the summary is
# empty and synthesis proceeds as normal — no behaviour change, no breakage.

_HEADERS = lambda: {  # noqa: E731
    "apikey": settings.SUPABASE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def store_engagement(rows: list[dict]) -> None:
    """Persist a batch of engagement rows to rw_post_engagement."""
    if not rows:
        return
    try:
        r = httpx.post(
            f"{settings.SUPABASE_URL}/rest/v1/rw_post_engagement",
            json=rows,
            headers={**_HEADERS(), "Prefer": "return=minimal"},
            timeout=30,
        )
        r.raise_for_status()
        log.info("feedback: stored %d engagement rows", len(rows))
    except Exception as exc:
        log.warning("feedback: store failed: %s", exc)


def recent_performance_summary(user_id: str, limit: int = 30) -> str:
    """
    Build a short 'what worked' note for the synthesis prompt from recent
    engagement. Empty string when there's no data yet (the common early case).
    """
    if not user_id:
        return ""
    try:
        r = httpx.get(
            f"{settings.SUPABASE_URL}/rest/v1/rw_post_engagement",
            params={
                "user_id": f"eq.{user_id}",
                "select": "platform,engagement_rate,impressions",
                "order": "engagement_rate.desc",
                "limit": str(limit),
            },
            headers=_HEADERS(),
            timeout=20,
        )
        r.raise_for_status()
        rows = r.json()
    except Exception as exc:
        log.warning("feedback: summary fetch failed: %s", exc)
        return ""

    if not rows:
        return ""

    # Average engagement per platform — tells synthesis where this account wins.
    by_platform: dict[str, list[float]] = {}
    for row in rows:
        by_platform.setdefault(row["platform"], []).append(float(row.get("engagement_rate", 0)))
    ranked = sorted(
        ((p, sum(v) / len(v)) for p, v in by_platform.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    parts = [f"{p} (avg engagement {rate:.1%})" for p, rate in ranked]
    best = ranked[0][0] if ranked else None
    summary = (
        "PRIOR PERFORMANCE FOR THIS ACCOUNT (use to weight effort): "
        + "; ".join(parts)
        + (f". Lead with {best}; it's where this audience responds most." if best else "")
    )
    log.info("feedback: performance summary built for user %s", user_id)
    return summary
