"""Self-QA lint + auto-fix (2026-08-23). Async paths run via asyncio.run —
the project venv has no pytest-asyncio plugin."""

import asyncio

from radarwindow import qa


def test_is_youtube_page():
    assert qa._is_youtube_page("https://www.youtube.com/@alexwg")
    assert qa._is_youtube_page("https://www.youtube.com/watch?v=abc")
    assert not qa._is_youtube_page("https://www.youtube.com/feeds/videos.xml?channel_id=UCx")
    assert not qa._is_youtube_page("https://example.com/feed.xml")


def test_resolve_feed_from_channel_url_needs_no_http():
    feed = asyncio.run(qa.resolve_youtube_feed(
        "https://www.youtube.com/channel/UCvjvMqS2tiyIZJm0AqwXvcw", client=None
    ))
    assert feed == "https://www.youtube.com/feeds/videos.xml?channel_id=UCvjvMqS2tiyIZJm0AqwXvcw"


def test_lint_moves_youtube_url_out_of_web_queries(monkeypatch):
    """The exact 2026-08-23 misconfiguration: a channel URL saved as a web query."""
    async def fake_fetch(self, client):
        return ["one item"]
    monkeypatch.setattr(qa.RSSSource, "fetch", fake_fetch)

    row = {
        "web_queries": "https://www.youtube.com/channel/UCvjvMqS2tiyIZJm0AqwXvcw",
        "rss_feeds": "", "subreddits": "", "github_topics": "", "niche": "x",
    }
    findings, updates = asyncio.run(qa._lint_and_fix(row, client=None))
    assert updates["web_queries"] == ""
    assert updates["rss_feeds"] == "https://www.youtube.com/feeds/videos.xml?channel_id=UCvjvMqS2tiyIZJm0AqwXvcw"
    fixed = [f for f in findings if f.get("auto_fixed")]
    assert len(fixed) == 1 and fixed[0]["code"] == "url-as-query"


def test_lint_flags_empty_feed_and_no_sources(monkeypatch):
    async def fake_fetch(self, client):
        return []
    monkeypatch.setattr(qa.RSSSource, "fetch", fake_fetch)

    row = {"web_queries": "", "rss_feeds": "https://example.com/feed.xml",
           "subreddits": "", "github_topics": "", "niche": ""}
    findings, updates = asyncio.run(qa._lint_and_fix(row, client=None))
    assert not updates
    codes = {f["code"] for f in findings}
    assert "feed-empty" in codes
    assert "no-niche-text" in codes
    assert "no-own-sources" not in codes  # it HAS a feed configured


def test_lint_non_youtube_url_in_queries_flagged_not_fixed():
    row = {"web_queries": "https://example.com/blog", "rss_feeds": "",
           "subreddits": "a", "github_topics": "", "niche": "x"}
    findings, updates = asyncio.run(qa._lint_and_fix(row, client=None))
    assert not updates
    assert any(f["code"] == "url-as-query" and not f.get("auto_fixed") for f in findings)
