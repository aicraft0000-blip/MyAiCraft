from fastapi import APIRouter, HTTPException, Depends
from supabase import create_client
from app.models import (
    RegisterRequest, LoginRequest, LoginResponse, RefreshRequest,
    UserSettingsPatch, NicheCreate, NichePatch,
)
from app.dependencies import get_user_from_jwt
from app.database import get_db
from app.config import get_settings

router = APIRouter()


@router.post("/register")
def register(req: RegisterRequest):
    settings = get_settings()
    db = get_db()

    # Access is tied to an active subscription (rw_customers, written by the
    # Stripe webhook). Public briefs stay free at /p — no account needed.
    customer = (
        db.table("rw_customers")
        .select("status")
        .eq("email", req.email.lower().strip())
        .execute()
    )
    if not customer.data or customer.data[0]["status"] != "active":
        raise HTTPException(
            status_code=403,
            detail="No active subscription found for this email. Subscribe at radarwindow.com/pricing — the public briefs at /p are free to read.",
        )

    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        result = auth_client.auth.sign_up({"email": req.email, "password": req.password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_id = result.user.id
    db.table("rw_users").insert({"id": user_id, "email": req.email}).execute()
    # Account-level settings (blotato key, default notify) live on rw_user_settings.
    db.table("rw_user_settings").insert({"user_id": user_id}).execute()
    # A starter niche so the account produces briefs immediately — they can add
    # more, or edit this one, from Settings.
    db.table("rw_niches").insert({"user_id": user_id, "label": "My niche"}).execute()
    return {"message": "Account created. Check your email to confirm.", "user_id": user_id}


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    settings = get_settings()
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        result = auth_client.auth.sign_in_with_password({"email": req.email, "password": req.password})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return LoginResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        user_id=result.user.id,
        email=result.user.email,
    )


@router.post("/refresh")
def refresh_token(req: RefreshRequest):
    settings = get_settings()
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        result = auth_client.auth.refresh_session(req.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }


@router.get("/settings")
def get_settings_route(user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    result = db.table("rw_user_settings").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return {}
    row = result.data[0]
    # Never return the raw blotato key — just whether it's set
    has_blotato = bool(row.pop("blotato_api_key", None))
    return {**row, "has_blotato_key": has_blotato}


@router.patch("/settings")
def update_settings(body: UserSettingsPatch, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    from datetime import datetime, timezone
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db.table("rw_user_settings").upsert({"user_id": user_id, **updates}).execute()
    return {"status": "ok"}


@router.get("/niches")
def list_niches(user_id: str = Depends(get_user_from_jwt)):
    """All of this account's niches (active + paused), newest first. Each one
    drives its own weekly brief + daily digest for its own sources."""
    db = get_db()
    result = (
        db.table("rw_niches")
        .select("id, label, niche, subreddits, github_topics, web_queries, rss_feeds, avoid_words, notify_email, active, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


@router.post("/niches")
def create_niche(body: NicheCreate, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    row = {"user_id": user_id, **body.model_dump()}
    result = db.table("rw_niches").insert(row).execute()
    return (result.data or [{}])[0]


@router.patch("/niches/{niche_id}")
def update_niche(niche_id: str, body: NichePatch, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    owned = (
        db.table("rw_niches").select("id").eq("id", niche_id).eq("user_id", user_id)
        .maybe_single().execute()
    )
    if not owned or not owned.data:
        raise HTTPException(status_code=404, detail="Niche not found")
    from datetime import datetime, timezone
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db.table("rw_niches").update(updates).eq("id", niche_id).eq("user_id", user_id).execute()
    return {"status": "ok"}


@router.delete("/niches/{niche_id}")
def delete_niche(niche_id: str, user_id: str = Depends(get_user_from_jwt)):
    """Delete a niche. Its past briefs/digests are kept (niche_id set null via
    FK) so history is never lost — only the config and future runs stop."""
    db = get_db()
    owned = (
        db.table("rw_niches").select("id").eq("id", niche_id).eq("user_id", user_id)
        .maybe_single().execute()
    )
    if not owned or not owned.data:
        raise HTTPException(status_code=404, detail="Niche not found")
    # Keep at least one niche so the account keeps producing briefs.
    count = db.table("rw_niches").select("id").eq("user_id", user_id).execute()
    if len(count.data or []) <= 1:
        raise HTTPException(status_code=400, detail="You need at least one niche. Add another before deleting this one.")
    db.table("rw_niches").delete().eq("id", niche_id).eq("user_id", user_id).execute()
    return {"status": "ok"}


@router.post("/settings/suggest-sources")
def suggest_sources_route(body: dict, user_id: str = Depends(get_user_from_jwt)):
    """Given a niche, suggest the sources RadarWindow should watch for it —
    the 'guide me to enough sources' step. Returns comma-joined strings ready
    to drop straight into the settings fields."""
    from radarwindow.suggest import suggest_sources
    niche = (body.get("niche") or "").strip()
    if not niche:
        raise HTTPException(status_code=400, detail="Enter your niche first, then suggest sources.")
    s = suggest_sources(niche)
    return {
        "subreddits":    ",".join(s["subreddits"]),
        "github_topics": ",".join(s["github_topics"]),
        "web_queries":   ",".join(s["web_queries"]),
    }
