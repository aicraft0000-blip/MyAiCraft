"""Stripe webhook — provisions RadarWindow customers.

checkout.session.completed → upsert rw_customers (plan by price id) and send
the welcome email via MailerSend. customer.subscription.updated/deleted keep
`status` in sync so the registration gate follows the subscription.
Same pattern as CostWindow's webhook.
"""

import hashlib
import hmac
import json
import logging
import time

import httpx
from fastapi import APIRouter, Header, HTTPException, Request

from app.config import get_settings
from app.database import get_db

log = logging.getLogger("radarwindow.webhook")
router = APIRouter()

PLAN_LABEL = {"radar": "Radar", "radar_pro": "Radar Pro"}
PLAN_PRICE = {"radar": "£29/month", "radar_pro": "£79/month"}


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------

def verify_stripe_signature(payload: bytes, header: str, secret: str, *, tolerance: int = 300, now: int | None = None) -> bool:
    """Validate a Stripe-Signature header against the raw payload."""
    try:
        parts = dict(p.split("=", 1) for p in header.split(","))
        timestamp = int(parts["t"])
        signature = parts["v1"]
    except (KeyError, ValueError, AttributeError):
        return False
    if abs((now if now is not None else int(time.time())) - timestamp) > tolerance:
        return False
    signed = f"{timestamp}.{payload.decode()}".encode()
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def plan_from_price_id(price_id: str | None, radar_price_id: str, radar_pro_price_id: str) -> str:
    if price_id and price_id == radar_pro_price_id:
        return "radar_pro"
    return "radar"


# ---------------------------------------------------------------------------
# Welcome email
# ---------------------------------------------------------------------------

async def _send_welcome_email(email: str, plan: str) -> None:
    settings = get_settings()
    if not settings.mailersend_api_key:
        log.warning("[WELCOME EMAIL] SKIPPED for %s — MAILERSEND_API_KEY not configured", email)
        return

    label, price = PLAN_LABEL.get(plan, "Radar"), PLAN_PRICE.get(plan, "£29/month")
    pro_line = (
        "<li><strong>Competitor tracking:</strong> include 3–5 competitor accounts or "
        "newsletters in your reply — the desk maps what they cover and steers your "
        "briefs into the gaps.</li>"
        if plan == "radar_pro" else ""
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family: Georgia, serif; color: #1d1c17; max-width: 560px; margin: 0 auto; padding: 24px;">
  <p style="font-family: monospace; font-size: 11px; letter-spacing: 2px; color: #1a7a4d;">
    RADARWINDOW · INTELLIGENCE BRIEF SERVICE
  </p>
  <h1 style="font-size: 22px;">Your radar is being pointed at your world.</h1>
  <p>Thanks for subscribing to <strong>RadarWindow {label}</strong> ({price}). Three steps and you're on the distribution list:</p>
  <ol style="line-height: 1.8;">
    <li><strong>Create your account</strong> — <a href="https://radarwindow.com/register">radarwindow.com/register</a>,
        using this email address ({email}). Access is tied to your subscription.</li>
    <li><strong>Reply to this email with your niche</strong> — two or three sentences on
        the world you want watched: the communities, the vocabulary, what "insider" sounds
        like. A human configures your radar from this within one working day.{pro_line}</li>
    <li><strong>Your first brief lands on Monday at 07:00 UK</strong> — researched, scored,
        written and revised autonomously, with the full media kit attached to your dashboard.</li>
  </ol>
  <p style="font-size: 13px; color: #6b675a;">Every brief passes a three-pass quality gate
  before it reaches you. If one ever reads like it was written by a machine trying to sound
  clever, reply and say so — the gate gets stricter.</p>
  <p>— the owner, RadarWindow</p>
</body></html>"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                "https://api.mailersend.com/v1/email",
                headers={"Authorization": f"Bearer {settings.mailersend_api_key}"},
                json={
                    "from": {"email": settings.mailersend_from_email, "name": "RadarWindow"},
                    "to": [{"email": email}],
                    "subject": "Welcome to RadarWindow — your radar is being configured",
                    "html": html,
                },
            )
        if res.is_success:
            log.info("[WELCOME EMAIL] Sent to %s (%s)", email, plan)
        else:
            log.warning("[WELCOME EMAIL] Failed for %s: %s %s", email, res.status_code, res.text[:200])
    except Exception as exc:
        log.warning("[WELCOME EMAIL] Failed for %s: %s", email, exc)


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

async def _handle_checkout_completed(session: dict) -> None:
    settings = get_settings()
    email = (
        (session.get("customer_details") or {}).get("email")
        or session.get("customer_email")
        or ""
    ).lower().strip()
    if not email:
        log.warning("webhook: checkout.session.completed with no email — skipping")
        return

    # Resolve plan from the subscription's price via the Stripe API.
    price_id = None
    sub_id = session.get("subscription")
    if sub_id and settings.stripe_secret_key:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"https://api.stripe.com/v1/subscriptions/{sub_id}",
                    headers={"Authorization": f"Bearer {settings.stripe_secret_key}"},
                )
            if r.is_success:
                items = r.json().get("items", {}).get("data", [])
                if items:
                    price_id = (items[0].get("price") or {}).get("id")
        except Exception as exc:
            log.warning("webhook: could not resolve subscription price: %s", exc)
    plan = plan_from_price_id(price_id, settings.stripe_radar_price_id, settings.stripe_radar_pro_price_id)

    db = get_db()
    db.table("rw_customers").upsert(
        {
            "email": email,
            "plan": plan,
            "status": "active",
            "stripe_customer_id": session.get("customer"),
            "stripe_subscription_id": sub_id,
            "updated_at": "now()",
        },
        on_conflict="email",
    ).execute()
    log.info("webhook: customer %s provisioned (%s)", email, plan)
    await _send_welcome_email(email, plan)


def _handle_subscription_status(event_type: str, subscription: dict) -> None:
    sub_id = subscription.get("id")
    if not sub_id:
        return
    if event_type == "customer.subscription.deleted":
        status = "canceled"
    else:
        stripe_status = subscription.get("status", "active")
        status = "active" if stripe_status in ("active", "trialing") else stripe_status
    db = get_db()
    db.table("rw_customers").update(
        {"status": status, "updated_at": "now()"}
    ).eq("stripe_subscription_id", sub_id).execute()
    log.info("webhook: subscription %s → %s", sub_id, status)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    payload = await request.body()
    if not stripe_signature or not verify_stripe_signature(payload, stripe_signature, settings.stripe_webhook_secret):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = json.loads(payload)
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    if etype == "checkout.session.completed" and obj.get("mode") == "subscription":
        await _handle_checkout_completed(obj)
    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        _handle_subscription_status(etype, obj)

    return {"received": True}
