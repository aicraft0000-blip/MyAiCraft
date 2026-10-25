from __future__ import annotations

import logging
from uuid import UUID

import httpx

from .config import settings
from .models import AuditEntry, Brief, BriefStatus, Digest, Lead, LeadStatus, Post, PostStatus, ScoredItem

log = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def _url(table: str) -> str:
    return f"{settings.SUPABASE_URL}/rest/v1/{table}"


def _upsert(table: str, row: dict, on_conflict: str | None = None) -> None:
    # on_conflict names the unique column(s) to merge on when it isn't the PK
    # (e.g. rw_leads' (user_id, url)); default merges on the primary key.
    params = {"on_conflict": on_conflict} if on_conflict else None
    r = httpx.post(
        _url(table),
        params=params,
        json=row,
        headers={**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
    )
    r.raise_for_status()


def _insert(table: str, rows: list[dict]) -> None:
    if not rows:
        return
    r = httpx.post(_url(table), json=rows, headers={**_headers(), "Prefer": "return=minimal"})
    r.raise_for_status()


def _select(table: str, filters: dict) -> list[dict]:
    params = {k: f"eq.{v}" for k, v in filters.items()}
    r = httpx.get(_url(table), params=params, headers=_headers())
    r.raise_for_status()
    return r.json()


def _patch(table: str, filters: dict, updates: dict) -> None:
    params = {k: f"eq.{v}" for k, v in filters.items()}
    r = httpx.patch(
        _url(table),
        params=params,
        json=updates,
        headers={**_headers(), "Prefer": "return=minimal"},
    )
    r.raise_for_status()


class Store:
    """Persistence layer — talks to Supabase via REST API directly."""

    # ------------------------------------------------------------------
    # Briefs
    # ------------------------------------------------------------------

    def save_brief(self, brief: Brief, user_id: str, niche_id: str | None = None) -> None:
        row = {
            "id": str(brief.id),
            "user_id": user_id,
            "niche_id": niche_id,
            "run_date": brief.run_date.isoformat(),
            "content_md": brief.content_md,
            "signal_mood": brief.signal_mood.value,
            "status": brief.status.value,
            "quality_score": brief.quality_score,
            "revision_count": brief.revision_count,
            "niche_voice_passed": brief.niche_voice_passed,
            "created_at": brief.created_at.isoformat(),
            "updated_at": brief.updated_at.isoformat(),
        }
        _upsert("rw_briefs", row)
        log.info("brief %s saved (status=%s)", brief.id, brief.status.value)

    def get_brief(self, brief_id: UUID) -> Brief | None:
        rows = _select("rw_briefs", {"id": str(brief_id)})
        return Brief(**rows[0]) if rows else None

    def get_approved_briefs(self) -> list[Brief]:
        rows = _select("rw_briefs", {"status": BriefStatus.APPROVED.value})
        return [Brief(**r) for r in rows]

    def update_brief_status(self, brief_id: UUID, status: BriefStatus) -> None:
        from datetime import datetime, timezone
        _patch("rw_briefs", {"id": str(brief_id)}, {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        log.info("brief %s → %s", brief_id, status.value)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def save_signals(self, signals: list[ScoredItem], brief_id: UUID) -> None:
        rows = [
            {
                "brief_id": str(brief_id),
                "source": si.item.source.value,
                "title": si.item.title,
                "url": si.item.url,
                "raw_score": si.item.raw_score,
                "comment_count": si.item.comment_count,
                "published_at": si.item.published_at.isoformat() if si.item.published_at else None,
                "fetched_at": si.item.fetched_at.isoformat(),
                "volume_score": si.volume_score,
                "velocity_score": si.velocity_score,
                "combined_score": si.combined_score,
                "metadata": si.item.metadata,
            }
            for si in signals
        ]
        _insert("rw_signals", rows)
        log.info("saved %d signals for brief %s", len(rows), brief_id)

    # ------------------------------------------------------------------
    # Digests
    # ------------------------------------------------------------------

    def all_active_niches(self) -> list[dict]:
        """Every ACTIVE niche across all users. The pipeline iterates these so a
        single account can hold several niches, each getting its own brief and
        digest for its own sources. Empty list if none (fresh install)."""
        r = httpx.get(
            _url("rw_niches"),
            params={
                "select": "id,user_id,label,niche,subreddits,github_topics,web_queries,rss_feeds,avoid_words,notify_email",
                "active": "eq.true",
            },
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()

    def update_niche(self, niche_id: str, updates: dict) -> None:
        """Self-QA auto-fixes — only ever touches the source fields it corrected."""
        _patch("rw_niches", {"id": niche_id}, updates)
        log.info("niche %s updated: %s", niche_id, ", ".join(updates))

    def latest_digest_for_niche(self, niche_id: str) -> dict | None:
        r = httpx.get(
            _url("rw_digests"),
            params={"niche_id": f"eq.{niche_id}", "order": "created_at.desc", "limit": "1"},
            headers=_headers(),
        )
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None

    def save_qa_report(self, row: dict) -> None:
        _insert("rw_qa_reports", [row])
        log.info("qa report saved for niche %s (%s)", row.get("niche_id"), row.get("status"))

    def save_digest(self, digest: Digest, user_id: str, niche_id: str | None = None) -> None:
        row = {
            "id": str(digest.id),
            "user_id": user_id,
            "niche_id": niche_id,
            "run_date": digest.run_date.isoformat(),
            "content_md": digest.content_md,
            "signals": digest.signals,
            "source_health": digest.source_health,
            "created_at": digest.created_at.isoformat(),
        }
        _upsert("rw_digests", row)
        log.info("digest %s saved (%d signals)", digest.id, len(digest.signals))

    def list_digests(self, limit: int = 14) -> list[Digest]:
        r = httpx.get(
            _url("rw_digests"),
            params={"order": "run_date.desc", "limit": str(limit)},
            headers=_headers(),
        )
        r.raise_for_status()
        return [Digest(**row) for row in r.json()]

    # ------------------------------------------------------------------
    # Leads (draft-and-queue — never auto-sent)
    # ------------------------------------------------------------------

    def save_lead(self, lead: Lead, user_id: str) -> None:
        row = {
            "id": str(lead.id),
            "user_id": user_id,
            "source": lead.source.value,
            "product": lead.product,
            "url": lead.url,
            "title": lead.title,
            "excerpt": lead.excerpt,
            "author": lead.author,
            "fit_score": lead.fit_score,
            "rationale": lead.rationale,
            "draft_reply": lead.draft_reply,
            "status": lead.status.value,
            "created_at": lead.created_at.isoformat(),
        }
        # Upsert on the (user_id, url) unique key so a re-run never double-queues
        # the same thread. existing_lead_urls() is the primary dedupe guard; this
        # makes the write itself idempotent as a backstop.
        _upsert("rw_leads", row, on_conflict="user_id,url")
        log.info("lead queued: %s (%s, fit=%.2f)", lead.url, lead.product, lead.fit_score)

    def existing_lead_urls(self, user_id: str) -> set[str]:
        """URLs already queued for this user — the dedupe guard for the finder."""
        r = httpx.get(
            _url("rw_leads"),
            params={"select": "url", "user_id": f"eq.{user_id}"},
            headers=_headers(),
        )
        r.raise_for_status()
        return {row["url"] for row in r.json()}

    def list_leads(self, user_id: str, status: LeadStatus | None = None, limit: int = 50) -> list[Lead]:
        params = {"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": str(limit)}
        if status is not None:
            params["status"] = f"eq.{status.value}"
        r = httpx.get(_url("rw_leads"), params=params, headers=_headers())
        r.raise_for_status()
        return [Lead(**row) for row in r.json()]

    def update_lead_status(self, lead_id: UUID, status: LeadStatus) -> None:
        _patch("rw_leads", {"id": str(lead_id)}, {"status": status.value})
        log.info("lead %s → %s", lead_id, status.value)

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------

    def save_post(self, post: Post) -> None:
        row = {
            "id": str(post.id),
            "brief_id": str(post.brief_id),
            "platform": post.platform.value,
            "content": post.content,
            "status": post.status.value,
            "image_path": post.image_path,
            "audio_path": post.audio_path,
            "video_path": post.video_path,
            "image_public_url": post.image_public_url,
            "audio_public_url": post.audio_public_url,
            "video_public_url": post.video_public_url,
            "blotato_post_id": post.blotato_post_id,
            "scheduled_for": post.scheduled_for.isoformat() if post.scheduled_for else None,
            "created_at": post.created_at.isoformat(),
        }
        _upsert("rw_posts", row)

    def get_posts(self, brief_id: UUID) -> list[Post]:
        rows = _select("rw_posts", {"brief_id": str(brief_id)})
        return [Post(**r) for r in rows]

    def get_posted_posts(self) -> list[Post]:
        """All posts that have been posted/scheduled (have a provider id) — for feedback."""
        rows = _select("rw_posts", {"status": PostStatus.POSTED.value})
        return [Post(**r) for r in rows]

    def update_post_status(self, post_id: UUID, status: PostStatus, blotato_post_id: str | None = None) -> None:
        updates: dict = {"status": status.value}
        if blotato_post_id:
            updates["blotato_post_id"] = blotato_post_id
        _patch("rw_posts", {"id": str(post_id)}, updates)

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def save_audit_entry(self, entry: AuditEntry) -> None:
        row = {
            "id": str(entry.id),
            "brief_id": str(entry.brief_id),
            "platform": entry.platform.value,
            "action": entry.action,
            "blotato_response_id": entry.blotato_response_id,
            "scheduled_for": entry.scheduled_for.isoformat() if entry.scheduled_for else None,
            "created_at": entry.created_at.isoformat(),
            "detail": entry.detail,
        }
        _insert("rw_audit_log", [row])
        log.info("audit: brief=%s platform=%s action=%s", entry.brief_id, entry.platform.value, entry.action)
