import hmac
import hashlib
import json
import httpx
from fastapi import APIRouter, Request, HTTPException
from app.config import get_settings
from app.database import get_db

router = APIRouter()


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
        timestamp = parts.get("t", "")
        v1 = parts.get("v1", "")
        signed = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)
    except Exception:
        return False


def _resolve_plan(price_id: str) -> str:
    settings = get_settings()
    if price_id == settings.stripe_yearly_price_id:
        return "yearly"
    return "monthly"


async def _send_welcome_email(email: str, plan: str) -> None:
    settings = get_settings()
    if not settings.mailersend_api_key:
        print(f"[WELCOME EMAIL] SKIPPED for {email} — MAILERSEND_API_KEY not configured")
        return

    plan_label = "Yearly" if plan == "yearly" else "Monthly"
    plan_price = "£99/year" if plan == "yearly" else "£12/month"
    register_url = "https://costwindow.com/register"
    api_base = settings.public_api_url

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family:'DM Sans',Arial,sans-serif;background:#f5f5f5;padding:40px;margin:0;">
<div style="max-width:580px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;">

  <div style="background:#111110;padding:32px 40px;">
    <span style="font-family:'Space Mono',monospace;font-size:1.1rem;font-weight:700;color:#F59E0B;letter-spacing:0.05em;">CostWindow</span>
  </div>

  <div style="padding:40px;">
    <h1 style="font-size:1.5rem;font-weight:700;color:#111110;margin:0 0 8px;">Welcome — you're in.</h1>
    <p style="color:#6b7280;font-size:0.9rem;margin:0 0 32px;">
      Your <strong style="color:#111110;">{plan_label} plan ({plan_price})</strong> is active.
      Here's everything you need to get set up.
    </p>

    <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:20px 24px;margin-bottom:32px;">
      <p style="margin:0;font-size:0.85rem;color:#92400e;line-height:1.6;">
        <strong>Step 1 — Create your account.</strong><br>
        Start here. Your dashboard login is separate from your Stripe receipt.
      </p>
      <a href="{register_url}" style="display:inline-block;margin-top:16px;background:#F59E0B;color:#111110;font-weight:700;font-size:0.85rem;padding:12px 28px;border-radius:40px;text-decoration:none;">
        Create my CostWindow account →
      </a>
    </div>

    <h2 style="font-size:1rem;font-weight:700;color:#111110;margin:0 0 16px;">Getting set up</h2>

    <p style="font-size:0.85rem;color:#374151;margin:0 0 6px;"><strong>Step 2 — Get your API key.</strong></p>
    <p style="font-size:0.85rem;color:#6b7280;margin:0 0 20px;line-height:1.6;">
      After you log in, go to <strong>Settings</strong> and generate your CostWindow API key. You'll need it for the next steps.
    </p>

    <p style="font-size:0.85rem;color:#374151;margin:0 0 6px;"><strong>Step 3 — Point your AI client at CostWindow.</strong></p>
    <p style="font-size:0.85rem;color:#6b7280;margin:0 0 12px;line-height:1.6;">
      No SDK, no code changes. Change one line — your client's base URL — and every
      call is tracked, with a hard kill switch in front of it. Your provider API key
      passes straight through and is never stored.
    </p>
    <div style="background:#111110;border-radius:8px;padding:14px 18px;margin-bottom:8px;line-height:1.8;">
      <code style="font-family:'Space Mono',monospace;font-size:0.78rem;color:#9ca3af;white-space:pre;"># Anthropic (Python)
client = anthropic.Anthropic(
    base_url="{api_base}/proxy/anthropic/cw_live_your_key",
)

