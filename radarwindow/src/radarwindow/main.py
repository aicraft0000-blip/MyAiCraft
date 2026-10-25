from __future__ import annotations

import argparse
import asyncio
import html
import logging
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from .config import settings
from .digest import render_digest
from .models import AuditEntry, BriefStatus, Digest, Platform, PostStatus, SourceName
from .radar.github import GitHubSource
from .radar.hackernews import HackerNewsSource
from .radar.polymarket import PolymarketSource
from .radar.reddit import RedditSource
from .radar.rss import RSSSource
from .radar.websearch import WebSearchSource
from .scoring import score
from .store import Store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("radarwindow")


def _csv(val: str | None, fallback: list[str]) -> list[str]:
    items = [s.strip() for s in (val or "").split(",") if s.strip()]
    return items or fallback


def _niche_configs() -> list[dict]:
    """One config per ACTIVE niche, resolved with global fallbacks. This is what
    makes the pipeline multi-niche: a single account can hold several niches, and
    each drives its own brief/digest for its own sources. If no niches exist yet,
    fall back to a single global run (historical single-tenant behaviour) so the
    pipeline never goes silent. `niche_id` is None only on that global fallback."""
    try:
        rows = Store().all_active_niches()
    except Exception as exc:
        log.warning("could not load niches (%s) — falling back to global run", exc)
        rows = []

    if not rows:
        rows = [{"id": None, "user_id": settings.RADARWINDOW_USER_ID, "label": "Default"}]

    configs = []
    for r in rows:
        # Content-shaping fields NEVER inherit the global env defaults on a real
        # niche row: an empty field means that source is OFF for that niche.
        # Inheriting was how an unrelated niche's digest filled up with the
        # default AI audience's subreddits and topics (drift QA, 2026-08-23).
        # The env defaults apply only to the legacy no-niches global run.
        is_global = r.get("id") is None
        niche_text = (r.get("niche") or "").strip()
        # A real row with no niche text falls back to its own label — never to
        # the global NICHE, which would aim the voice at the wrong audience.
        fallback_niche = settings.NICHE if is_global else (r.get("label") or "Default").strip()
        configs.append({
            "niche_id":      r.get("id"),
            "user_id":       r.get("user_id") or settings.RADARWINDOW_USER_ID,
            "label":         (r.get("label") or "Default").strip(),
            "niche":         niche_text or fallback_niche,
            "avoid_words":   (r.get("avoid_words") or "").strip() or settings.NICHE_AVOID_WORDS,
            "subreddits":    _csv(r.get("subreddits"), settings.reddit_subreddits_list if is_global else []),
            "github_topics": _csv(r.get("github_topics"), settings.github_topics_list if is_global else []),
            "web_queries":   _csv(r.get("web_queries"), settings.web_search_queries_list if is_global else []),
            "rss_feeds":     _csv(r.get("rss_feeds"), []),
            "notify_email":  (r.get("notify_email") or "").strip() or settings.NOTIFY_EMAIL,
        })
    return configs


def _sources_for(cfg: dict) -> list:
    """Build the radar source list for one user's config. HN + Polymarket fetch
    globally (their items pass a niche-relevance gate before scoring);
    Reddit/GitHub/web/RSS run only when the niche actually configured them, so
    an empty field means off — never someone else's defaults — and source
    health doesn't show permanently-empty sources."""
    sources: list = [
        HackerNewsSource(min_score=settings.HN_MIN_SCORE),
        PolymarketSource(),
    ]
    if cfg.get("subreddits"):
        sources.append(RedditSource(subreddits=cfg["subreddits"]))
    if cfg.get("github_topics"):
        sources.append(GitHubSource(topics=cfg["github_topics"]))
    if cfg.get("web_queries"):
        sources.append(WebSearchSource(queries=cfg["web_queries"], niche=cfg.get("niche")))
    if cfg.get("rss_feeds"):
        sources.append(RSSSource(feeds=cfg["rss_feeds"]))
    return sources


async def _gather_radar(sources: list) -> tuple[list, dict[str, int]]:
    """Fetch all sources concurrently. Returns (items, per-source health counts)."""
    async with httpx.AsyncClient(timeout=30) as client:
        results = await asyncio.gather(
            *(s.fetch(client) for s in sources),
            return_exceptions=True,
        )
    items = []
    health: dict[str, int] = {}
    for src, result in zip(sources, results):
        if isinstance(result, Exception):
            log.warning("source %s failed: %s", src.name, result)
            health[src.name] = 0
            continue
        log.info("source %s: %d items", src.name, len(result))
        health[src.name] = len(result)
        items.extend(result)
    return items, health


