from __future__ import annotations

import logging

import anthropic

from .config import settings
from .models import ScoredItem

log = logging.getLogger(__name__)

# The competitor-gap pre-pass. Before synthesis writes anything, it asks: for
# this week's top signals, what is the *predictable* take every other AI
# newsletter / LinkedIn-bro will post — and what is the differentiated angle
# almost nobody will cover? Synthesis is then told to avoid the saturated take
# and lean into the gap.
#
# This is the answer to a pain point users don't know they have: they're
# shipping commodity opinions into a feed already saturated with them. Velocity
# scoring tells you *what's* rising; the gap pass tells you *how to say it*
# differently enough to be worth reading.


def find_gaps(signals: list[ScoredItem], top_n: int = 8) -> str:
    """
    Return a markdown 'saturation map': for the top signals, the obvious take to
    avoid and the underexplored angle to take. Empty string on failure (synthesis
    proceeds without it rather than breaking).
    """
    if not signals:
        return ""
    top = signals[:top_n]
    signal_lines = "\n".join(
        f"- [{s.item.source.value}] {s.item.title}" for s in top
    )
    prompt = f"""You are a contrarian content strategist for this audience: {settings.NICHE}.

This week's top signals:
{signal_lines}

For the 3-4 most postable themes here, map the saturation:
- THE SATURATED TAKE: the obvious angle every AI newsletter and LinkedIn poster
  will run this week. The thing readers have already seen ten times.
- THE GAP: a specific, defensible, underexplored angle on the same theme that a
  builder who actually ships would find genuinely useful — a second-order
  implication, a cost/latency/deployment consequence, a counter-intuitive read.

Be concrete and brief. This is internal strategy notes, not prose.

Return markdown:
## Saturation map
### [theme]
- Saturated: ...
- Gap: ...
"""
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        r = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in r.content if getattr(b, "type", None) == "text").strip()
        log.info("competitor gap pass: %d chars of saturation map", len(text))
        return text
    except Exception as exc:
        log.warning("competitor gap pass failed (non-fatal): %s", exc)
        return ""
