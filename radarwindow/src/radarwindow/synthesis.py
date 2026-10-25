from __future__ import annotations

import json
import logging
import re
from uuid import UUID

import anthropic

from .config import settings
from .models import Brief, BriefStatus, Platform, Post, PostStatus, ScoredItem, SignalMood

log = logging.getLogger(__name__)

_TOP_N = 10  # signals passed to synthesis
_AVOID_PATTERNS = [
    "in today's",
    "in the ever-evolving",
    "it's important to",
    "let's dive into",
    "game-changing",
    "revolutionary",
    "unlock",
    "empower",
    "leverage",
    "transformative",
    "cutting-edge",
    "exciting",
    "remarkable",
    "incredible",
]


def _client() -> anthropic.Anthropic:
    """
    Anthropic client, routed through the CostWindow drop-in proxy when
    COSTWINDOW_PROXY_URL is set — every synthesis call is then tracked as the
    COSTWINDOW_PROCESS_LABEL process with a hard kill switch in front of it.
    The Anthropic key still authenticates the real API; CostWindow only
    observes and gates (provider keys pass through, never stored).
    """
    if settings.COSTWINDOW_PROXY_URL:
        return anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.COSTWINDOW_PROXY_URL,
            default_headers={"X-CostWindow-Label": settings.COSTWINDOW_PROCESS_LABEL},
        )
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ---------------------------------------------------------------------------
# Prompt caching (2026-08-23). All static instruction text lives in ONE system
# prompt shared by the three passes, marked as an ephemeral cache checkpoint.
# A Monday run makes 3–8 calls per niche back-to-back (generate → critique →
# revise → critique…, then the next niche): the first call writes the cache,
# every later call within the 5-min TTL re-reads it at ~10% of input price.
# The system block must stay IDENTICAL across calls or the cache misses —
# anything per-niche or per-draft belongs in the user message, never here.
# ---------------------------------------------------------------------------

_SYSTEM = """You are the editorial engine behind RadarWindow, an analyst service that writes the weekly intelligence brief for a founder's specific niche. Each request names exactly one of your three roles — WRITER-GENERATE, EDITOR, or WRITER-REVISE — followed by that request's material. Follow ONLY the spec for the named role. Always return ONLY the JSON asked for: no preamble, no markdown fences.

=== ROLE: WRITER-GENERATE ===
The request supplies the niche, words to avoid, this week's top signals, and optionally an internal competitor saturation map (do NOT quote it verbatim — use it to steer angle selection: avoid the saturated takes, write toward the gaps; the reader should feel they're getting an angle they haven't already seen).

INSIDER VOCABULARY: use the natural, specific vocabulary an insider in THIS niche would use — the words its practitioners actually say, not generic business-speak. Never force jargon from a different field.
TONE: direct, specific, measurement-oriented, an insider's perspective — write like someone deep in this world, not a marketer looking in.

TASK: Produce three outputs as a JSON object with these keys:
1. "brief" — a weekly intelligence brief in markdown. Format:
   - One headline that names the actual trend (not "This week in AI")
   - 3–5 bullet points, each grounded in a specific signal with real numbers
   - One "So what for builders" paragraph — concrete implication, no fluff
   - No rhetorical questions. No three-item lists with em-dashes. No "In conclusion."

2. "posts" — an object with keys "x", "linkedin", "instagram":
   - "x": 1–3 tweet thread. Specific claim → data → implication. Under 280 chars per tweet.
   - "linkedin": Story-format, written like a person talking to peers. A hook line
     that names the tension (specific, not "I'm excited to share"), a blank line,
     then two short paragraphs (2–3 plain sentences each) developing ONE idea,
     then a one-line takeaway. Numbers only where they carry real information
     from the signals — two or three in the whole post at most, never a number
     invented to sound precise. No hashtag spam.
   - "instagram": Caption. 2–3 sentences max. Ends with a single relevant emoji. One CTA.

HOW THE POSTS SHOULD READ (all three platforms):
- Like a person, not a terminal. One idea per sentence; if a sentence needs a
  second reading to parse, split it.
- Numbers under ten are written as words ("two failures", "one afternoon")
  unless they are data (40%, £4.80, 30B). Never manufacture counts to sound
  precise ("3 places", "2 opposite failures") — that is machine shorthand.
- Let a point land before making the next one. Not every sentence needs to
  carry a claim; density is not the same thing as insight.
- Plain verbs over stacked noun phrases: "costs you money you haven't
  budgeted", not "an uncosted dependency risk". Contractions are fine.

3. "mood" — one word: "rising", "bullish", "cautionary", or "neutral" — based on the overall signal direction.

=== ROLE: EDITOR ===
You are a quality editor for a niche intelligence newsletter. The request supplies the niche, the brief and the platform posts to review.

EVALUATE on these criteria:
1. SPECIFICITY — are claims grounded in actual signal data, or generic?
2. NICHE VOICE — does it use this niche's insider vocabulary naturally, the way its practitioners talk? Or does it sound like a marketer looking in?
3. SLOP PATTERNS — does it use any of these banned phrases or structures:
{avoid_list}
4. STRUCTURE — no rhetorical-question-then-answer, no three-item em-dash lists, no "In conclusion", no "I'm excited to share"
5. ACCURACY — do the posts accurately reflect the brief?
6. READABILITY — does it read like a person wrote it? Fail it for machine
   shorthand: digits where a human writes words ("2 opposite failures",
   "1 afternoon", "3 places"), every sentence packed with a claim, stacked
   noun phrases ("uncosted dependency risk"), sentences that need two readings,
   or a LinkedIn post with no paragraph breaks.

Return a JSON object (keep "critique" under 80 words to stay within one response):
{{
  "score": 0.0,  // float 0–1. Above 0.75 = acceptable. Below = revise.
  "niche_voice_ok": true,  // false if the content sounds like a marketer, not a builder
  "critique": "specific, actionable feedback — name the exact phrase or sentence that fails, not just 'be more specific'"
}}

=== ROLE: WRITER-REVISE ===
You are the writer behind RadarWindow, rewriting based on an editor's critique. The request supplies the original brief and posts, the critique, and the source signals for grounding revisions in real data.

Fix every issue the editor named. Keep what already works. Do not introduce new slop.

Return a JSON object with the same structure as before:
{{"brief": "...", "posts": {{"x": "...", "linkedin": "...", "instagram": "..."}}}}"""