# OpenAI (Python) — note the /v1
client = openai.OpenAI(
    base_url="{api_base}/proxy/openai/cw_live_your_key/v1",
)</code>
    </div>
    <p style="font-size:0.8rem;color:#9ca3af;margin:0 0 24px;line-height:1.6;">
      Same idea in any language — set the base URL, done. Optional: add a header
      <code style="color:#F59E0B;">X-CostWindow-Label: my-script</code> to name the process.
    </p>

    <p style="font-size:0.85rem;color:#374151;margin:0 0 6px;"><strong>Step 4 (optional) — Track Claude Code sessions.</strong></p>
    <p style="font-size:0.85rem;color:#6b7280;margin:0 0 6px;line-height:1.6;">
      Paste this prompt into Claude Code to set up automatic session cost tracking:
    </p>
    <div style="background:#111110;border-radius:8px;padding:14px 18px;margin-bottom:32px;">
      <code style="font-family:'Space Mono',monospace;font-size:0.78rem;color:#9ca3af;line-height:1.6;">Set up a CostWindow Stop hook. My API key is cw_live_... and my backend URL is {api_base}</code>
    </div>

    <div style="border-top:1px solid #e5e7eb;padding-top:24px;margin-top:8px;">
      <p style="font-size:0.8rem;color:#9ca3af;margin:0;line-height:1.6;">
        Questions? Reply to this email.<br>
        — the owner, myAIcraft
      </p>
    </div>
  </div>
</div>
</body>
</html>"""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                "https://api.mailersend.com/v1/email",
                headers={
                    "Authorization": f"Bearer {settings.mailersend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": {
                        "email": settings.mailersend_from_email,
                        "name": settings.mailersend_from_name,
                    },
                    "to": [{"email": email}],
                    "subject": "Welcome to CostWindow — here's how to get set up",
                    "html": html,
                },
            )
            if not res.is_success:
                print(f"[WELCOME EMAIL] Failed for {email}: {res.text}")
            else:
                print(f"[WELCOME EMAIL] Sent to {email} ({plan})")
    except Exception as e:
        print(f"[WELCOME EMAIL] Error for {email}: {e}")


async def _handle_new_subscription(session: dict) -> None:
    settings = get_settings()
    db = get_db()

    email = (session.get("customer_details") or {}).get("email") or session.get("customer_email")
    stripe_customer_id = session.get("customer")
    stripe_subscription_id = session.get("subscription")

    if not email or not stripe_customer_id or not stripe_subscription_id:
        print(f"[WEBHOOK] Missing fields on checkout session: {session.get('id')}")
        return

    # Resolve plan from the subscription's price.
    # Requires STRIPE_SECRET_KEY (sk_live_...) — the webhook signing secret
    # cannot authenticate to the Stripe API. Falls back to "monthly" if unset.
    res = None
    if settings.stripe_secret_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"https://api.stripe.com/v1/subscriptions/{stripe_subscription_id}",
                    headers={"Authorization": f"Bearer {settings.stripe_secret_key}"},
                )
        except Exception:
            res = None
    else:
        print("[WEBHOOK] STRIPE_SECRET_KEY not set — cannot resolve plan, defaulting to monthly")

    price_id = ""
    if res and res.is_success:
        sub_data = res.json()
        price_id = sub_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id", "")

    plan = _resolve_plan(price_id)

    db.table("customers").upsert({
        "email": email.lower().strip(),
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": stripe_subscription_id,
        "plan": plan,
        "status": "active",
    }, on_conflict="email").execute()

    print(f"[WEBHOOK] New subscriber: {email} ({plan})")
    await _send_welcome_email(email, plan)


def _handle_subscription_status(subscription: dict, status: str) -> None:
    db = get_db()
    stripe_customer_id = subscription.get("customer")
    if stripe_customer_id:
        db.table("customers").update({"status": status}).eq("stripe_customer_id", stripe_customer_id).execute()
        print(f"[WEBHOOK] Subscription {status} for customer: {stripe_customer_id}")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Fail closed: a missing secret means we cannot verify the caller is Stripe,
    # so we must not act on the event (previously this silently accepted
    # unsigned events — anyone could forge a subscription).
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    if not _verify_stripe_signature(payload, sig_header, settings.stripe_webhook_secret):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        event = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        if obj.get("mode") == "subscription":
            await _handle_new_subscription(obj)

    elif event_type in ("customer.subscription.updated",):
        status_map = {"active": "active", "past_due": "past_due", "paused": "paused"}
        mapped = status_map.get(obj.get("status", ""), obj.get("status", ""))
        _handle_subscription_status(obj, mapped)

    elif event_type == "customer.subscription.deleted":
        _handle_subscription_status(obj, "cancelled")

    return {"received": True}