async def _synthesise_for(cfg: dict) -> None:
    from .media import enrich_posts
    from .relevance import filter_offniche
    from .synthesis import synthesise

    items, health = await _gather_radar(_sources_for(cfg))
    if not items:
        log.error("[%s] no items fetched — skipping synthesise", cfg["user_id"])
        return
    items = filter_offniche(items, cfg["niche"], cfg["label"])
    if not items:
        log.error("[%s] every item filtered as off-niche — skipping synthesise", cfg["user_id"])
        return

    live = [s for s, n in health.items() if n > 0]
    dead = [s for s, n in health.items() if n == 0]
    log.info("[%s] source health — live: %s | no data: %s", cfg["user_id"], ", ".join(live) or "none", ", ".join(dead) or "none")

    scored = score(items)
    log.info("[%s] scored %d items; top: %s (%.3f)", cfg["user_id"], len(scored), scored[0].item.title[:60], scored[0].combined_score)

    store = Store()
    brief_id = uuid4()
    brief, posts = synthesise(
        scored, brief_id, user_id=cfg["user_id"],
        niche=cfg["niche"], avoid_words=cfg["avoid_words"],
    )
    try:
        enrich_posts(posts, top_signal=scored[0], mood=brief.signal_mood)
    except Exception as exc:
        log.warning("[%s] media enrichment failed (non-fatal): %s", cfg["user_id"], exc)

    store.save_brief(brief, user_id=cfg["user_id"], niche_id=cfg["niche_id"])
    store.save_signals(scored, brief_id)
    for post in posts:
        store.save_post(post)

    log.info("[%s/%s] brief %s saved: quality=%.2f niche_voice=%s revisions=%d",
             cfg["user_id"], cfg["label"], brief_id, brief.quality_score or 0, brief.niche_voice_passed, brief.revision_count)
    _notify(brief_id, brief.quality_score or 0, health, to_email=cfg["notify_email"])


async def job_synthesise() -> None:
    log.info("=== JOB: synthesise ===")
    configs = _niche_configs()
    log.info("synthesising for %d niche(s)", len(configs))
    for cfg in configs:
        try:
            await _synthesise_for(cfg)
        except Exception as exc:
            log.error("[%s] synthesise failed: %s", cfg["user_id"], exc)
    log.info("=== synthesise complete ===")


async def _digest_for(cfg: dict) -> None:
    from .actions import make_brief_link
    from .relevance import filter_offniche

    items, health = await _gather_radar(_sources_for(cfg))
    if not items:
        log.error("[%s] no items fetched — skipping digest", cfg["user_id"])
        return
    items = filter_offniche(items, cfg["niche"], cfg["label"])
    if not items:
        log.error("[%s] every item filtered as off-niche — skipping digest", cfg["user_id"])
        return

    scored = score(items)
    top = scored[:10]
    log.info("[%s] scored %d items; digest carries top %d", cfg["user_id"], len(scored), len(top))

    digest = Digest(
        content_md=render_digest(top, datetime.now(timezone.utc), health),
        signals=[
            {
                "title": si.item.title,
                "source": si.item.source.value,
                "url": si.item.url,
                "combined_score": si.combined_score,
                "velocity_score": si.velocity_score,
                "volume_score": si.volume_score,
            }
            for si in top
        ],
        source_health=health,
    )
    Store().save_digest(digest, user_id=cfg["user_id"], niche_id=cfg["niche_id"])

    top_lines = "".join(
        f"<li style='margin-bottom:10px'>"
        f"<a href='{html.escape(si.item.url, quote=True)}' style='color:#0f766e'>{html.escape(si.item.title)}</a>"
        f" <span style='color:#9ca3af'>({si.item.source.value}, {si.combined_score:.2f})</span><br>"
        f"<a href='{html.escape(make_brief_link(si.item.title, si.item.url, si.item.source.value, si.combined_score, si.velocity_score, si.volume_score, user_id=cfg['user_id'], niche_id=cfg['niche_id']), quote=True)}'"
        f" style='font-size:12px;color:#0f766e;font-weight:600'>Make this a brief &rarr;</a>"
        f"</li>"
        for si in top[:5]
    )
    _send_email(
        "RadarWindow — daily signals",
        f"<p>Today's top signals in your niche, velocity-scored from the live radar.</p>"
        f"<ol>{top_lines}</ol>"
        f"{_health_html(health)}"
        f"<p style='margin-top:16px'>The full digest is on your dashboard.</p>",
        to_email=cfg["notify_email"],
    )


