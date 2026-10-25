import requests as http_requests
from functools import lru_cache
from fastapi import Header, HTTPException
from jose import jwt, JWTError
from app.config import get_settings


@lru_cache
def _get_jwks_key() -> dict:
    supabase_url = get_settings().supabase_url
    try:
        resp = http_requests.get(f"{supabase_url}/auth/v1/.well-known/jwks.json", timeout=10)
        keys = resp.json().get("keys", [])
        if keys:
            return keys[0]
    except Exception:
        pass
    return get_settings().supabase_jwt_secret


def get_user_from_jwt(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization[7:]
    key = _get_jwks_key()
    try:
        payload = _decode_jwt(token, key)
    except JWTError:
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
