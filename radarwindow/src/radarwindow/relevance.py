from __future__ import annotations

import json
import logging

import anthropic

from .config import settings
from .models import Item, SourceName

log = logging.getLogger(__name__)

# Sources that fetch globally rather than from the niche's own settings.
# Hacker News pulls the whole front page and Polymarket matches hardcoded
# keywords, so without a gate their items land in every niche's digest
# regardless of what the niche is about (the 2026-08-23 drift QA).
NICHE_BLIND: frozenset[SourceName] = frozenset({SourceName.HACKERNEWS, SourceName.POLYMARKET})

_MAX_TITLE = 140


def _client() -> anthropic.Anthropic:
    """Route through the CostWindow proxy when configured, like synthesis —
    the filter's spend is tracked under its own process label."""
    if settings.COSTWINDOW_PROXY_URL:
        return anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.COSTWINDOW_PROXY_URL,
            default_headers={"X-CostWindow-Label": "radarwindow-relevance"},
        )
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def filter_offniche(items: list[Item], niche: str, label: str = "") -> list[Item]:
    """Drop clearly off-niche items from the niche-blind sources before scoring.

    Items from user-chosen sources (Reddit, GitHub, web search, RSS) pass
    through untouched — the user picked those places, so their content is
    theirs to judge. Fail-open: any error keeps every item, because a digest
    with some noise beats a digest that silently vanished.
    """
    niche = (niche or "").strip()
    judged = [it for it in items if it.source in NICHE_BLIND]
    if not judged or not niche:
        return items
    kept_always = [it for it in items if it.source not in NICHE_BLIND]

    numbered = "\n".join(f"{i}. {it.title[:_MAX_TITLE]}" for i, it in enumerate(judged))
    prompt = (
        "You curate a signals radar for one specific audience.\n"
        f"Audience / niche: {niche}\n\n"
        "Below are headlines swept from general sources (Hacker News front page, "
        "prediction markets). Keep ONLY the ones this audience would genuinely "
        "care about — directly relevant to their niche, not merely interesting "
        "tech news. When in doubt, drop it.\n\n"
        f"{numbered}\n\n"
        "Return ONLY a JSON array of the numbers to KEEP, e.g. [0, 4]. "
        "An empty array [] is a valid answer. No prose, no fences."
    )

    try:
        r = _client().messages.create(
            model=settings.RELEVANCE_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in r.content if getattr(b, "type", None) == "text").strip()
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end == -1:
            raise ValueError(f"no JSON array in reply: {text[:80]!r}")
        keep_idx = {int(i) for i in json.loads(text[start : end + 1])}
    except Exception as exc:
        log.warning("relevance filter failed (%s) — keeping all %d items", exc, len(items))
        return items

    kept = [it for i, it in enumerate(judged) if i in keep_idx]
    log.info(
        "relevance [%s]: kept %d/%d niche-blind items (%d user-source items untouched)",
        label or niche[:40], len(kept), len(judged), len(kept_always),
    )
    return kept_always + kept
