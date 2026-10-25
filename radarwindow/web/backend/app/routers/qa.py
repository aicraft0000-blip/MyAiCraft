from fastapi import APIRouter, Depends
from app.dependencies import get_user_from_jwt
from app.database import get_db

router = APIRouter()


@router.get("/latest")
def latest_qa(user_id: str = Depends(get_user_from_jwt)):
    """The most recent self-QA run: latest report per niche, newest first.

    Powers the dashboard's QA notification — confirms the recurring alignment
    check ran and whether anything was auto-fixed or needs attention.
    """
    db = get_db()
    result = (
        db.table("rw_qa_reports")
        .select("id, niche_id, status, on_niche_pct, findings, summary, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    rows = result.data or []

    # Keep only each niche's newest report so the banner reflects the last run.
    latest: list[dict] = []
    seen: set = set()
    for r in rows:
        key = r.get("niche_id") or "global"
        if key in seen:
            continue
        seen.add(key)
        latest.append(r)

    # Label the niches for display.
    niche_ids = [r["niche_id"] for r in latest if r.get("niche_id")]
    labels = {}
    if niche_ids:
        n = db.table("rw_niches").select("id, label").in_("id", niche_ids).execute()
        labels = {row["id"]: row["label"] for row in (n.data or [])}
    for r in latest:
        r["niche_label"] = labels.get(r.get("niche_id"), "Default")
    return latest