async def job_digest() -> None:
    """Daily signal digest per niche — radar + scoring only, no LLM, near-zero cost."""
    log.info("=== JOB: digest ===")
    configs = _niche_configs()
    log.info("digest for %d niche(s)", len(configs))
    for cfg in configs:
        try:
            await _digest_for(cfg)
        except Exception as exc:
            log.error("[%s] digest failed: %s", cfg["user_id"], exc)
    log.info("=== digest complete ===")


def _owner_lead_cfg() -> dict:
    """Config for the lead-finder. Owner-only: lead-gen hunts for the owner's own
    products, so it always runs for the owner account (RADARWINDOW_USER_ID)
    rather than per tenant. notify_email comes from the owner's settings row."""
    owner = settings.RADARWINDOW_USER_ID
    cfg = next((c for c in _niche_configs() if c["user_id"] == owner), None)
    return {
        "user_id": owner,
        "notify_email": cfg["notify_email"] if cfg else settings.NOTIFY_EMAIL,
        "lead_subreddits": settings.lead_subreddits_list,
        "lead_queries": settings.lead_queries_list,
    }


async def job_leads() -> None:
    """Find public posts a product genuinely fits, draft a helpful reply for
    each, and queue them for MANUAL review (emailed + stored). Never auto-sends."""
    from .leads import find_leads, render_leads_email

    log.info("=== JOB: leads ===")
    cfg = _owner_lead_cfg()
    if not cfg["user_id"]:
        log.error("leads: RADARWINDOW_USER_ID not set — cannot queue leads")
        return

    store = Store()
    try:
        existing = store.existing_lead_urls(cfg["user_id"])
    except Exception as exc:
        log.warning("leads: could not load existing lead urls (%s) — proceeding without dedupe", exc)
        existing = set()

    leads = await find_leads(cfg, skip_urls=existing)
    if not leads:
        log.info("=== leads complete: no new leads this run ===")
        return

    for lead in leads:
        try:
            store.save_lead(lead, user_id=cfg["user_id"])
        except Exception as exc:
            log.warning("leads: save failed for %s (%s)", lead.url, exc)

    _send_email(
        f"RadarWindow — {len(leads)} lead{'s' if len(leads) != 1 else ''} to reply to",
        render_leads_email(leads),
        to_email=cfg["notify_email"],
    )
    log.info("=== leads complete: %d queued ===", len(leads))


async def publish_brief(store: Store, publisher, brief) -> int:
    """
    Schedule all DRAFT posts of one approved brief. Returns how many were
    scheduled. Marks the brief POSTED only when something actually went out —
    a fully failed run must stay approved so the next publish retries it
    (2026-07-06).
    """
    # Stagger posts: X first, then LinkedIn 10 min later, Instagram 20 min later
    stagger = {Platform.X: 0, Platform.LINKEDIN: 10, Platform.INSTAGRAM: 20}
    base_time = datetime.now(timezone.utc) + timedelta(minutes=5)

    posts = store.get_posts(brief.id)
    scheduled_count = 0
    for post in posts:
        if post.status != PostStatus.DRAFT:
            continue
        scheduled_for = base_time + timedelta(minutes=stagger[post.platform])
        try:
            blotato_id = await publisher.schedule(post, scheduled_for)
            scheduled_count += 1
            store.update_post_status(post.id, PostStatus.SCHEDULED, blotato_id)
            store.save_audit_entry(
                AuditEntry(
                    brief_id=brief.id,
                    platform=post.platform,
                    action="scheduled",
                    blotato_response_id=blotato_id,
                    scheduled_for=scheduled_for,
                )
            )
            log.info("scheduled %s post for %s (blotato=%s)", post.platform.value, scheduled_for.isoformat(), blotato_id)
        except Exception as exc:
            log.error("failed to schedule %s post: %s", post.platform.value, exc)
            store.save_audit_entry(
                AuditEntry(
                    brief_id=brief.id,
                    platform=post.platform,
                    action="failed",
                    detail={"error": str(exc)},
                )
            )

    if scheduled_count:
        store.update_brief_status(brief.id, BriefStatus.POSTED)
    else:
        log.warning("publish: brief %s had zero successful schedules — left approved", brief.id)
    return scheduled_count


