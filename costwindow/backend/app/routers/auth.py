from fastapi import APIRouter, HTTPException, Depends
from supabase import create_client
from app.models import (
    RegisterRequest, LoginRequest, LoginResponse, RefreshRequest,
    ApiKeyResponse, ApiKeyInfoResponse, UserSettingsUpdate,
)
from app.dependencies import generate_api_key, get_user_from_jwt
from app.database import get_db
from app.config import get_settings
from app.plans import plan_from_customer_row, resolve_user_plan, FREE_PROCESS_LIMIT
from app.ratelimit import rate_limit

router = APIRouter()

_register_limit = rate_limit("register", limit=5, window_s=3600)   # 5/hour/IP
_login_limit = rate_limit("login", limit=10, window_s=300)         # 10 per 5 min/IP


@router.post("/register", dependencies=[Depends(_register_limit)])
def register(req: RegisterRequest):
    settings = get_settings()
    db = get_db()

    # Paid customers (Stripe webhook writes `customers`) register onto their
    # plan; everyone else registers onto the free tier — every feature,
    # capped at FREE_PROCESS_LIMIT processes.
    customer = (
        db.table("customers")
        .select("plan, status")
        .eq("email", req.email.lower().strip())
        .execute()
    )
    plan = plan_from_customer_row(customer.data[0] if customer.data else None)

    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        result = auth_client.auth.sign_up({"email": req.email, "password": req.password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_id = result.user.id
    db.table("users").insert({"id": user_id, "email": req.email, "plan": plan}).execute()
    db.table("user_settings").insert({"user_id": user_id}).execute()
    return {"message": "Registered. Check your email to confirm.", "user_id": user_id, "plan": plan}


@router.get("/plan")
def get_plan(user_id: str = Depends(get_user_from_jwt)):
    """Effective plan + free-tier limit, for dashboard gating/upsell copy."""
    db = get_db()
    plan = resolve_user_plan(db, user_id)
    return {"plan": plan, "free_process_limit": FREE_PROCESS_LIMIT}


@router.post("/login", response_model=LoginResponse, dependencies=[Depends(_login_limit)])
def login(req: LoginRequest):
    settings = get_settings()
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        result = auth_client.auth.sign_in_with_password(
            {"email": req.email, "password": req.password}
        )
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


@router.post("/apikey/generate", response_model=ApiKeyResponse)
def generate_key(user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    key, key_hash = generate_api_key()
    key_prefix = key[:16]

    db.table("api_keys").delete().eq("user_id", user_id).execute()
    db.table("api_keys").insert({
        "user_id": user_id,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
    }).execute()

    return ApiKeyResponse(
        api_key=key,
        key_prefix=key_prefix,
        message="Store this key securely — it will not be shown again.",
    )


@router.get("/apikey/info", response_model=ApiKeyInfoResponse)
def key_info(user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    result = (
        db.table("api_keys")
        .select("key_prefix, created_at, last_used_at")
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        return ApiKeyInfoResponse(has_key=False)
    row = result.data[0]
    return ApiKeyInfoResponse(has_key=True, **row)


@router.get("/settings")
def get_user_settings(user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    result = db.table("user_settings").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return {"currency": "GBP", "spike_threshold": 2.0, "notifications_enabled": True}
    return result.data[0]


@router.patch("/settings")
def update_user_settings(body: UserSettingsUpdate, user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    db.table("user_settings").upsert({"user_id": user_id, **updates}).execute()
    return {"status": "ok"}
