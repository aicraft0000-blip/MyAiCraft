"""Tests for the media-kit assembler — RadarWindow's core deliverable. If this
breaks, the product's main value (the downloadable kit) breaks."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mediakit import build_media_kit  # noqa: E402

_BRIEF = {
    "id": "abc-123",
    "run_date": "2026-06-26T07:30:00+00:00",
    "content_md": "# Headline\n\n- point one\n\n**So what:** ship faster.",
    "signal_mood": "rising",
    "status": "draft",
    "quality_score": 0.82,
    "revision_count": 0,
    "niche_voice_passed": True,
}
_POSTS = [
    {"platform": "x", "content": "X thread here", "image_public_url": None},
    {"platform": "linkedin", "content": "LinkedIn post", "image_public_url": None},
    {"platform": "instagram", "content": "IG caption 🚀", "image_public_url": None},
]
_SIGNALS = [
    {"source": "hackernews", "title": "HN top", "combined_score": 0.9},
    {"source": "github", "title": "repo", "combined_score": 0.7},
    {"source": "github", "title": "repo2", "combined_score": 0.5},
]


def _open():
    fname, data = build_media_kit(_BRIEF, _POSTS, _SIGNALS)
    return fname, zipfile.ZipFile(io.BytesIO(data))


def test_filename_uses_run_date():
    fname, _ = _open()
    assert fname == "radarwindow-brief-2026-06-26.zip"


def test_kit_contains_core_files():
    _, zf = _open()
    names = "\n".join(zf.namelist())
    for expected in ("README.md", "brief.md", "brief.json", "source-health.md",
                     "signals.json", "x-post.md", "linkedin-post.md", "instagram-post.md"):
        assert expected in names, f"missing {expected}"


def test_brief_md_content_preserved():
    _, zf = _open()
    root = zf.namelist()[0].split("/")[0]
    assert "Headline" in zf.read(f"{root}/brief.md").decode()


def test_source_health_counts_correct():
    _, zf = _open()
    root = zf.namelist()[0].split("/")[0]
    health = zf.read(f"{root}/source-health.md").decode()
    assert "| github | 2 |" in health
    assert "| hackernews | 1 |" in health
    assert "| reddit | 0 |" in health  # absent source shown as 0


def test_brief_json_valid():
    _, zf = _open()
    root = zf.namelist()[0].split("/")[0]
    data = json.loads(zf.read(f"{root}/brief.json"))
    assert data["quality_score"] == 0.82
    assert len(data["posts"]) == 3