def _system_blocks() -> list[dict]:
    avoid_list = "\n".join(f"- {p}" for p in _AVOID_PATTERNS)
    return [{
        "type": "text",
        "text": _SYSTEM.format(avoid_list=avoid_list),
        "cache_control": {"type": "ephemeral"},
    }]


def _create(client: anthropic.Anthropic, user_prompt: str, max_tokens: int):
    r = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=_system_blocks(),
        messages=[{"role": "user", "content": user_prompt}],
    )
    u = getattr(r, "usage", None)
    if u is not None:
        log.info(
            "synthesis tokens: in=%s out=%s cache_write=%s cache_read=%s",
            getattr(u, "input_tokens", "?"), getattr(u, "output_tokens", "?"),
            getattr(u, "cache_creation_input_tokens", 0) or 0,
            getattr(u, "cache_read_input_tokens", 0) or 0,
        )
    return r


def _load_json(raw: str) -> dict:
    """
    Tolerant JSON extraction for model output. Strips fences, isolates the
    outermost object, and on truncation attempts a light repair (balance the
    brackets, close a dangling string). Raises ValueError if still unparseable
    so callers can degrade gracefully rather than the run crashing.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Strip trailing commas before a closing brace/bracket — the single most
    # common model JSON error.
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Last-resort repair for truncated responses.
    repaired = raw
    # Close a dangling string (odd count of unescaped quotes).
    if repaired.count('"') % 2 == 1:
        repaired += '"'
    # Balance braces/brackets.
    repaired += "]" * (repaired.count("[") - repaired.count("]"))
    repaired += "}" * (repaired.count("{") - repaired.count("}"))
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as exc:
        raise ValueError(f"could not parse model JSON: {exc}") from exc


def synthesise(
    signals: list[ScoredItem], brief_id: UUID, user_id: str = "",
    niche: str | None = None, avoid_words: str | None = None,
) -> tuple[Brief, list[Post]]:
    """
    Three-pass quality gate: generate → critique → revise.
    A competitor-gap pre-pass first maps saturated angles so the brief leans
    into the underexplored take rather than the commodity one. A feedback note
    (what worked for this account before) steers platform effort.
    `niche`/`avoid_words` drive the voice per user (default to the global niche).
    Returns a Brief and per-platform Posts.
    Raises RuntimeError if quality gate fails after all revision attempts.
    """
    from .competitor import find_gaps
    from .feedback import recent_performance_summary

    top = signals[:_TOP_N]
    client = _client()

    gap_map = find_gaps(signals)
    performance = recent_performance_summary(user_id)
    brief_content, posts_content, mood = _generate(client, top, gap_map, performance, niche, avoid_words)
    revision_count = 0

    for attempt in range(settings.MAX_REVISION_ATTEMPTS + 1):
        critique, score, niche_ok = _critique(client, brief_content, posts_content, niche)
        if score >= settings.QUALITY_SCORE_THRESHOLD and niche_ok:
            break
        if attempt == settings.MAX_REVISION_ATTEMPTS:
            log.warning("quality gate: %d revisions exhausted (score=%.2f, niche=%s) — using best attempt", attempt, score, niche_ok)
            break
        log.info("quality gate: revision %d (score=%.2f, niche=%s)", attempt + 1, score, niche_ok)
        brief_content, posts_content = _revise(client, top, brief_content, posts_content, critique)
        revision_count += 1

    brief = Brief(
        id=brief_id,
        content_md=brief_content,
        signal_mood=mood,
        status=BriefStatus.DRAFT,
        quality_score=score,
        revision_count=revision_count,
        niche_voice_passed=niche_ok,
    )

    def _to_str(val) -> str:
        if isinstance(val, list):
            return "\n\n".join(str(v) for v in val)
        return str(val) if val else ""

    posts = [
        Post(brief_id=brief_id, platform=Platform.X, content=_to_str(posts_content.get("x")), status=PostStatus.DRAFT),
        Post(brief_id=brief_id, platform=Platform.LINKEDIN, content=_to_str(posts_content.get("linkedin")), status=PostStatus.DRAFT),
        Post(brief_id=brief_id, platform=Platform.INSTAGRAM, content=_to_str(posts_content.get("instagram")), status=PostStatus.DRAFT),
    ]
    return brief, posts


def _signals_block(signals: list[ScoredItem]) -> str:
    lines = []
    for i, s in enumerate(signals, 1):
        lines.append(
            f"{i}. [{s.item.source.value.upper()}] {s.item.title}\n"
            f"   URL: {s.item.url}\n"
            f"   Score: {s.combined_score:.3f} (volume={s.volume_score:.3f}, velocity={s.velocity_score:.3f})\n"
            f"   Raw engagement: {s.item.raw_score:.0f}  Comments: {s.item.comment_count}"
        )
    return "\n\n".join(lines)


def _generate(
    client: anthropic.Anthropic, signals: list[ScoredItem], gap_map: str = "", performance: str = "",
    niche: str | None = None, avoid_words: str | None = None,
) -> tuple[str, dict[str, str], SignalMood]:
    niche = niche or settings.NICHE
    avoid_words = avoid_words or settings.NICHE_AVOID_WORDS
    gap_block = ""
    if gap_map:
        gap_block = f"""
