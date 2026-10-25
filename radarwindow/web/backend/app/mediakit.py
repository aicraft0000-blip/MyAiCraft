"""
Media-kit assembler — RadarWindow's core download-first deliverable.

Turns a stored brief (+ its posts + scored signals + optional generated media)
into a single ZIP the user downloads and posts from. No OAuth, no posting layer
required to get the value: the kit IS the product.

Layout produced:

    radarwindow-brief-YYYY-MM-DD/
    ├── README.md             ← what's in here + how to use it
    ├── brief.md              ← the intelligence brief (shareable)
    ├── brief.json            ← structured brief data
    ├── x-post.md             ← X / Twitter draft
    ├── linkedin-post.md      ← LinkedIn draft
    ├── instagram-post.md     ← Instagram caption
    ├── source-health.md      ← which sources were live + signal counts
    ├── signals.json          ← raw scored signals behind the brief
    └── media/                ← images / audio / reel when generated
"""
from __future__ import annotations

import io
import json
import zipfile
from collections import Counter
from datetime import datetime

import httpx

_PLATFORM_FILES = {
    "x": "x-post.md",
    "linkedin": "linkedin-post.md",
    "instagram": "instagram-post.md",
}
_PLATFORM_TITLE = {"x": "X / Twitter", "linkedin": "LinkedIn", "instagram": "Instagram"}


def _kit_date(brief: dict) -> str:
    raw = brief.get("run_date") or brief.get("created_at") or ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime.utcnow().strftime("%Y-%m-%d")


def _source_health_md(signals: list[dict]) -> str:
    counts = Counter(s.get("source", "unknown") for s in signals)
    all_sources = ["reddit", "hackernews", "github", "polymarket", "websearch"]
    lines = [
        "# Source Health",
        "",
        "How many signals each radar source contributed to this brief. A source",
        "showing 0 was unavailable this run — the brief was built from the rest.",
        "",
        "| Source | Signals | Status |",
        "| --- | --- | --- |",
    ]
    for src in all_sources:
        n = counts.get(src, 0)
        status = "live" if n > 0 else "no data this run"
        lines.append(f"| {src} | {n} | {status} |")
    extra = set(counts) - set(all_sources)
    for src in sorted(extra):
        lines.append(f"| {src} | {counts[src]} | live |")
    lines.append("")
    lines.append(f"**Total signals:** {sum(counts.values())}")
    return "\n".join(lines)


def _readme_md(brief: dict, date: str) -> str:
    mood = brief.get("signal_mood", "neutral")
    q = brief.get("quality_score")
    q_str = f"{float(q) * 100:.0f}%" if q is not None else "—"
    return f"""# RadarWindow Media Kit — {date}

Signal mood: **{mood}**  ·  Quality score: **{q_str}**

This kit was assembled by RadarWindow from this week's velocity-scored signals,
written through a three-pass quality gate (generate → critique → revise).

## What's inside
- **brief.md** — the weekly intelligence brief. This is the core asset: a
  standalone analyst memo you can publish as a newsletter or read to decide
  what to post.
- **x-post.md / linkedin-post.md / instagram-post.md** — platform-ready drafts
  derived from the brief. Edit to taste, then post.
- **source-health.md** — which sources fed this brief, so you can trust it.
- **signals.json** — the raw scored signals, if you want to dig in.
- **media/** — generated image / audio / reel, when available.

## How to use it
1. Read brief.md. 2. Pick the platform drafts you want. 3. Edit, attach the
matching media, and post — manually or via your scheduler.

Velocity over volume: these signals are ranked by what's *accelerating*, not
just what's already popular. You're posting about what's rising, not what peaked.
"""


def _brief_json(brief: dict, posts: list[dict], signals: list[dict]) -> str:
    payload = {
        "id": brief.get("id"),
        "run_date": brief.get("run_date"),
        "signal_mood": brief.get("signal_mood"),
        "status": brief.get("status"),
        "quality_score": brief.get("quality_score"),
        "revision_count": brief.get("revision_count"),
        "niche_voice_passed": brief.get("niche_voice_passed"),
        "content_md": brief.get("content_md"),
        "posts": [
            {"platform": p.get("platform"), "content": p.get("content")} for p in posts
        ],
        "signal_count": len(signals),
    }
    return json.dumps(payload, indent=2, default=str)


def _fetch_media(url: str) -> bytes | None:
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def build_media_kit(brief: dict, posts: list[dict], signals: list[dict]) -> tuple[str, bytes]:
    """
    Assemble the media kit ZIP in memory.
    Returns (filename, zip_bytes).
    """
    date = _kit_date(brief)
    root = f"radarwindow-brief-{date}"
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{root}/README.md", _readme_md(brief, date))
        zf.writestr(f"{root}/brief.md", brief.get("content_md", "") or "")
        zf.writestr(f"{root}/brief.json", _brief_json(brief, posts, signals))
        zf.writestr(f"{root}/source-health.md", _source_health_md(signals))
        zf.writestr(
            f"{root}/signals.json",
            json.dumps(signals, indent=2, default=str),
        )

        for post in posts:
            platform = post.get("platform", "")
            fname = _PLATFORM_FILES.get(platform)
            if not fname:
                continue
            title = _PLATFORM_TITLE.get(platform, platform)
            body = f"# {title} post\n\n{post.get('content', '') or ''}\n"
            zf.writestr(f"{root}/{fname}", body)

            # Embed generated media when present.
            img_url = post.get("image_public_url")
            if img_url:
                data = _fetch_media(img_url)
                if data:
                    zf.writestr(f"{root}/media/{platform}-image.jpg", data)

        # Reel + ambient track are shared assets (generated once per brief);
        # embed each once, from whichever post carries the URL.
        video_url = next((p.get("video_public_url") for p in posts if p.get("video_public_url")), None)
        if video_url:
            data = _fetch_media(video_url)
            if data:
                zf.writestr(f"{root}/media/instagram-reel.mp4", data)
        audio_url = next((p.get("audio_public_url") for p in posts if p.get("audio_public_url")), None)
        if audio_url:
            data = _fetch_media(audio_url)
            if data:
                ext = ".wav" if ".wav" in audio_url else ".mp3"
                zf.writestr(f"{root}/media/ambient-track{ext}", data)

    buf.seek(0)
    return f"{root}.zip", buf.getvalue()
