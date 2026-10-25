from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_user_from_jwt
from app.database import get_db
from app.models import ManualEntryRequest, ManualEntryUpdate
from app.plans import resolve_user_plan, can_add_process, count_processes

router = APIRouter()


@router.get("/manual-entries")
def list_manual_entries(user_id: str = Depends(get_user_from_jwt), limit: int = 50):
    db = get_db()
    rows = (
        db.table("api_calls")
        .select("id, cost_usd, called_at, provider, metadata, processes(label)")
        .eq("user_id", user_id)
        .eq("is_manual", True)
        .order("called_at", desc=True)
        .limit(limit)
        .execute()
        .data or []
    )
    return [
        {
            "id": r["id"],
            "label": (r.get("processes") or {}).get("label", "unknown"),
            "provider": r["provider"],
            "cost_usd": float(r["cost_usd"]),
            "called_at": r["called_at"],
            "notes": (r.get("metadata") or {}).get("notes"),
        }
        for r in rows
    ]


@router.patch("/manual-entry/{entry_id}")
def update_manual_entry(entry_id: str, req: ManualEntryUpdate, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    existing = (
        db.table("api_calls")
        .select("id, metadata")
        .eq("id", entry_id).eq("user_id", user_id).eq("is_manual", True)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Manual entry not found")

    updates: dict = {}
    if req.cost_usd is not None:
        if req.cost_usd < 0:
            raise HTTPException(status_code=400, detail="Cost cannot be negative")
        updates["cost_usd"] = req.cost_usd
    if req.called_at is not None:
        updates["called_at"] = req.called_at.isoformat()
    if req.notes is not None:
        meta = existing.data[0].get("metadata") or {}
        meta["notes"] = req.notes or None
        updates["metadata"] = meta
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = db.table("api_calls").update(updates).eq("id", entry_id).execute()
    return result.data[0]


@router.delete("/manual-entry/{entry_id}", status_code=204)
def delete_manual_entry(entry_id: str, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    existing = (
        db.table("api_calls")
        .select("id")
        .eq("id", entry_id).eq("user_id", user_id).eq("is_manual", True)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Manual entry not found")
    db.table("api_calls").delete().eq("id", entry_id).execute()


@router.post("/manual-entry")
def create_manual_entry(req: ManualEntryRequest, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()

    existing = (
        db.table("processes")
        .select("id")
        .eq("user_id", user_id)
        .eq("label", req.label)
        .execute()
    )

    if existing.data:
        process_id = existing.data[0]["id"]
    else:
        # Free-tier cap applies here too, or manual entries would be a bypass.
        plan = resolve_user_plan(db, user_id)
        if not can_add_process(plan, count_processes(db, user_id)):
            raise HTTPException(
                status_code=403,
                detail="Free plan is limited to 2 processes. Upgrade to add more.",
            )
        created = db.table("processes").insert({
            "user_id": user_id,
            "label": req.label,
            "provider": req.provider,
        }).execute()
        process_id = created.data[0]["id"]

    db.table("api_calls").insert({
        "process_id": process_id,
        "user_id": user_id,
        "model": "manual",
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "cost_usd": req.cost_usd,
        "provider": req.provider,
        "called_at": req.called_at.isoformat(),
        "is_manual": True,
        "metadata": {"notes": req.notes} if req.notes else None,
    }).execute()

    return {"status": "ok", "process_id": process_id}
