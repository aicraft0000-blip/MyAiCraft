import secrets
import hashlib
import hmac
import requests as http_requests
from functools import lru_cache
from fastapi import Header, HTTPException
from jose import jwt, JWTError
from app.config import get_settings
from app.database import get_db


def generate_api_key() -> tuple[str, str]:
    """Generate a CostWindow API key. Returns (plaintext_key, sha256_hex_hash)."""
    key = "cw_live_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash


def verify_api_key(provided: str, stored_hash: str) -> bool:
    provided_hash = hashlib.sha256(provided.encode()).hexdigest()
    return hmac.compare_digest(provided_hash, stored_hash)


@lru_cache
def _get_jwks_key() -> dict:
    """Fetch and cache the Supabase JWKS public key (ES256 or HS256)."""
    supabase_url = get_settings().supabase_url
    try:
        resp = http_requests.get(
            f"{supabase_url}/auth/v1/.well-known/jwks.json", timeout=10
        )
        keys = resp.json().get("keys", [])
        if keys:
            return keys[0]
    except Exception:
        pass
    # Fallback to the raw JWT secret value (older HS256 projects)
    return get_settings().supabase_jwt_secret


def get_user_from_jwt(authorization: str = Header(...)) -> str:
    """Validate a Supabase-issued JWT and return the user_id (UUID str)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization[7:]
    key = _get_jwks_key()
    try:
        payload = _decode_jwt(token, key)
    except JWTError:
        # The cached JWKS key may be stale (Supabase rotated keys) —
        # refetch once and retry before rejecting the token.
        _get_jwks_key.cache_clear()
        key = _get_jwks_key()
        try:
            payload = _decode_jwt(token, key)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject claim")
    return user_id


def _decode_jwt(token: str, key) -> dict:
    alg = "ES256" if isinstance(key, dict) and key.get("kty") == "EC" else "HS256"
    return jwt.decode(token, key, algorithms=[alg], options={"verify_aud": False})


def get_user_from_api_key(x_api_key: str = Header(...)) -> str:
    """Look up a user by their CostWindow API key and return user_id."""
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    db = get_db()
    result = (
        db.table("api_keys")
        .select("user_id")
        .eq("key_hash", key_hash)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid API key")
    user_id = result.data[0]["user_id"]
    try:
        db.table("api_keys").update({"last_used_at": "now()"}).eq("key_hash", key_hash).execute()
    except Exception:
        pass
    return user_id


def get_user_from_api_key_or_jwt(
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
) -> str:
    """Accept either a CostWindow API key (X-Api-Key) or a Supabase JWT.
    Used by endpoints the SDK calls with its api key AND the dashboard calls
    with a JWT (e.g. process status)."""
    if x_api_key:
        return get_user_from_api_key(x_api_key)
    if authorization:
        return get_user_from_jwt(authorization)
    raise HTTPException(status_code=401, detail="Missing X-Api-Key or Authorization header")
