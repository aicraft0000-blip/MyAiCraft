"""Self-QA — the recurring alignment check (the owner, 2026-08-23).

Automates the manual drift QA of 2026-08-23: for every active niche it
 1. lints the saved settings, AUTO-FIXING the safe misconfigurations
    (a YouTube page/handle/watch URL saved as a web query or feed is
    resolved to its real feed URL and moved into rss_feeds — exactly the
    mistake that silenced two custom sources),
 2. health-checks every feed URL through the production RSS fetcher,
 3. asks a cheap model what fraction of the latest digest's signals are
    actually on-niche, and flags the niche when drift crosses the line,
then writes a report to rw_qa_reports (the dashboard shows the latest run
as a notification) and emails only when something needs attention.

Scheduled weekly (Sunday 09:00 London) via web/backend/app/scheduler.py.
Manual run: python -m radarwindow.main --job=qa
"""

from __future__ import annotations

import asyncio
import html as html_mod
import json
import logging
import re
from datetime import datetime, timezone

import httpx

from .config import settings
from .radar.rss import _HEADERS as _RSS_HEADERS
from .radar.rss import RSSSource
from .relevance import _client as _llm_client
from .store import Store

log = logging.getLogger("radarwindow.qa")

DRIFT_THRESHOLD = 0.6  # below this on-niche fraction, the niche is flagged
_YT_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id="
_CHANNEL_ID_RE = re.compile(r'(?:"externalId":"|channel_id=|/channel/)(UC[\w-]{16,})')


def _csv(val: str | None) -> list[str]:
    return [s.strip() for s in (val or "").split(",") if s.strip()]


def _is_url(text: str) -> bool:
    return text.startswith(("http://", "https://"))


def _is_youtube_page(url: str) -> bool:
    return ("youtube.com" in url or "youtu.be" in url) and "feeds/videos.xml" not in url


async def resolve_youtube_feed(url: str, client: httpx.AsyncClient) -> str | None:
    """Any YouTube URL (handle, /channel/, watch link) → its videos feed URL."""
    m = _CHANNEL_ID_RE.search(url)
    if m:
        return f"{_YT_FEED}{m.group(1)}"
    try:
        r = await client.get(url, headers=_RSS_HEADERS, follow_redirects=True)
        r.raise_for_status()
    except Exception as exc:
        log.warning("qa: could not resolve YouTube URL %s (%s)", url, exc)
        return None
    m = _CHANNEL_ID_RE.search(r.text)
    return f"{_YT_FEED}{m.group(1)}" if m else None


async def _lint_and_fix(row: dict, client: httpx.AsyncClient) -> tuple[list[dict], dict]:
    """Returns (findings, updates-to-save). Only provably-safe fixes go in updates."""
    findings: list[dict] = []
    web_queries = _csv(row.get("web_queries"))
    rss_feeds = _csv(row.get("rss_feeds"))
    changed = False

    # URLs saved as "web queries" are dead weight — a search query is a phrase.
    # YouTube URLs get resolved and moved to feeds (the 2026-08-23 fix); other
    # URLs are flagged for the human, since we can't know what they meant.
    for q in list(web_queries):
        if not _is_url(q):
            continue
        if _is_youtube_page(q) or q.startswith(_YT_FEED):
            feed = q if q.startswith(_YT_FEED) else await resolve_youtube_feed(q, client)
            if feed:
                web_queries.remove(q)
                if feed not in rss_feeds:
                    rss_feeds.append(feed)
                changed = True
                findings.append({
                    "code": "url-as-query", "severity": "warn", "auto_fixed": True,
                    "message": f"YouTube link saved as a web search — moved to Your feeds as {feed}",
                })
                continue
        findings.append({
            "code": "url-as-query", "severity": "warn", "auto_fixed": False,
            "message": f"“{q[:80]}” is a URL saved as a web search — searches are phrases; feeds belong under Your feeds",
        })

    # YouTube page URLs saved as feeds don't parse — resolve to the real feed.
    for f in list(rss_feeds):
        if _is_url(f) and _is_youtube_page(f):
            feed = await resolve_youtube_feed(f, client)
            if feed:
                rss_feeds[rss_feeds.index(f)] = feed
                changed = True
                findings.append({
                    "code": "yt-page-as-feed", "severity": "warn", "auto_fixed": True,
                    "message": f"YouTube page URL in feeds — replaced with its feed {feed}",
                })

    # Health-check the final feed list through the production fetcher.
    for f in rss_feeds:
        try:
            items = await RSSSource(feeds=[f]).fetch(client)
            if not items:
                findings.append({
                    "code": "feed-empty", "severity": "warn", "auto_fixed": False,
                    "message": f"Feed returns no entries: {f}",
                })
        except Exception as exc:
            findings.append({
                "code": "feed-error", "severity": "warn", "auto_fixed": False,
                "message": f"Feed unreachable ({exc}): {f}",
            })

    if not any([_csv(row.get("subreddits")), _csv(row.get("github_topics")), web_queries, rss_feeds]):
        findings.append({
            "code": "no-own-sources", "severity": "warn", "auto_fixed": False,
            "message": "Niche has no sources of its own — only the filtered general sweep (Hacker News, Polymarket) feeds it",
        })
    if not (row.get("niche") or "").strip():
        findings.append({
            "code": "no-niche-text", "severity": "warn", "auto_fixed": False,
            "message": "Niche description is empty — the relevance filter and brief voice have nothing to aim at",
        })

    updates = {}
    if changed:
        updates = {
            "web_queries": ",".join(web_queries),
            "rss_feeds": ",".join(rss_feeds),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    return findings, updates


def _drift_pct(niche: str, signals: list[dict]) -> float | None:
    """Fraction of the digest's signals a cheap model judges on-niche."""
    titles = [(s.get("title") or "")[:140] for s in signals if s.get("title")]
    if not titles or not niche.strip():
        return None
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(titles))
    prompt = (
        "You are auditing a signals digest for one audience.\n"
        f"Audience / niche: {niche}\n\n"
        "For each headline below, decide if it is genuinely relevant to this "
        "audience's niche.\n\n"
        f"{numbered}\n\n"
        "Return ONLY a JSON array of the numbers that ARE relevant, e.g. [0, 2]. "
        "No prose, no fences."
    )
    # Failures propagate: a drift check that can't run is itself a finding —
    # the same LLM powers synthesis and the relevance filter, so the caller
    # must flag it rather than report the niche as aligned (2026-08-23).
    r = _llm_client().messages.create(
        model=settings.RELEVANCE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in r.content if getattr(b, "type", None) == "text").strip()
    start, end = text.find("["), text.rfind("]")
    on = {int(i) for i in json.loads(text[start : end + 1])}
    return len([i for i in on if 0 <= i < len(titles)]) / len(titles)


