"""
Signed one-click action tokens for email buttons.

The daily digest email carries a "Make this a brief" button per signal, and the
"brief ready" email carries an "Approve & post" button. Both are HMAC-signed
URLs handled by web/backend/app/routers/actions.py. Every GET renders a confirm
form and the real work happens on POST — email scanners prefetch GET links, and
a prefetch must never trigger an LLM run or a publish.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://radarwindow.com")

MAKE_BRIEF_EXP_HOURS = 72       # digest buttons live 3 days
APPROVE_EXP_HOURS = 24 * 7      # approve buttons live a week


def _secret() -> bytes:
    for key in ("ACTION_SECRET", "SUPABASE_JWT_SECRET", "SUPABASE_KEY"):
        val = os.environ.get(key)
        if val:
            return val.encode()
    raise RuntimeError("no signing secret available (ACTION_SECRET / SUPABASE_JWT_SECRET / SUPABASE_KEY)")


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_action(payload: dict[str, Any], exp_hours: float) -> str:
    body = dict(payload)
    body["exp"] = int(time.time() + exp_hours * 3600)
    blob = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    mac = hmac.new(_secret(), blob, hashlib.sha256).digest()
    return f"{_b64e(blob)}.{_b64e(mac)}"


def verify_action(token: str) -> dict[str, Any] | None:
    """Returns the payload if the signature is valid and unexpired, else None."""
    try:
        blob_s, mac_s = token.split(".", 1)
        blob = _b64d(blob_s)
        if not hmac.compare_digest(hmac.new(_secret(), blob, hashlib.sha256).digest(), _b64d(mac_s)):
            return None
        payload = json.loads(blob)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def make_brief_link(title: str, url: str, source: str, combined: float, velocity: float, volume: float,
                    user_id: str = "", niche_id: str | None = None) -> str:
    payload = {"a": "mb", "t": title[:300], "u": url, "s": source,
               "cs": round(combined, 4), "vs": round(velocity, 4), "vo": round(volume, 4)}
    if user_id:
        payload["uid"] = user_id  # owns the resulting brief (multi-tenant)
    if niche_id:
        payload["nid"] = niche_id  # which niche's voice the brief uses (multi-niche)
    token = sign_action(payload, MAKE_BRIEF_EXP_HOURS)
    return f"{PUBLIC_BASE_URL}/api/actions/make-brief?token={token}"


def approve_link(brief_id: str) -> str:
    token = sign_action({"a": "ap", "b": brief_id}, APPROVE_EXP_HOURS)
    return f"{PUBLIC_BASE_URL}/api/actions/approve-post?token={token}"
