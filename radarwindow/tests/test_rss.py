"""Custom RSS feeds per niche (2026-08-11) — parsing + pipeline wiring."""

from datetime import datetime, timezone

from radarwindow import main as m
from radarwindow.models import SourceName
from radarwindow.radar.rss import RSSSource, _parse_date
from radarwindow.scoring import _SOURCE_WEIGHT

RSS2 = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Example Blog</title>
  <item>
    <title>First post</title>
    <link>https://example.com/first</link>
    <pubDate>Mon, 10 Aug 2026 09:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Second post</title>
    <link>https://example.com/second</link>
    <pubDate>Sun, 09 Aug 2026 09:00:00 GMT</pubDate>
  </item>
  <item>
    <title></title>
    <link>https://example.com/no-title</link>
  </item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom</title>
  <entry>
    <title>Atom entry</title>
    <link rel="alternate" href="https://example.com/atom-1"/>
    <published>2026-08-10T09:00:00Z</published>
  </entry>
  <entry>
    <title>Bare-link entry</title>
    <link href="https://example.com/atom-2"/>
    <updated>2026-08-09T09:00:00+00:00</updated>
  </entry>
</feed>"""


def test_parse_rss2():
    items = RSSSource(feeds=[]).parse(RSS2, "https://example.com/feed")
    assert [i.title for i in items] == ["First post", "Second post"]  # empty title dropped
    assert items[0].url == "https://example.com/first"
    assert items[0].source == SourceName.RSS
    assert items[0].published_at == datetime(2026, 8, 10, 9, tzinfo=timezone.utc)
    # feed-position proxy: top of feed scores highest
    assert items[0].raw_score > items[1].raw_score
    assert items[0].metadata["feed"] == "https://example.com/feed"


def test_parse_atom():
    items = RSSSource(feeds=[]).parse(ATOM, "https://example.com/atom")
    assert [i.title for i in items] == ["Atom entry", "Bare-link entry"]
    assert items[0].url == "https://example.com/atom-1"
    assert items[1].url == "https://example.com/atom-2"  # link without rel=alternate still found
    assert items[1].published_at == datetime(2026, 8, 9, 9, tzinfo=timezone.utc)  # falls back to <updated>


def test_parse_garbage_returns_empty():
    assert RSSSource(feeds=[]).parse("not xml at all", "https://x.com/feed") == []
    assert RSSSource(feeds=[]).parse("<html><body>hi</body></html>", "https://x.com/feed") == []


def test_parse_date_variants():
    assert _parse_date("Mon, 10 Aug 2026 09:00:00 GMT") == datetime(2026, 8, 10, 9, tzinfo=timezone.utc)
    assert _parse_date("2026-08-10T09:00:00Z") == datetime(2026, 8, 10, 9, tzinfo=timezone.utc)
    assert _parse_date("nonsense") is None
    assert _parse_date(None) is None
    assert _parse_date("") is None


def test_rss_has_scoring_weight():
    assert SourceName.RSS in _SOURCE_WEIGHT


# --- pipeline wiring ---

def test_niche_configs_carry_rss_feeds(monkeypatch):
    class FakeStore:
        def all_active_niches(self):
            return [{"id": "n1", "user_id": "u1", "rss_feeds": "https://a.com/feed, https://b.com/rss"}]
    monkeypatch.setattr(m, "Store", lambda: FakeStore())
    cfg = m._niche_configs()[0]
    assert cfg["rss_feeds"] == ["https://a.com/feed", "https://b.com/rss"]


def test_niche_configs_rss_feeds_default_empty(monkeypatch):
    class FakeStore:
        def all_active_niches(self):
            return [{"id": "n1", "user_id": "u1"}]
    monkeypatch.setattr(m, "Store", lambda: FakeStore())
    assert m._niche_configs()[0]["rss_feeds"] == []  # no global fallback for custom feeds


def test_sources_for_includes_rss_only_when_feeds_set():
    base = {"subreddits": ["a"], "github_topics": ["b"], "web_queries": ["c"]}
    assert len(m._sources_for({**base, "rss_feeds": []})) == 5
    srcs = m._sources_for({**base, "rss_feeds": ["https://a.com/feed"]})
    assert len(srcs) == 6
    assert srcs[-1].name == SourceName.RSS.value
