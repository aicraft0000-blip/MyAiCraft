from fastapi import APIRouter, Depends
from app.dependencies import get_user_from_jwt
from app.database import get_db

router = APIRouter()


@router.get("")
def list_digests(user_id: str = Depends(get_user_from_jwt)):
    """Latest daily signal digests — radar + scoring output, newest first."""
    db = get_db()
    result = (
        db.table("rw_digests")
        .select("id, run_date, content_md, signals, source_health, created_at, niche_id")
        .eq("user_id", user_id)
        .order("run_date", desc=True)
        .limit(14)
        .execute()
    )
    digests = result.data or []

    # Enrich each signal with a signed "make this a brief" action link — the
    # same two-click flow as the digest email. Links are minted fresh on every
    # view (72h expiry from now), so old digests stay actionable. A signing
    # failure must never break the digest list.
    from radarwindow.actions import make_brief_link

    for d in digests:
        for s in d.get("signals") or []:
            try:
                s["make_brief_url"] = make_brief_link(
                    s.get("title", ""),
                    s.get("url", ""),
                    s.get("source", ""),
                    float(s.get("combined_score") or 0),
                    float(s.get("velocity_score") or 0),
                    float(s.get("volume_score") or 0),
                    user_id=user_id,
                    niche_id=d.get("niche_id"),
                )
            except Exception:
                pass
    return digests