async def job_publish() -> None:
    from .publisher.blotato import BlatoPublisher

    log.info("=== JOB: publish ===")
    store = Store()
    publisher = BlatoPublisher()

    briefs = store.get_approved_briefs()
    if not briefs:
        log.info("no approved briefs — publish job is a no-op")
        return

    for brief in briefs:
        await publish_brief(store, publisher, brief)

    log.info("=== publish complete ===")


async def make_brief_from_signal(payload: dict) -> str:
    """
    One-click flow, step 1: synthesise a focused brief seeded from a single
    digest signal (chosen by the human — curation is the judgment layer).
    Runs the same three-pass quality gate as the weekly job, saves the brief
    as DRAFT so it appears in the dashboard Briefs list, and emails a
    review/approve link. Returns the new brief id as a string.
    """
    from .actions import PUBLIC_BASE_URL, approve_link
    from .models import Item, ScoredItem
    from .synthesis import synthesise

    log.info("=== JOB: make-brief-from-signal (%s) ===", payload.get("t", "")[:60])
    store = Store()

    # The token carries the owning user + niche (multi-niche); fall back to the
    # global owner for legacy links. Prefer the exact niche when the token names
    # one, else the user's first niche, so the brief uses the right voice.
    user_id = payload.get("uid") or settings.RADARWINDOW_USER_ID
    niche_id = payload.get("nid")
    user_cfgs = [c for c in _niche_configs() if c["user_id"] == user_id]
    cfg = next((c for c in user_cfgs if niche_id and c["niche_id"] == niche_id), None) \
        or (user_cfgs[0] if user_cfgs else None)
    niche_id = cfg["niche_id"] if cfg else niche_id
    niche = cfg["niche"] if cfg else None
    avoid_words = cfg["avoid_words"] if cfg else None
    to_email = cfg["notify_email"] if cfg else None

    seed = ScoredItem(
        item=Item(
            source=SourceName(payload["s"]),
            title=payload["t"],
            url=payload["u"],
            raw_score=0.0,
        ),
        volume_score=float(payload.get("vo", 0.0)),
        velocity_score=float(payload.get("vs", 0.0)),
        combined_score=float(payload.get("cs", 0.0)),
    )

    brief_id = uuid4()
    brief, posts = synthesise([seed], brief_id, user_id=user_id, niche=niche, avoid_words=avoid_words)

    from .media import enrich_posts
    try:
        enrich_posts(posts, top_signal=seed, mood=brief.signal_mood)
    except Exception as exc:
        log.warning("media enrichment failed (non-fatal): %s", exc)

    store.save_brief(brief, user_id=user_id, niche_id=niche_id)
    store.save_signals([seed], brief_id)
    for post in posts:
        store.save_post(post)

    _send_email(
        "RadarWindow — your signal brief is ready to review",
        f"<p>The brief you asked for is written: seeded from "
        f"<strong>{html.escape(payload['t'])}</strong>, passed through the three-pass "
        f"quality gate (quality {brief.quality_score or 0:.0%}, "
        f"{brief.revision_count} revision{'s' if brief.revision_count != 1 else ''}).</p>"
        f"<p style='margin-top:16px'>"
        f"<a href='{PUBLIC_BASE_URL}/briefs/{brief_id}' style='color:#0f766e;font-weight:600'>Read it on your dashboard</a>"
        f" — edit anything you like, or if it's good as it stands:</p>"
        f"<p style='margin-top:12px'><a href='{approve_link(str(brief_id))}' "
        f"style='background:#0f766e;color:#fff;padding:10px 18px;border-radius:6px;"
        f"text-decoration:none;font-weight:600'>Approve &amp; post &rarr;</a></p>"
        f"<p style='color:#9ca3af;font-size:12px;margin-top:16px'>Posts go to your connected "
        f"platforms a few minutes after you approve. Brief ID: {brief_id}</p>",
        to_email=to_email,
    )
    log.info("=== make-brief-from-signal complete (%s) ===", brief_id)
    return str(brief_id)


async def approve_and_publish(brief_id_str: str) -> int:
    """
    One-click flow, step 2: mark the brief approved and publish it now
    (instead of waiting for the Monday publish cron). Returns scheduled count.
    """
    from uuid import UUID

    from .publisher.blotato import BlatoPublisher

    store = Store()
    brief = store.get_brief(UUID(brief_id_str))
    if brief is None:
        raise ValueError("brief not found")
    if brief.status == BriefStatus.POSTED:
        return 0
    store.update_brief_status(brief.id, BriefStatus.APPROVED)
    brief.status = BriefStatus.APPROVED
    log.info("brief %s approved via email link — publishing now", brief.id)
    return await publish_brief(store, BlatoPublisher(), brief)


