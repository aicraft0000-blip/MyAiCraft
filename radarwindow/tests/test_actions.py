import os
import time

import pytest

os.environ.setdefault("ACTION_SECRET", "test-secret-for-actions")

from radarwindow.actions import (  # noqa: E402
    approve_link,
    make_brief_link,
    sign_action,
    verify_action,
)


def test_sign_verify_roundtrip():
    payload = {"a": "mb", "t": "Some signal", "u": "https://example.com/x", "s": "hackernews"}
    token = sign_action(payload, exp_hours=1)
    out = verify_action(token)
    assert out is not None
    assert out["t"] == "Some signal"
    assert out["a"] == "mb"
    assert out["exp"] > time.time()


def test_tampered_token_rejected():
    token = sign_action({"a": "ap", "b": "abc"}, exp_hours=1)
    blob, mac = token.split(".")
    assert verify_action(blob + "x." + mac) is None
    assert verify_action(blob + "." + mac[:-2] + "zz") is None


def test_expired_token_rejected():
    token = sign_action({"a": "mb"}, exp_hours=-1)
    assert verify_action(token) is None


def test_garbage_token_rejected():
    assert verify_action("") is None
    assert verify_action("not-a-token") is None
    assert verify_action("a.b.c") is None


def test_make_brief_link_carries_signal():
    link = make_brief_link("Title here", "https://example.com/s", "github", 0.91, 0.8, 0.95)
    assert link.startswith("http")
    assert "/api/actions/make-brief?token=" in link
    token = link.split("token=", 1)[1]
    payload = verify_action(token)
    assert payload["a"] == "mb"
    assert payload["u"] == "https://example.com/s"
    assert payload["cs"] == 0.91


def test_approve_link_carries_brief_id():
    link = approve_link("11111111-2222-3333-4444-555555555555")
    assert "/api/actions/approve-post?token=" in link
    payload = verify_action(link.split("token=", 1)[1])
    assert payload == pytest.approx(payload)  # sanity
    assert payload["a"] == "ap"
    assert payload["b"] == "11111111-2222-3333-4444-555555555555"
