"""Lead-finder: pure helpers + orchestration wiring (2026-07-14).

No network: the LLM client and candidate gathering are monkeypatched, so these
test the logic around the model calls — dedupe, threshold, caps, email render —
not the model output itself.
"""

import asyncio

from radarwindow import leads as L
from radarwindow.config import settings
from radarwindow.models import Lead, LeadStatus, SourceName


# --- a minimal fake Anthropic client -------------------------------------

class _Block:
    def __init__(self, text): self.text = text

class _Resp:
    def __init__(self, text): self.content = [_Block(text)]

class FakeMessages:
    def __init__(self, text): self._text = text
    def create(self, **kw): return _Resp(self._text)

class FakeClient:
    def __init__(self, text): self.messages = FakeMessages(text)


# --- render_leads_email ---------------------------------------------------

def test_email_empty():
    assert "No new leads" in L.render_leads_email([])


def test_email_renders_lead_card():
    lead = Lead(
        source=SourceName.REDDIT, product="costwindow",
        url="https://reddit.com/r/x/comments/1", title="Agent ate my credits",
        excerpt="my agent ran overnight and cost $400", author="someone",
        fit_score=0.82, rationale="hard spend cap is exactly the ask",
        draft_reply="Set a hard cap. I built CostWindow which does that.",
    )
    html = L.render_leads_email([lead])
    assert "https://reddit.com/r/x/comments/1" in html
    assert "CostWindow" in html                    # product name resolved
    assert "you post them yourself" in html.lower()  # manual-send disclaimer
    assert "CostWindow which does that" in html    # the draft is shown


# --- _focus_products ------------------------------------------------------

def test_focus_products_filters(monkeypatch):
    monkeypatch.setattr(settings, "LEADS_PRODUCTS", "costwindow")
    focus = L._focus_products()
    assert set(focus) == {"costwindow"}


def test_focus_products_empty_falls_back_to_all(monkeypatch):
    monkeypatch.setattr(settings, "LEADS_PRODUCTS", "")
    assert set(L._focus_products()) == set(L.PRODUCTS)


# --- _classify parsing ----------------------------------------------------

def test_classify_keeps_valid_drops_invalid():
    candidates = [{"source": "reddit", "title": "a", "body": "b"},
                  {"source": "hackernews", "title": "c", "body": "d"}]
    # index 5 is out of range; product 'nope' unknown; index 0 valid.
    client = FakeClient(
        '[{"index":0,"product":"costwindow","fit_score":0.9,"rationale":"fits"},'
        ' {"index":5,"product":"costwindow","fit_score":0.9,"rationale":"oob"},'
        ' {"index":1,"product":"nope","fit_score":0.9,"rationale":"bad product"}]'
    )
    out = L._classify(client, candidates, L.PRODUCTS)
    assert len(out) == 1
    assert out[0]["index"] == 0 and out[0]["product"] == "costwindow"


def test_classify_handles_non_json():
    out = L._classify(FakeClient("no json here"), [{"source": "reddit"}], L.PRODUCTS)
    assert out == []


# --- find_leads orchestration --------------------------------------------

def _run(coro):
    return asyncio.run(coro)


def test_find_leads_dedupes_and_applies_threshold(monkeypatch):
    cands = [
        {"source": "reddit", "title": "t0", "url": "u0", "body": "burned my budget"},
        {"source": "reddit", "title": "t0dup", "url": "u0", "body": "dup url dropped"},
        {"source": "hackernews", "title": "t1", "url": "u1", "body": "spend cap please"},
        {"source": "websearch", "title": "t2", "url": "u2", "body": "low fit"},
    ]

    async def fake_gather(cfg): return cands
    monkeypatch.setattr(L, "_gather_candidates", fake_gather)
    monkeypatch.setattr(L, "_llm_client", lambda: FakeClient("[]"))
    # u0 fits high, u1 fits below threshold, u2 not returned at all.
    monkeypatch.setattr(L, "_classify", lambda c, cands_, p: [
        {"index": 0, "product": "costwindow", "fit_score": 0.9, "rationale": "strong"},
        {"index": 2, "product": "costwindow", "fit_score": 0.3, "rationale": "weak"},
    ])
    monkeypatch.setattr(L, "_draft", lambda c, cand, prod: "helpful reply")
    monkeypatch.setattr(settings, "LEADS_FIT_THRESHOLD", 0.6)

    out = _run(L.find_leads({"lead_subreddits": [], "lead_queries": []}))
    assert len(out) == 1                      # only the >=0.6 lead survives
    assert out[0].url == "u0"
    assert out[0].status == LeadStatus.PENDING
    assert out[0].draft_reply == "helpful reply"


def test_find_leads_skips_already_queued(monkeypatch):
    cands = [{"source": "reddit", "title": "t0", "url": "u0", "body": "burned my budget"}]

    async def fake_gather(cfg): return cands
    monkeypatch.setattr(L, "_gather_candidates", fake_gather)
    monkeypatch.setattr(L, "_llm_client", lambda: FakeClient("[]"))
    monkeypatch.setattr(L, "_classify", lambda c, cands_, p: [
        {"index": 0, "product": "costwindow", "fit_score": 0.9, "rationale": "x"}])
    monkeypatch.setattr(L, "_draft", lambda c, cand, prod: "reply")

    out = _run(L.find_leads({"lead_subreddits": [], "lead_queries": []}, skip_urls={"u0"}))
    assert out == []                          # already queued → skipped before classify


def test_find_leads_respects_max_drafts(monkeypatch):
    cands = [{"source": "reddit", "title": f"t{i}", "url": f"u{i}", "body": "cap my spend"}
             for i in range(10)]

    async def fake_gather(cfg): return cands
    monkeypatch.setattr(L, "_gather_candidates", fake_gather)
    monkeypatch.setattr(L, "_llm_client", lambda: FakeClient("[]"))
    monkeypatch.setattr(L, "_classify", lambda c, cands_, p: [
        {"index": i, "product": "costwindow", "fit_score": 0.7, "rationale": "x"}
        for i in range(10)])
    monkeypatch.setattr(L, "_draft", lambda c, cand, prod: "reply")
    monkeypatch.setattr(settings, "LEADS_MAX_DRAFTS", 3)

    out = _run(L.find_leads({"lead_subreddits": [], "lead_queries": []}))
    assert len(out) == 3
