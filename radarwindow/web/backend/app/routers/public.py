"""Public brief pages — read-only, no auth. Only briefs the owner has
explicitly made public are served; user ids, posts, and drafts never leave."""
import re
from fastapi import APIRouter, HTTPException
from app.database import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without a DB)
# ---------------------------------------------------------------------------

def derive_title(content_md: str, run_date: str) -> str:
    """First markdown heading, falling back to the run date."""
    for line in content_md.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return f"Brief — {run_date[:10]}"


def make_excerpt(content_md: str, length: int = 200) -> str:
    """First ~length chars of body text — headings and markdown stripped."""
    body = []
    for line in content_md.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        body.append(re.sub(r"^[-*]\s+", "", stripped))
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", " ".join(body))
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "…"


def make_slug(run_date: str, brief_id: str) -> str:
    """Public slug: YYYY-MM-DD + first 8 chars of the brief id."""
    return f"{run_date[:10]}-{brief_id[:8]}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/briefs")
def list_public_briefs():
    db = get_db()
    result = (
        db.table("rw_briefs")
        .select("public_slug, run_date, content_md")
        .eq("is_public", True)
        .order("run_date", desc=True)
        .limit(50)
        .execute()
    )
    return [
        {
            "slug": row["public_slug"],
            "title": derive_title(row["content_md"], row["run_date"]),
            "run_date": row["run_date"],
            "excerpt": make_excerpt(row["content_md"]),
        }
        for row in (result.data or [])
        if row.get("public_slug")
    ]


@router.get("/briefs/{slug}")
def get_public_brief(slug: str):
    db = get_db()
    result = (
        db.table("rw_briefs")
        .select("id, public_slug, run_date, content_md")
        .eq("public_slug", slug)
        .eq("is_public", True)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        raise HTTPException(status_code=404, detail="Brief not found")
    brief = result.data

    # Source health — derived from signals, same as the private view.
    sig_result = (
        db.table("rw_signals").select("source").eq("brief_id", brief["id"]).execute()
    )
    counts: dict[str, int] = {}
    for row in sig_result.data or []:
        counts[row["source"]] = counts.get(row["source"], 0) + 1

    return {
        "slug": brief["public_slug"],
        "title": derive_title(brief["content_md"], brief["run_date"]),
        "run_date": brief["run_date"],
        "content_md": brief["content_md"],
        "source_health": counts or None,
    }
