from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import io
import logging
from app.dependencies import get_user_from_jwt
from app.database import get_db
from app.models import BriefPatch, PostPatch
from app.mediakit import build_media_kit
from app.routers.public import make_slug
from datetime import datetime, timezone

router = APIRouter()


@router.get("")
def list_briefs(user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    result = (
        db.table("rw_briefs")
        .select("id, run_date, status, signal_mood, quality_score, revision_count, niche_voice_passed, created_at, niche_id, rw_niches(label)")
        .eq("user_id", user_id)
        .order("run_date", desc=True)
        .limit(50)
        .execute()
    )
    # Flatten the embedded niche into a plain `niche_label` for the client.
    briefs = result.data or []
    for b in briefs:
        niche = b.pop("rw_niches", None)
        b["niche_label"] = niche.get("label") if isinstance(niche, dict) else None
    return briefs


@router.get("/{brief_id}")
def get_brief(brief_id: str, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    result = (
        db.table("rw_briefs")
        .select("*")
        .eq("id", brief_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Brief not found")
    brief = result.data

    posts_result = (
        db.table("rw_posts")
        .select("*")
        .eq("brief_id", brief_id)
        .execute()
    )
    brief["posts"] = posts_result.data or []

    audit_result = (
        db.table("rw_audit_log")
        .select("*")
        .eq("brief_id", brief_id)
        .order("created_at", desc=True)
        .execute()
    )
    brief["audit_log"] = audit_result.data or []

    # Source health — how many signals each radar source contributed.
    sig_result = (
        db.table("rw_signals").select("source").eq("brief_id", brief_id).execute()
    )
    counts: dict[str, int] = {}
    for row in sig_result.data or []:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    all_sources = ["reddit", "hackernews", "github", "polymarket", "websearch"]
    brief["source_health"] = {s: counts.get(s, 0) for s in all_sources}
    for extra in counts:
        if extra not in brief["source_health"]:
            brief["source_health"][extra] = counts[extra]

    return brief


@router.get("/{brief_id}/download")
def download_media_kit(brief_id: str, user_id: str = Depends(get_user_from_jwt)):
    """Assemble and stream the media-kit ZIP — RadarWindow's core deliverable."""
    db = get_db()
    brief_res = (
        db.table("rw_briefs")
        .select("*")
        .eq("id", brief_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not brief_res.data:
        raise HTTPException(status_code=404, detail="Brief not found")

    posts = (db.table("rw_posts").select("*").eq("brief_id", brief_id).execute()).data or []
    signals = (
        db.table("rw_signals")
        .select("source, title, url, raw_score, comment_count, combined_score, velocity_score, volume_score, published_at, metadata")
        .eq("brief_id", brief_id)
        .order("combined_score", desc=True)
        .execute()
    ).data or []

    filename, zip_bytes = build_media_kit(brief_res.data, posts, signals)
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{brief_id}")
def patch_brief(brief_id: str, body: BriefPatch, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    # Verify ownership
    check = (
        db.table("rw_briefs")
        .select("id, status, run_date, public_slug")
        .eq("id", brief_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Brief not found")

    if body.status and body.status not in ("draft", "approved", "archived"):
        raise HTTPException(status_code=400, detail="Invalid status")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    # First publish mints a permanent slug for the public page.
    slug = check.data.get("public_slug")
    if body.is_public and not slug:
        slug = make_slug(check.data["run_date"], brief_id)
        updates["public_slug"] = slug

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db.table("rw_briefs").update(updates).eq("id", brief_id).execute()
    return {"status": "ok", "public_slug": slug}


@router.post("/{brief_id}/approve")
async def approve_brief(brief_id: str, user_id: str = Depends(get_user_from_jwt)):
    """Approve a draft brief and post it to the connected platforms straight away
    (staggered: X first, LinkedIn +10 min, Instagram +20 min). If posting fails,
    the brief is left in 'approved' state so the Monday publish cron retries it."""
    db = get_db()
    check = (
        db.table("rw_briefs")
        .select("id, status")
        .eq("id", brief_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Brief not found")
    if check.data["status"] != "draft":
        raise HTTPException(status_code=400, detail="Only draft briefs can be approved")

    # Approve + publish now. approve_and_publish sets status='approved' before it
    # attempts to schedule, so a mid-publish failure still leaves the brief queued
    # for the Monday cron — nothing is silently lost.
    from radarwindow.main import approve_and_publish

    try:
        scheduled = await approve_and_publish(brief_id)
    except Exception as exc:
        logging.getLogger("radarwindow.web").error(
            "approve+publish failed for %s: %s", brief_id, exc
        )
        raise HTTPException(
            status_code=502,
            detail="Approved, but posting hit a problem — the Monday publish run will retry.",
        )

    if scheduled == 0:
        return {
            "status": "approved",
            "scheduled": 0,
            "message": "Approved, but nothing was scheduled — check your connected accounts.",
        }
    return {
        "status": "posted",
        "scheduled": scheduled,
        "message": f"Approved — {scheduled} post{'s' if scheduled != 1 else ''} scheduled to your platforms.",
    }


@router.patch("/posts/{post_id}")
def patch_post(post_id: str, body: PostPatch, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    # Verify the post belongs to a brief owned by this user
    post_result = (
        db.table("rw_posts")
        .select("id, brief_id")
        .eq("id", post_id)
        .maybe_single()
        .execute()
    )
    if not post_result.data:
        raise HTTPException(status_code=404, detail="Post not found")

    brief_check = (
        db.table("rw_briefs")
        .select("id")
        .eq("id", post_result.data["brief_id"])
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not brief_check.data:
        raise HTTPException(status_code=403, detail="Forbidden")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    db.table("rw_posts").update(updates).eq("id", post_id).execute()
    return {"status": "ok"}
