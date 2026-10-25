from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from ..models import Item, SourceName

log = logging.getLogger(__name__)

_BASE = "https://gamma-api.polymarket.com"
_KEYWORDS = ["AI", "artificial intelligence", "LLM", "GPT", "Claude", "model", "OpenAI", "Anthropic"]
_LIMIT = 50
_MIN_VOLUME = 1000.0  # USDC — ignore micro-markets


class PolymarketSource:
    name = SourceName.POLYMARKET.value

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        try:
            r = await client.get(
                f"{_BASE}/markets",
                params={"limit": _LIMIT, "active": "true", "order": "volume", "ascending": "false"},
            )
            r.raise_for_status()
            markets = r.json()
        except Exception as exc:
            log.warning("polymarket fetch failed: %s", exc)
            return []

        items = []
        for m in markets:
            if not self._is_relevant(m):
                continue
            volume = float(m.get("volume", 0) or 0)
            if volume < _MIN_VOLUME:
                continue
            end_date = None
            if m.get("endDate"):
                try:
                    end_date = datetime.fromisoformat(m["endDate"].replace("Z", "+00:00"))
                except ValueError:
                    pass
            items.append(
                Item(
                    source=SourceName.POLYMARKET,
                    title=m.get("question", m.get("title", "")),
                    url=f"https://polymarket.com/event/{m.get('slug', m.get('id', ''))}",
                    raw_score=volume,
                    comment_count=0,
                    published_at=end_date,
                    metadata={
                        "volume_usdc": volume,
                        "liquidity": m.get("liquidity"),
                        "slug": m.get("slug"),
                    },
                )
            )
        return items

    def _is_relevant(self, market: dict) -> bool:
        text = (market.get("question", "") + " " + market.get("description", "")).lower()
        return any(kw.lower() in text for kw in _KEYWORDS)
