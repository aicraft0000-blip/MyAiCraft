"""Tests for the public brief page helpers — slug minting, title derivation,
and excerpt extraction. Pure functions, no DB."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.public import derive_title, make_excerpt, make_slug  # noqa: E402

_MD = (
    "# LLM pricing just moved\n\n"
    "## The signal\n\n"
    "- **Anthropic** cut input pricing 40% this week.\n"
    "- What cost £8/M tokens now costs £4.80.\n\n"
    "So what: rerun your unit economics before Monday.\n"
)


def test_slug_is_date_plus_short_id():
    slug = make_slug("2026-06-26T07:30:00+00:00", "abcdef12-3456-7890-abcd-ef1234567890")
    assert slug == "2026-06-26-abcdef12"


def test_title_is_first_heading():
    assert derive_title(_MD, "2026-06-26T07:30:00+00:00") == "LLM pricing just moved"


def test_title_falls_back_to_run_date():
    assert derive_title("no headings here", "2026-06-26T07:30:00+00:00") == "Brief — 2026-06-26"


def test_excerpt_skips_headings_and_strips_markdown():
    excerpt = make_excerpt(_MD)
    assert "LLM pricing just moved" not in excerpt  # heading excluded
    assert excerpt.startswith("Anthropic cut input pricing 40% this week.")
    assert "**" not in excerpt


def test_excerpt_truncates_on_word_boundary():
    long_md = "word " * 100
    excerpt = make_excerpt(long_md, length=50)
    assert len(excerpt) <= 51  # 50 chars + ellipsis
    assert excerpt.endswith("…")
    assert " wor…" not in excerpt  # no mid-word cut
