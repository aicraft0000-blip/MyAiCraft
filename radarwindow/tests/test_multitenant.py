"""Per-user pipeline + source suggester (2026-07-09)."""

from radarwindow import main as m
from radarwindow.config import settings
from radarwindow.suggest import _clean_list, _extract_json
from radarwindow.actions import make_brief_link, verify_action


# --- _csv fallback ---

def test_csv_uses_value_when_present():
    assert m._csv("a, b ,c", ["x"]) == ["a", "b", "c"]


def test_csv_falls_back_when_empty():
    assert m._csv("", ["x", "y"]) == ["x", "y"]
    assert m._csv(None, ["x"]) == ["x"]


# --- _niche_configs backward-compat + multi-niche ---

def test_niche_configs_empty_falls_back_to_global(monkeypatch):
    class FakeStore:
        def all_active_niches(self): return []
    monkeypatch.setattr(m, "Store", lambda: FakeStore())
    cfgs = m._niche_configs()
    assert len(cfgs) == 1
    assert cfgs[0]["user_id"] == settings.RADARWINDOW_USER_ID
    assert cfgs[0]["niche_id"] is None                  # None only on global fallback
    assert cfgs[0]["niche"] == settings.NICHE
    assert cfgs[0]["subreddits"] == settings.reddit_subreddits_list


def test_niche_configs_row_empty_fields_mean_off(monkeypatch):
    """A saved niche's empty source fields are OFF — inheriting the global AI
    defaults was how unrelated niches drifted (QA, 2026-08-23)."""
    class FakeStore:
        def all_active_niches(self):
            return [{"id": "n1", "user_id": "u1", "label": "Event Horizon",
                     "niche": "", "subreddits": None, "notify_email": ""}]
    monkeypatch.setattr(m, "Store", lambda: FakeStore())
    cfg = m._niche_configs()[0]
    assert cfg["niche_id"] == "n1"
    assert cfg["user_id"] == "u1"
    assert cfg["niche"] == "Event Horizon"              # empty → the label, never global
    assert cfg["subreddits"] == []                      # None → off, never global defaults
    assert cfg["notify_email"] == settings.NOTIFY_EMAIL # delivery may fall back (not content)


def test_niche_configs_custom_niche_and_sources(monkeypatch):
    class FakeStore:
        def all_active_niches(self):
            return [{"id": "n2", "user_id": "u2", "label": "Bakeries", "niche": "artisan bakeries",
                     "subreddits": "Breadit,Baking", "github_topics": "",
                     "web_queries": "sourdough trends", "notify_email": "baker@x.com"}]
    monkeypatch.setattr(m, "Store", lambda: FakeStore())
    cfg = m._niche_configs()[0]
    assert cfg["niche_id"] == "n2"
    assert cfg["label"] == "Bakeries"
    assert cfg["niche"] == "artisan bakeries"
    assert cfg["subreddits"] == ["Breadit", "Baking"]
    assert cfg["github_topics"] == []                   # empty → off, never defaults
    assert cfg["web_queries"] == ["sourdough trends"]
    assert cfg["notify_email"] == "baker@x.com"


def test_niche_configs_multiple_niches_one_user(monkeypatch):
    """One account, two niches → two configs, each with its own niche_id."""
    class FakeStore:
        def all_active_niches(self):
            return [
                {"id": "n1", "user_id": "u1", "label": "AI", "niche": "AI tools"},
                {"id": "n2", "user_id": "u1", "label": "Glass", "niche": "vehicle glass"},
            ]
    monkeypatch.setattr(m, "Store", lambda: FakeStore())
    cfgs = m._niche_configs()
    assert [c["niche_id"] for c in cfgs] == ["n1", "n2"]
    assert all(c["user_id"] == "u1" for c in cfgs)
    assert {c["niche"] for c in cfgs} == {"AI tools", "vehicle glass"}


def test_sources_for_uses_config():
    cfg = {"subreddits": ["Breadit"], "github_topics": ["x"], "web_queries": ["q"]}
    srcs = m._sources_for(cfg)
    assert len(srcs) == 5  # reddit, hn, github, polymarket, websearch


# --- make_brief_link carries user_id ---

def test_make_brief_link_embeds_user(monkeypatch):
    monkeypatch.setenv("ACTION_SECRET", "test-secret")
    link = make_brief_link("t", "https://e.com", "reddit", 0.5, 0.4, 0.6, user_id="u9")
    payload = verify_action(link.split("token=", 1)[1])
    assert payload["uid"] == "u9"


def test_make_brief_link_no_user_omits_uid(monkeypatch):
    monkeypatch.setenv("ACTION_SECRET", "test-secret")
    link = make_brief_link("t", "https://e.com", "reddit", 0.5, 0.4, 0.6)
    payload = verify_action(link.split("token=", 1)[1])
    assert "uid" not in payload
    assert "nid" not in payload


def test_make_brief_link_embeds_niche(monkeypatch):
    monkeypatch.setenv("ACTION_SECRET", "test-secret")
    link = make_brief_link("t", "https://e.com", "reddit", 0.5, 0.4, 0.6, user_id="u9", niche_id="n9")
    payload = verify_action(link.split("token=", 1)[1])
    assert payload["uid"] == "u9" and payload["nid"] == "n9"


# --- suggester helpers ---

def test_suggest_clean_list_strips_prefixes():
    assert _clean_list(["r/Breadit", "#baking", "Breadit"], 8) == ["Breadit", "baking"]


def test_suggest_clean_list_keeps_leading_r():
    # regression: lstrip('r/') used to turn 'roasting' into 'oasting'
    assert _clean_list(["r/roasting", "roasting"], 8) == ["roasting"]


def test_suggest_extract_json_from_fence():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
