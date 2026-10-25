"""Image-prompt construction (2026-07-21) — concrete, story-grounded, no radar.

The LLM concept step (_image_concept) hits the network, so it's monkeypatched;
these test the prompt assembly around it.
"""

from radarwindow import media as M
from radarwindow.models import Item, ScoredItem, SourceName


def _signal(title: str) -> ScoredItem:
    return ScoredItem(
        item=Item(source=SourceName.WEBSEARCH, title=title, url="http://x", raw_score=1.0),
        volume_score=0.5, velocity_score=0.5, combined_score=0.5,
    )


def test_prompt_uses_llm_concept(monkeypatch):
    monkeypatch.setattr(M, "_image_concept", lambda t, s: "A giant coin sliced clean in half on a desk.")
    p = M._image_prompt(_signal("Anthropic cut input pricing 40%"), "prices dropped this week")
    assert "A giant coin sliced clean in half" in p          # concept is the lead of the prompt
    assert "Visual metaphor:" not in p                        # old radar-metaphor template gone
    assert "Abstract editorial illustration evoking" not in p # old abstract template gone
    assert "avoid" in p.lower()                               # still constrains the model


def test_prompt_falls_back_to_title(monkeypatch):
    monkeypatch.setattr(M, "_image_concept", lambda t, s: "")  # LLM failed / empty
    p = M._image_prompt(_signal("Sonnet 5 ships as the Claude Code default"), "")
    assert "Sonnet 5 ships as the Claude Code default" in p    # title-grounded fallback
    assert "recognisable" in p.lower()


def test_avoid_list_bans_radar_and_abstract():
    # The banned list must explicitly steer away from the exact failure the owner flagged.
    from radarwindow.config import settings
    avoid = settings.VISUAL_AVOID.lower()
    assert "radar" in avoid and "abstract" in avoid