async def job_qa() -> None:
    log.info("=== JOB: qa (self-alignment check) ===")
    store = Store()
    try:
        rows = store.all_active_niches()
    except Exception as exc:
        log.error("qa: could not load niches (%s) — aborting", exc)
        return
    if not rows:
        log.info("qa: no active niches — nothing to check")
        return

    reports: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for row in rows:
            label = (row.get("label") or "Default").strip()
            niche_text = (row.get("niche") or "").strip() or label
            findings, updates = await _lint_and_fix(row, client)
            if updates:
                try:
                    store.update_niche(row["id"], updates)
                    log.info("qa [%s]: auto-fixed settings (%s)", label,
                             ", ".join(f["code"] for f in findings if f.get("auto_fixed")))
                except Exception as exc:
                    log.error("qa [%s]: auto-fix save failed: %s", label, exc)
                    for f in findings:
                        if f.get("auto_fixed"):
                            f["auto_fixed"] = False
                            f["message"] += " (fix could not be saved — apply by hand)"

            pct = None
            try:
                digest = store.latest_digest_for_niche(row["id"])
            except Exception as exc:
                log.warning("qa [%s]: could not load digest (%s)", label, exc)
                digest = None
            if digest and digest.get("signals"):
                try:
                    pct = await asyncio.to_thread(_drift_pct, niche_text, digest["signals"])
                except Exception as exc:
                    log.warning("qa [%s]: drift check failed: %s", label, exc)
                    findings.append({
                        "code": "drift-check-failed", "severity": "warn", "auto_fixed": False,
                        "message": f"Drift check could not run ({str(exc)[:160]}) — the same "
                                   "LLM powers the relevance filter, web search and briefs, "
                                   "so those are likely down too",
                    })
                if pct is not None and pct < DRIFT_THRESHOLD:
                    findings.append({
                        "code": "digest-drift", "severity": "warn", "auto_fixed": False,
                        "message": f"Only {pct:.0%} of the latest digest is on-niche — "
                                   "check the niche description and sources",
                    })

            needs_attention = any(f["severity"] == "warn" and not f.get("auto_fixed") for f in findings)
            fixed = sum(1 for f in findings if f.get("auto_fixed"))
            if not findings:
                summary = "Aligned — settings clean" + (f", digest {pct:.0%} on-niche" if pct is not None else "")
            else:
                parts = []
                if fixed:
                    parts.append(f"{fixed} setting{'s' if fixed != 1 else ''} auto-fixed")
                open_n = len(findings) - fixed
                if open_n:
                    parts.append(f"{open_n} finding{'s need' if open_n != 1 else ' needs'} attention")
                summary = ", ".join(parts)
            report = {
                "user_id": row["user_id"],
                "niche_id": row["id"],
                "status": "attention" if needs_attention else "ok",
                "on_niche_pct": pct,
                "findings": findings,
                "summary": summary,
            }
            try:
                store.save_qa_report(report)
            except Exception as exc:
                log.error("qa [%s]: report save failed: %s", label, exc)
            reports.append({**report, "label": label})
            log.info("qa [%s]: %s", label, summary)

    flagged = [r for r in reports if r["findings"]]
    if flagged:
        _email_findings(flagged)
    log.info("=== qa complete: %d niche(s), %d flagged ===", len(reports), len(flagged))


def _email_findings(reports: list[dict]) -> None:
    from .main import _send_email

    total = sum(len(r["findings"]) for r in reports)
    blocks = ""
    for r in reports:
        lines = "".join(
            f"<li style='margin-bottom:6px'>{'✅ auto-fixed: ' if f.get('auto_fixed') else ''}"
            f"{html_mod.escape(f['message'])}</li>"
            for f in r["findings"]
        )
        blocks += f"<p style='margin:14px 0 4px'><strong>{html_mod.escape(r['label'])}</strong></p><ul>{lines}</ul>"
    _send_email(
        f"RadarWindow — self-QA: {total} finding{'s' if total != 1 else ''}",
        "<p>The weekly alignment check ran. Auto-fixes are already applied; "
        "anything else listed needs your eye in Settings → Niches.</p>" + blocks +
        "<p style='margin-top:16px'>The full report is on your dashboard.</p>",
    )