async def job_feedback() -> None:
    """
    Ingest engagement for recently posted content and store it, so the next
    synthesise run knows what worked. Safe no-op when the provider exposes no
    analytics — it just stores nothing.
    """
    from .publisher.blotato import BlatoPublisher
    from .feedback import store_engagement

    log.info("=== JOB: feedback ===")
    store = Store()
    publisher = BlatoPublisher()

    posted = store.get_posted_posts()
    if not posted:
        log.info("no posted content to measure — feedback job is a no-op")
        return

    rows = []
    for post in posted:
        if not post.blotato_post_id:
            continue
        metrics = await publisher.get_engagement(post.blotato_post_id)
        if not metrics:
            continue
        total = metrics["likes"] + metrics["comments"] + metrics["shares"] + metrics["clicks"]
        rate = total / max(metrics["impressions"], 1)
        rows.append(
            {
                "post_id": str(post.id),
                "brief_id": str(post.brief_id),
                "user_id": settings.RADARWINDOW_USER_ID,
                "platform": post.platform.value,
                **metrics,
                "engagement_rate": rate,
            }
        )
    store_engagement(rows)
    log.info("=== feedback complete: %d posts measured ===", len(rows))


def _health_html(health: dict[str, int] | None) -> str:
    if not health:
        return ""
    rows = "".join(
        f"<tr><td style='padding:2px 12px 2px 0'>{src}</td>"
        f"<td style='color:{'#16a34a' if n else '#9ca3af'}'>{n if n else 'no data'}</td></tr>"
        for src, n in sorted(health.items(), key=lambda x: -x[1])
    )
    return (
        "<p style='margin-top:16px'><strong>Source health</strong></p>"
        f"<table style='font-size:13px'>{rows}</table>"
    )


def _send_email(subject: str, html: str, to_email: str | None = None) -> None:
    # MailerSend — same account/verified domain (myaicraft.uk) as CostWindow.
    recipient = to_email or settings.NOTIFY_EMAIL
    if not settings.MAILERSEND_API_KEY:
        log.info("notification skipped — MAILERSEND_API_KEY not set (%s)", subject)
        return

    try:
        r = httpx.post(
            "https://api.mailersend.com/v1/email",
            headers={
                "Authorization": f"Bearer {settings.MAILERSEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": {"email": settings.MAILERSEND_FROM_EMAIL, "name": "RadarWindow"},
                "to": [{"email": recipient}],
                "subject": subject,
                "html": html,
            },
            timeout=30,
        )
        if r.is_success:
            log.info("notification sent to %s", recipient)
        else:
            log.warning("notification failed (non-fatal): %s %s", r.status_code, r.text[:200])
    except Exception as exc:
        log.warning("notification failed (non-fatal): %s", exc)


def _notify(brief_id, quality_score: float, health: dict[str, int] | None = None, to_email: str | None = None) -> None:
    _send_email(
        "RadarWindow — your intelligence brief is ready",
        f"<p>This week's analyst brief is written and waiting for you — "
        f"researched from the live radar, scored, and passed through the "
        f"three-pass quality gate (quality {quality_score:.0%}).</p>"
        f"{_health_html(health)}"
        f"<p style='margin-top:16px'>Log in to read and edit the brief. The media kit "
        f"(platform posts, imagery, audio) is derived from it and ready to download, "
        f"or approve before the publish job runs.</p>"
        f"<p style='color:#9ca3af;font-size:12px'>Brief ID: {brief_id}</p>",
        to_email=to_email,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", choices=["synthesise", "digest", "publish", "feedback", "leads", "qa", "signal-brief"], required=True)
    parser.add_argument("--token", help="signed action token (signal-brief job only)")
    args = parser.parse_args()

    if args.job == "synthesise":
        asyncio.run(job_synthesise())
    elif args.job == "digest":
        asyncio.run(job_digest())
    elif args.job == "publish":
        asyncio.run(job_publish())
    elif args.job == "feedback":
        asyncio.run(job_feedback())
    elif args.job == "leads":
        asyncio.run(job_leads())
    elif args.job == "qa":
        from .qa import job_qa

        asyncio.run(job_qa())
    elif args.job == "signal-brief":
        from .actions import verify_action

        payload = verify_action(args.token or "")
        if not payload or payload.get("a") != "mb":
            log.error("signal-brief: invalid or expired token")
            sys.exit(1)
        asyncio.run(make_brief_from_signal(payload))


if __name__ == "__main__":
    main()
