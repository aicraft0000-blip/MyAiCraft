"""
Email one-click actions — /api/actions/* (worker strips /api).

Flow: the daily digest email carries a signed "Make this a brief" link per
signal; the resulting "brief ready" email carries a signed "Approve & post"
link. Every GET renders a confirm form and the real work happens on POST,
because mail scanners prefetch GET links — a prefetch must never trigger an
LLM run or a publish. Tokens are HMAC-signed with an expiry (radarwindow.actions).

The synthesis run is spawned as a subprocess (same isolation pattern as the
scheduler): a crash can never take the web process down, and the event loop
never blocks on a multi-minute LLM job.
"""

from __future__ import annotations

import html
import logging
import subprocess
import sys

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse

log = logging.getLogger("radarwindow.actions")

router = APIRouter()

# Light double-click guard (per-process, single-operator product).
_used_tokens: set[str] = set()


def _page(title: str, body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>{html.escape(title)} — RadarWindow</title>
<style>
  body{{margin:0;background:#0b1220;color:#e5e7eb;font-family:'IBM Plex Sans',system-ui,sans-serif;
       display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}}
  .card{{max-width:520px;background:#111a2e;border:1px solid #1f2a44;border-radius:10px;padding:32px}}
  h1{{font-size:1.15rem;margin:0 0 12px;color:#f9fafb}}
  p{{line-height:1.6;color:#9ca3af;margin:0 0 12px}}
  strong{{color:#e5e7eb}}
  button{{background:#0f766e;color:#fff;border:none;border-radius:6px;padding:12px 22px;
         font-size:1rem;font-weight:600;cursor:pointer;margin-top:8px}}
  button:hover{{background:#0d655e}}
  .muted{{font-size:12px;color:#6b7280;margin-top:16px}}
  a{{color:#2dd4bf}}
</style></head><body><main class="card">{body}</main></body></html>""",
        status_code=status,
    )


def _expired() -> HTMLResponse:
    return _page(
        "Link expired",
        "<h1>This link has expired or is invalid</h1>"
        "<p>Email action links are signed and time-limited. Use a button from a "
        "more recent email, or head to your <a href='/'>dashboard</a>.</p>",
        status=400,
    )


@router.get("/make-brief")
def make_brief_confirm(token: str = Query(...)):
    from radarwindow.actions import verify_action

    payload = verify_action(token)
    if not payload or payload.get("a") != "mb":
        return _expired()
    return _page(
        "Make this a brief",
        f"<h1>Turn this signal into a brief?</h1>"
        f"<p><strong>{html.escape(payload['t'])}</strong><br>"
        f"{html.escape(payload['s'])} · score {payload.get('cs', 0):.2f}</p>"
        f"<p>RadarWindow will research and write a focused intelligence brief seeded "
        f"from this signal, through the full three-pass quality gate. You'll get an "
        f"email when it's ready to review — nothing is posted.</p>"
        f"<form method='post' action='/api/actions/make-brief'>"
        f"<input type='hidden' name='token' value='{html.escape(token, quote=True)}'>"
        f"<button type='submit'>Generate the brief</button></form>"
        f"<p class='muted'>Usually ready within a few minutes.</p>",
    )


@router.post("/make-brief")
def make_brief_run(token: str = Form(...)):
    from radarwindow.actions import verify_action

    payload = verify_action(token)
    if not payload or payload.get("a") != "mb":
        return _expired()
    if token in _used_tokens:
        return _page(
            "Already running",
            "<h1>That brief is already being written</h1>"
            "<p>You'll get an email the moment it clears the quality gate.</p>",
        )
    _used_tokens.add(token)

    subprocess.Popen(
        [sys.executable, "-m", "radarwindow.main", "--job=signal-brief", "--token", token],
        start_new_session=True,
    )
    log.info("signal-brief subprocess spawned for: %s", payload.get("t", "")[:60])
    return _page(
        "Brief queued",
        f"<h1>On it — the brief is being written</h1>"
        f"<p>Seeded from <strong>{html.escape(payload['t'])}</strong>, running through "
        f"the three-pass quality gate now.</p>"
        f"<p>You'll get an email when it's ready to review. It will also appear as a "
        f"draft in your <a href='/briefs'>Briefs</a> list.</p>",
    )


@router.get("/approve-post")
def approve_confirm(token: str = Query(...)):
    from radarwindow.actions import verify_action

    payload = verify_action(token)
    if not payload or payload.get("a") != "ap":
        return _expired()

    from uuid import UUID

    from radarwindow.store import Store

    brief = Store().get_brief(UUID(payload["b"]))
    if brief is None:
        return _page("Not found", "<h1>Brief not found</h1><p>It may have been deleted.</p>", status=404)
    if brief.status.value == "posted":
        return _page(
            "Already posted",
            "<h1>This brief has already been posted</h1>"
            f"<p>Nothing more to do. See it in your <a href='/briefs/{payload['b']}'>dashboard</a>.</p>",
        )
    return _page(
        "Approve & post",
        f"<h1>Approve this brief and post it now?</h1>"
        f"<p>Quality {brief.quality_score or 0:.0%} · {brief.revision_count} revision"
        f"{'s' if brief.revision_count != 1 else ''} · status {brief.status.value}</p>"
        f"<p>Platform posts go out via your connected accounts, staggered: X first, "
        f"LinkedIn +10 min, Instagram +20 min. If you haven't read it yet: "
        f"<a href='/briefs/{payload['b']}'>read the brief first</a>.</p>"
        f"<form method='post' action='/api/actions/approve-post'>"
        f"<input type='hidden' name='token' value='{html.escape(token, quote=True)}'>"
        f"<button type='submit'>Approve &amp; post</button></form>",
    )


@router.post("/approve-post")
async def approve_run(token: str = Form(...)):
    from radarwindow.actions import verify_action

    payload = verify_action(token)
    if not payload or payload.get("a") != "ap":
        return _expired()

    from radarwindow.main import approve_and_publish

    try:
        scheduled = await approve_and_publish(payload["b"])
    except ValueError:
        return _page("Not found", "<h1>Brief not found</h1>", status=404)
    except Exception as exc:  # publish problems must surface, not 500 blankly
        log.error("approve-and-publish failed: %s", exc)
        return _page(
            "Something went wrong",
            "<h1>Approved, but posting hit a problem</h1>"
            "<p>The brief is marked approved; the Monday publish run will retry "
            "anything that didn't go out. Details are in the service logs.</p>",
            status=502,
        )

    if scheduled == 0:
        return _page(
            "Nothing to post",
            "<h1>Approved — but no posts were scheduled</h1>"
            "<p>Either they already went out, or every platform post failed to "
            "schedule (in which case the brief stays approved and the Monday "
            "publish run retries).</p>",
        )
    return _page(
        "Posted",
        f"<h1>Approved — {scheduled} post{'s' if scheduled != 1 else ''} scheduled</h1>"
        f"<p>X goes first, LinkedIn about 10 minutes later, Instagram about 20. "
        f"Track it in your <a href='/briefs/{payload['b']}'>dashboard</a>.</p>",
    )
