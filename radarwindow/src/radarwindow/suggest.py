"""Source suggester — given a plain-English niche, propose the sources
RadarWindow should watch for it (subreddits, GitHub topics, web-search
queries). This is the "RadarWindow guides you to enough sources" piece of the
original vision: a founder types their niche, we fill in where their world
actually talks.

Non-tech niches are expected — a florist has subreddits and web queries but no
meaningful GitHub topics, and that's fine (we return an empty list, not junk).
"""

from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5"  # cheap + fast; this is a simple structured task

_PROMPT = """You configure RadarWindow, a tool that watches a founder's niche for what's \
moving each week. Given their niche, suggest the best sources to track it.

NICHE: {niche}

Return ONLY a JSON object with these keys:
- "subreddits": 4-8 real subreddit names (no "r/" prefix) where this niche's people actually gather. Only real, active subreddits.
- "github_topics": 0-6 GitHub topic tags relevant to this niche. Use [] if the niche is not technical (e.g. floristry, coaching, hospitality) — do NOT invent tech topics for non-tech niches.
- "web_queries": 3-5 short web-search queries that would surface this week's news and trends for this niche. Phrase them like a person searching, e.g. "indie coffee roaster trends" or "small law firm marketing news".

Be specific to the niche. If the niche is broad, pick the most active, on-topic sources. Return only the JSON, no prose."""


def _client():
    # Reuse the synthesis client (routes through the CostWindow proxy when
    # configured, so this call is tracked + kill-switchable like everything else).
    from .synthesis import _client as synth_client
    return synth_client()


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def _clean_list(val, limit: int) -> list[str]:
    if not isinstance(val, list):
        return []
    out = []
    for v in val:
        s = str(v).strip()
        # Strip a leading "r/" or "#" PREFIX (not stray chars — lstrip('r/')
        # would eat the 'r' in "roasting").
        if s.startswith("r/"):
            s = s[2:]
        elif s.startswith("#"):
            s = s[1:]
        s = s.strip()
        if s and s not in out:
            out.append(s)
    return out[:limit]


def suggest_sources(niche: str) -> dict:
    """Return {'subreddits': [...], 'github_topics': [...], 'web_queries': [...]}
    for the given niche. Raises ValueError if the niche is empty; on an LLM/parse
    failure returns empty lists so the caller can degrade gracefully."""
    niche = (niche or "").strip()
    if not niche:
        raise ValueError("niche is required")

    try:
        client = _client()
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": _PROMPT.format(niche=niche)}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        data = _extract_json(text)
    except Exception as exc:  # never 500 the settings page over this
        log.warning("suggest_sources failed for %r: %s", niche, exc)
        return {"subreddits": [], "github_topics": [], "web_queries": []}

    return {
        "subreddits":    _clean_list(data.get("subreddits"), 8),
        "github_topics": _clean_list(data.get("github_topics"), 6),
        "web_queries":   _clean_list(data.get("web_queries"), 5),
    }
