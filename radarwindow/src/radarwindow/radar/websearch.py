from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import anthropic
import httpx

from ..config import settings
from ..models import Item, SourceName

log = logging.getLogger(__name__)

# Server-side web search tool. The model runs live searches, then returns a
# structured digest we turn into ranked Items. This is what makes the brief
# aware of *current events* (pricing changes, launches, outages) that never
# show up on GitHub or Polymarket.
_WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
_MAX_ITEMS = 8


class WebSearchSource:
    """
    Live web-news source backed by Anthropic's web_search tool.

    Runs the (sync) Anthropic call in a thread so it slots into the async radar
    gather alongside the HTTP sources. Returns ranked Items with a recency-based
    published_at so velocity scoring treats fresh news as fresh.
    """

    name = SourceName.WEBSEARCH.value

    def __init__(self, queries: list[str], niche: str | None = None) -> None:
        self._queries = queries
        # The audience the search is aimed at. Must be the NICHE'S OWN text —
        # falling back to the global settings.NICHE pointed every niche's web
        # search at the default AI audience (drift QA, 2026-08-23).
        self._niche = (niche or "").strip() or settings.NICHE

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        if not self._queries:
            return []
        try:
            return await asyncio.to_thread(self._search_blocking)
        except Exception as exc:
            log.warning("websearch failed: %s", exc)
            return []

    def _search_blocking(self) -> list[Item]:
        anth = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        query_block = "; ".join(self._queries)
        prompt = (
            "Use web search to find this week's most significant, specific news for "
            f"this audience: {self._niche}.\n\n"
            f"Focus areas: {query_block}.\n\n"
            "Prioritise concrete developments builders can act on: model launches, "
            "pricing changes, API/feature releases, notable outages, funding that "
            "shifts the tools landscape. Avoid opinion pieces and listicles.\n\n"
            f"Return ONLY a JSON array of up to {_MAX_ITEMS} objects, ranked most to "
            "least important, each:\n"
            '{"title": str, "url": str (real source URL), '
            '"days_ago": int (0-7, when it broke), '
            '"importance": int (1-100, your ranking weight)}\n'
            "No preamble, no markdown fences."
        )

        r = anth.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1500,
            tools=[_WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": prompt}],
        )

        # The final text block holds the JSON digest; earlier blocks are tool I/O.
        text = ""
        for block in r.content:
            if getattr(block, "type", None) == "text":
                text += block.text
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        # Trim to the JSON array if the model added stray prose.
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]

        try:
            rows = json.loads(text)
        except json.JSONDecodeError:
            log.warning("websearch: could not parse model JSON; returning none")
            return []

        now = datetime.now(timezone.utc)
        items: list[Item] = []
        for row in rows:
            url = (row.get("url") or "").strip()
            title = (row.get("title") or "").strip()
            if not title or not url.startswith("http"):
                continue
            importance = float(row.get("importance", 50) or 50)
            days_ago = max(0, min(int(row.get("days_ago", 2) or 2), 7))
            published = now - timedelta(days=days_ago, hours=1)
            items.append(
                Item(
                    source=SourceName.WEBSEARCH,
                    title=title,
                    url=url,
                    raw_score=importance,
                    comment_count=0,
                    published_at=published,
                    metadata={"days_ago": days_ago},
                )
            )
        log.info("websearch: %d live news items", len(items))
        return items