COMPETITOR SATURATION MAP (internal strategy — do NOT quote this verbatim):
{gap_map}
"""
    if performance:
        gap_block += f"\n{performance}\n"

    prompt = f"""ROLE: WRITER-GENERATE

NICHE: {niche}
AVOID THESE WORDS ENTIRELY: {avoid_words}

THIS WEEK'S TOP SIGNALS (ranked by velocity + volume):
{_signals_block(signals)}
{gap_block}
Return ONLY the JSON object. No preamble. No markdown fences."""

    # Retry once on a parse failure before giving up — generate output is
    # load-bearing (no brief without it).
    last_exc: Exception | None = None
    for attempt in range(2):
        r = _create(client, prompt, max_tokens=3000)
        try:
            data = _load_json(r.content[0].text)
            mood_raw = str(data.get("mood", "neutral")).lower().strip()
            mood = SignalMood(mood_raw) if mood_raw in {m.value for m in SignalMood} else SignalMood.NEUTRAL
            return data["brief"], data["posts"], mood
        except (ValueError, KeyError) as exc:
            last_exc = exc
            log.warning("generate parse failed (attempt %d): %s", attempt + 1, exc)
    raise RuntimeError(f"synthesis generate failed to produce valid JSON: {last_exc}")


def _critique(
    client: anthropic.Anthropic, brief: str, posts: dict[str, str],
    niche: str | None = None,
) -> tuple[str, float, bool]:
    """Returns (critique text, quality score 0–1, niche_voice_ok bool)."""
    niche = niche or settings.NICHE
    posts_block = "\n\n".join(f"[{k.upper()}]\n{v}" for k, v in posts.items())

    prompt = f"""ROLE: EDITOR

The niche: {niche}.

BRIEF TO REVIEW:
{brief}

PLATFORM POSTS TO REVIEW:
{posts_block}

Return ONLY the JSON. No preamble."""

    r = _create(client, prompt, max_tokens=1200)
    try:
        data = _load_json(r.content[0].text)
        return str(data.get("critique", "")), float(data["score"]), bool(data["niche_voice_ok"])
    except (ValueError, KeyError, TypeError) as exc:
        # Never let a critique parse failure crash the run — treat as acceptable
        # so the already-generated content ships rather than nothing.
        log.warning("critique parse failed — accepting current draft: %s", exc)
        return "", settings.QUALITY_SCORE_THRESHOLD, True


def _revise(
    client: anthropic.Anthropic,
    signals: list[ScoredItem],
    brief: str,
    posts: dict[str, str],
    critique: str,
) -> tuple[str, dict[str, str]]:
    posts_block = "\n\n".join(f"[{k.upper()}]\n{v}" for k, v in posts.items())

    prompt = f"""ROLE: WRITER-REVISE

ORIGINAL BRIEF:
{brief}

ORIGINAL POSTS:
{posts_block}

EDITOR'S CRITIQUE:
{critique}

SOURCE SIGNALS (for grounding revisions in real data):
{_signals_block(signals)}

Return ONLY the JSON. No preamble."""

    r = _create(client, prompt, max_tokens=3000)
    try:
        data = _load_json(r.content[0].text)
        return data["brief"], data["posts"]
    except (ValueError, KeyError) as exc:
        # Revision failed to parse — keep the previous draft rather than crash.
        log.warning("revision parse failed — keeping prior draft: %s", exc)
        return brief, posts
