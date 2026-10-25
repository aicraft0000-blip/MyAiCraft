from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

from ..config import settings
from ..models import Item, SourceName

log = logging.getLogger(__name__)

# Reddit blocks unauthenticated JSON from cloud/datacenter IPs (403) and rate
# limits the public RSS hard (429 after ~1 request). So we use two strategies:
#
#   1. App-only OAuth  — if REDDIT_CLIENT_ID/SECRET are set. Full scores +
#      comment counts via oauth.reddit.com. Reliable. Preferred.
#   2. Public RSS       — no auth. Titles + hot-rank only (no upvote numbers),
#      with polite delays to dodge the 429. Revives the qualitative signal
#      (what builders are *talking about*) even without engagement numbers.
#
# Reddit is where pain points live, so losing it entirely guts the brief — this
# keeps it alive on a free path and upgrades automatically when keys are added.

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_OAUTH_UA = "RadarWindow/0.1 by /u/aicraft (intelligence pipeline)"
_LIMIT = 25
_RSS_DELAY_S = 2.0  # polite gap between RSS requests to avoid 429
_ATOM = "{http://www.w3.org/2005/Atom}"


async def _app_token(client: httpx.AsyncClient) -> str:
    """App-only OAuth token. Shared by the trending source and the lead search."""
    r = await client.post(
        "https://www.reddit.com/api/v1/access_token",
        data={"grant_type": "client_credentials"},
        auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
        headers={"User-Agent": _OAUTH_UA},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def search_reddit(
    client: httpx.AsyncClient,
    subreddits: list[str],
    queries: list[str],
    per_query: int = 15,
    time_filter: str = "week",
) -> list[dict]:
    """Search Reddit for problem-intent phrases — the lead-finder's Reddit arm.

    Returns raw dicts (not Items): leads need the poster's own words (selftext)
    and author, which the brief's Item shape doesn't carry. Only self/text posts
    are useful for lead-gen, so link posts with empty selftext are dropped.

    Requires app-only OAuth (REDDIT_CLIENT_ID/SECRET). Reddit blocks unauth'd
    search JSON from datacenter IPs, and RSS has no search endpoint, so without
    keys this arm returns [] rather than pretending — the caller logs it.
    """
    if not (settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET):
        log.info("reddit lead search skipped — no OAuth keys (set REDDIT_CLIENT_ID/SECRET)")
        return []
    if not queries:
        return []
    try:
        token = await _app_token(client)
    except Exception as exc:
        log.warning("reddit lead search: token fetch failed (%s)", exc)
        return []

    headers = {"Authorization": f"bearer {token}", "User-Agent": _OAUTH_UA}
    scope = "+".join(subreddits) if subreddits else "all"
    seen: set[str] = set()
    out: list[dict] = []
    for q in queries:
        try:
            r = await client.get(
                f"https://oauth.reddit.com/r/{scope}/search",
                params={
                    "q": q,
                    "restrict_sr": "1" if subreddits else "0",
                    "sort": "new",
                    "t": time_filter,
                    "limit": per_query,
                    "type": "link",
                },
                headers=headers,
            )
            r.raise_for_status()
        except Exception as exc:
            log.warning("reddit lead search q=%r failed: %s", q, exc)
            continue
        for child in r.json().get("data", {}).get("children", []):
            d = child.get("data", {})
            permalink = d.get("permalink")
            selftext = (d.get("selftext") or "").strip()
            if not permalink or permalink in seen or not selftext:
                continue
            seen.add(permalink)
            out.append({
                "source": SourceName.REDDIT.value,
                "title": d.get("title", ""),
                "url": f"https://reddit.com{permalink}",
                "body": selftext[:1200],
                "author": d.get("author"),
                "matched_query": q,
            })
        await asyncio.sleep(0.5)  # polite gap between search calls
    log.info("reddit lead search: %d candidate posts across %d queries", len(out), len(queries))
    return out


class RedditSource:
    name = SourceName.REDDIT.value

    def __init__(self, subreddits: list[str]) -> None:
        self._subreddits = subreddits

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            try:
                return await self._fetch_oauth(client)
            except Exception as exc:
                log.warning("reddit OAuth failed (%s) — falling back to RSS", exc)
        return await self._fetch_rss(client)

    # ------------------------------------------------------------------
    # Strategy 1 — app-only OAuth (full fidelity)
    # ------------------------------------------------------------------

    async def _fetch_oauth(self, client: httpx.AsyncClient) -> list[Item]:
        token = await self._get_token(client)
        headers = {"Authorization": f"bearer {token}", "User-Agent": _OAUTH_UA}
        items: list[Item] = []
        for sub in self._subreddits:
            try:
                r = await client.get(
                    f"https://oauth.reddit.com/r/{sub}/hot",
                    params={"limit": _LIMIT},
                    headers=headers,
                )
                r.raise_for_status()
                items.extend(self._parse_json(r.json(), sub))
            except Exception as exc:
                log.warning("reddit r/%s (oauth) failed: %s", sub, exc)
        log.info("reddit: %d items via OAuth", len(items))
        return items

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        r = await client.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET),
            headers={"User-Agent": _OAUTH_UA},
        )
        r.raise_for_status()
        return r.json()["access_token"]

    def _parse_json(self, payload: dict, sub: str) -> list[Item]:
        items = []
        for child in payload.get("data", {}).get("children", []):
            d = child.get("data", {})
            if d.get("stickied"):
                continue
            items.append(
                Item(
                    source=SourceName.REDDIT,
                    title=d["title"],
                    url=f"https://reddit.com{d['permalink']}",
                    raw_score=float(d.get("score", 0)),
                    comment_count=int(d.get("num_comments", 0)),
                    published_at=datetime.fromtimestamp(d["created_utc"], tz=timezone.utc),
                    metadata={
                        "subreddit": sub,
                        "upvote_ratio": d.get("upvote_ratio"),
                        "flair": d.get("link_flair_text"),
                        "fidelity": "full",
                    },
                )
            )
        return items

    # ------------------------------------------------------------------
    # Strategy 2 — public RSS (no auth, hot-rank only)
    # ------------------------------------------------------------------

    async def _fetch_rss(self, client: httpx.AsyncClient) -> list[Item]:
        items: list[Item] = []
        for i, sub in enumerate(self._subreddits):
            if i:
                await asyncio.sleep(_RSS_DELAY_S)
            try:
                r = await client.get(
                    f"https://www.reddit.com/r/{sub}/hot.rss",
                    params={"limit": _LIMIT},
                    headers={"User-Agent": _BROWSER_UA},
                )
                if r.status_code == 429:
                    log.warning("reddit r/%s RSS rate-limited (429) — skipping", sub)
                    continue
                r.raise_for_status()
                items.extend(self._parse_rss(r.text, sub))
            except Exception as exc:
                log.warning("reddit r/%s (rss) failed: %s", sub, exc)
        log.info("reddit: %d items via RSS (hot-rank proxy scores)", len(items))
        return items

    def _parse_rss(self, xml_text: str, sub: str) -> list[Item]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            log.warning("reddit r/%s RSS parse error: %s", sub, exc)
            return []
        entries = root.findall(f"{_ATOM}entry")
        items = []
        n = len(entries)
        for idx, entry in enumerate(entries):
            title_el = entry.find(f"{_ATOM}title")
            link_el = entry.find(f"{_ATOM}link")
            pub_el = entry.find(f"{_ATOM}published") or entry.find(f"{_ATOM}updated")
            if title_el is None or link_el is None:
                continue
            title = (title_el.text or "").strip()
            url = link_el.get("href", "").strip()
            if not title or not url:
                continue
            published = None
            if pub_el is not None and pub_el.text:
                try:
                    published = datetime.fromisoformat(pub_el.text.strip())
                except ValueError:
                    pass
            # No upvotes in RSS: use hot-rank as a proxy score (top of hot = highest).
            proxy_score = float(n - idx)
            items.append(
                Item(
                    source=SourceName.REDDIT,
                    title=title,
                    url=url,
                    raw_score=proxy_score,
                    comment_count=0,
                    published_at=published,
                    metadata={"subreddit": sub, "fidelity": "rss_rank", "hot_rank": idx + 1},
                )
            )
        return items
