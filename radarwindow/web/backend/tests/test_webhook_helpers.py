import hashlib
import hmac

from app.routers.webhook import plan_from_price_id, verify_stripe_signature

SECRET = "whsec_testsecret"


def _sign(payload: bytes, timestamp: int, secret: str = SECRET) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.{payload.decode()}".encode(), hashlib.sha256)
    return f"t={timestamp},v1={mac.hexdigest()}"


def test_valid_signature_accepted():
    payload = b'{"type":"checkout.session.completed"}'
    header = _sign(payload, 1000)
    assert verify_stripe_signature(payload, header, SECRET, now=1000)


def test_tampered_payload_rejected():
    header = _sign(b'{"a":1}', 1000)
    assert not verify_stripe_signature(b'{"a":2}', header, SECRET, now=1000)


def test_wrong_secret_rejected():
    payload = b"{}"
    header = _sign(payload, 1000, secret="whsec_other")
    assert not verify_stripe_signature(payload, header, SECRET, now=1000)


def test_stale_timestamp_rejected():
    payload = b"{}"
    header = _sign(payload, 1000)
    assert not verify_stripe_signature(payload, header, SECRET, now=1000 + 301)
    assert verify_stripe_signature(payload, header, SECRET, now=1000 + 299)


def test_malformed_header_rejected():
    assert not verify_stripe_signature(b"{}", "garbage", SECRET, now=1000)
    assert not verify_stripe_signature(b"{}", "", SECRET, now=1000)


def test_plan_resolution():
    assert plan_from_price_id("price_pro", "price_std", "price_pro") == "radar_pro"
    assert plan_from_price_id("price_std", "price_std", "price_pro") == "radar"
    # Unknown or missing price ids must never lock someone out of the base plan
    assert plan_from_price_id("price_other", "price_std", "price_pro") == "radar"
    assert plan_from_price_id(None, "price_std", "price_pro") == "radar"
