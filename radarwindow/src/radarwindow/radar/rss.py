from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from ..models import Item, SourceName

log = logging.getLogger(__name__)

# User-supplied feeds: any site that publishes RSS 2.0 or Atom — blogs,
# newsletters, YouTube channels, news sites. Feeds carry no engagement
# numbers, so like the Reddit-RSS fallback we use feed position as a proxy
# score (top of feed = newest/most prominent) and rely on published_at for
# the velocity signal.

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
# YouTube's feed endpoint returns 404 when Accept-Encoding is exactly "gzip"
# (httpx's default without brotli installed); "gzip, deflate" is accepted.
_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
}
_LIMIT = 15          # items kept per feed
_FEED_DELAY_S = 0.5  # polite gap between feed fetches
_ATOM = "{http://www.w3.org/2005/Atom}"


def _parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    try:  # RFC 822 — RSS 2.0 pubDate
        dt = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:  # ISO 8601 — Atom published/updated
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class RSSSource:
    name = SourceName.RSS.value

    def __init__(self, feeds: list[str]) -> None:
        self._feeds = feeds

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        items: list[Item] = []
        for i, feed in enumerate(self._feeds):
            if i:
                await asyncio.sleep(_FEED_DELAY_S)
            try:
                r = await client.get(feed, headers=_HEADERS, follow_redirects=True)
                r.raise_for_status()
                items.extend(self.parse(r.text, feed))
            except Exception as exc:
                log.warning("rss feed %s failed: %s", feed, exc)
        log.info("rss: %d items across %d feed(s)", len(items), len(self._feeds))
        return items

    def parse(self, xml_text: str, feed_url: str) -> list[Item]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            log.warning("rss feed %s parse error: %s", feed_url, exc)
            return []
        if root.tag == f"{_ATOM}feed":
            entries = [self._from_atom(e) for e in root.findall(f"{_ATOM}entry")]
        else:  # RSS 2.0 (root <rss><channel>) or bare <channel>
            channel = root.find("channel") if root.tag != "channel" else root
            if channel is None:
                log.warning("rss feed %s: unrecognised feed shape <%s>", feed_url, root.tag)
                return []
            entries = [self._from_rss(e) for e in channel.findall("item")]

        entries = [e for e in entries if e][:_LIMIT]
        n = len(entries)
        items = []
        for idx, (title, url, published) in enumerate(entries):
            items.append(
                Item(
                    source=SourceName.RSS,
                    title=title,
                    url=url,
                    raw_score=float(n - idx),  # feed-position proxy, like Reddit RSS
                    published_at=published,
                    metadata={"feed": feed_url, "fidelity": "rank-proxy"},
                )
            )
        return items

    def _from_rss(self, item: ET.Element) -> tuple[str, str, datetime | None] | None:
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        if not title or not url:
            return None
        return title, url, _parse_date(item.findtext("pubDate"))

    def _from_atom(self, entry: ET.Element) -> tuple[str, str, datetime | None] | None:
        title = (entry.findtext(f"{_ATOM}title") or "").strip()
        link_el = entry.find(f"{_ATOM}link[@rel='alternate']")
        if link_el is None:
            link_el = entry.find(f"{_ATOM}link")
        url = (link_el.get("href", "") if link_el is not None else "").strip()
        if not title or not url:
            return None
        published = _parse_date(
            entry.findtext(f"{_ATOM}published") or entry.findtext(f"{_ATOM}updated")
        )
        return title, url, published
