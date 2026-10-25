from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from ..models import Item, SourceName

log = logging.getLogger(__name__)

_BASE = "https://hacker-news.firebaseio.com/v0"
_TOP_N = 30       # how many top stories to pull IDs for
_FETCH_N = 20     # max items to fully hydrate (avoids hammering the API)


class HackerNewsSource:
    name = SourceName.HACKERNEWS.value

    def __init__(self, min_score: int = 50) -> None:
        self._min_score = min_score

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        r = await client.get(f"{_BASE}/topstories.json")
        r.raise_for_status()
        ids = r.json()[:_TOP_N]

        items = await asyncio.gather(
            *(self._fetch_item(client, story_id) for story_id in ids[:_FETCH_N]),
            return_exceptions=True,
        )

        result = []
        for item in items:
            if isinstance(item, Exception):
                log.warning("HN item fetch failed: %s", item)
                continue
            if item is not None:
                result.append(item)
        return result

    async def _fetch_item(self, client: httpx.AsyncClient, story_id: int) -> Item | None:
        r = await client.get(f"{_BASE}/item/{story_id}.json")
        r.raise_for_status()
        d = r.json()
        if not d or d.get("type") != "story":
            return None
        score = int(d.get("score", 0))
        if score < self._min_score:
            return None
        url = d.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        return Item(
            source=SourceName.HACKERNEWS,
            title=d.get("title", ""),
            url=url,
            raw_score=float(score),
            comment_count=int(d.get("descendants", 0)),
            published_at=datetime.fromtimestamp(d["time"], tz=timezone.utc) if d.get("time") else None,
            metadata={"hn_id": story_id, "by": d.get("by")},
        )
