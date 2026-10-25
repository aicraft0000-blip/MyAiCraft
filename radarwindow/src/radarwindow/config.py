from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core secrets — all required; Railway injects these per-service
    ANTHROPIC_API_KEY: str
    BLOTATO_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    # Blotato account ids (the owner's connected accounts; env-overridable)
    BLOTATO_TWITTER_ACCOUNT_ID: str = ""   # set in your environment
    BLOTATO_LINKEDIN_ACCOUNT_ID: str = ""   # set in your environment
    BLOTATO_INSTAGRAM_ACCOUNT_ID: str = ""   # set in your environment

    MAILERSEND_API_KEY: str = ""
    MAILERSEND_FROM_EMAIL: str = "hello@example.com"
    FAL_API_KEY: str = ""
    RADARWINDOW_USER_ID: str = ""

    # Reddit app-only OAuth (optional). When both are set, the Reddit source
    # uses the authenticated API (full scores + comment counts, no rate-limit
    # pain). When absent, it falls back to the public RSS feed. Create a
    # "script" app at https://www.reddit.com/prefs/apps to get these.
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""

    # Notification
    NOTIFY_EMAIL: str = "you@example.com"

    # Anthropic model
    ANTHROPIC_MODEL: str = "claude-opus-4-8"
    # Cheap model for the niche-relevance gate and the self-QA drift check —
    # both are classify-titles jobs, so the small tier is plenty.
    RELEVANCE_MODEL: str = "claude-haiku-4-5-20251001"

    # CostWindow drop-in proxy (dogfooding the flagship). When set, all
    # synthesis calls route through CostWindow: usage is tracked per-process
    # and a killed/budget-blocked process is refused BEFORE Anthropic is
    # called. Full base URL including the cw_live key, e.g.
    # https://your-backend.up.railway.app/proxy/anthropic/<cw_live_key>
    # Unset = direct Anthropic (untracked).
    COSTWINDOW_PROXY_URL: str = ""
    COSTWINDOW_PROCESS_LABEL: str = "radarwindow-synthesis"
    COSTWINDOW_LEADS_LABEL: str = "radarwindow-leads"

    # Lead-finder (draft-and-queue). Scans public posts for problem-intent, has
    # an LLM honestly qualify which fit a product, drafts a helpful reply, and
    # queues them for MANUAL review. Never auto-sends. Owner-only (the owner's products).
    LEADS_PRODUCTS: str = "costwindow,radarwindow"  # which products to hunt for
    # Subreddits where AI-cost blowups actually get posted — dev/agent-heavy
    # subs where someone woke up to a bill, plus the founder subs where the
    # "how do I cap this" question lands.
    LEADS_SUBREDDITS: str = (
        "LocalLLaMA,LangChain,AI_Agents,artificial,OpenAI,OpenAIDev,ClaudeAI,"
        "ChatGPTCoding,cursor,AutoGPT,LLMDevs,SaaS,indiehackers,SideProject"
    )
    # Cost-horror-story hunt. These are the words people actually use in the
    # moment they get burned — a bill shock, a runaway agent, a loop that ran
    # all night — plus the "how do I cap this" searches that follow. This is
    # CostWindow's exact pain, voiced by the customer. (RadarWindow's own
    # content-pipeline leads still surface incidentally via web/HN search; the
    # query list is deliberately cost-weighted per the owner's focus.)
    LEADS_QUERIES: str = (
        "woke up to a huge API bill,unexpected openai bill,anthropic bill shock,"
        "agent stuck in a loop cost,runaway LLM costs,accidentally spent thousands on API,"
        "infinite loop API calls bill,token usage exploded,claude api costs out of control,"
        "gpt bill hundreds of dollars,cursor usage blew through,api key leaked huge bill,"
        "hard spend limit openai,cap costs on autonomous agent,kill switch AI agent,"
        "how to limit LLM spend,control AI agent spend,budget alert came too late"
    )
    LEADS_PER_QUERY: int = 12         # results pulled per query per source
    LEADS_CANDIDATE_CAP: int = 60     # max candidates sent to the classifier (cost guard)
    LEADS_FIT_THRESHOLD: float = 0.6  # minimum honest fit score to queue a lead
    LEADS_MAX_DRAFTS: int = 8         # max replies drafted per run (cost guard)

    # Quality gate
    QUALITY_SCORE_THRESHOLD: float = 0.75
    MAX_REVISION_ATTEMPTS: int = 2

    # Radar source config — comma-separated lists
    REDDIT_SUBREDDITS: str = "artificial,MachineLearning,LocalLLaMA,SideProject,indiehackers"
    HN_MIN_SCORE: int = 50
    GITHUB_TOPICS: str = "llm,anthropic,claude,mcp,ai-agents"
    WEB_SEARCH_QUERIES: str = "AI tools builders week,SaaS operator AI news,LLM pricing update"

    # Niche voice profile (AICraft)
    NICHE: str = "AI tools, independent builders, SaaS operators"
    NICHE_AVOID_WORDS: str = "transformative,game-changing,revolutionary,unlock,empower,leverage"

    # Visual style profile — governs generated image aesthetic. Images depict a
    # CONCRETE, recognisable subject drawn from the specific story (an LLM writes
    # the concept per brief), rendered in a cohesive AI-centric editorial style.
    # NOT abstract, NOT radar-themed — the reader should grasp the image at a glance.
    VISUAL_AESTHETIC: str = (
        "modern editorial tech illustration — one clear focal subject, clean and "
        "dimensional, confident cinematic lighting, premium magazine-cover quality"
    )
    VISUAL_PALETTE: str = "deep navy base with signal-green and warm white accents"
    # The visual WORLD the concept should live in (AI-centric, but broad — the LLM
    # picks the specific subject that fits each story).
    VISUAL_WORLD: str = (
        "artificial intelligence and software — chips, code, data, robots, agents, "
        "screens, automation, the concrete thing the story is actually about"
    )
    VISUAL_AVOID: str = (
        "abstract patterns, radar or sonar imagery, generic swirls, unidentifiable "
        "shapes, plain gradient backgrounds, stock-photo people at laptops, corporate "
        "clip-art, any text, words or numbers"
    )
    FAL_IMAGE_MODEL: str = "fal-ai/flux/dev"      # fal.ai endpoint slug
    FAL_AUDIO_MODEL: str = "fal-ai/stable-audio"  # fal.ai text-to-music (replaces Mubert — pennies per track)
    # Supabase Storage bucket for hosting generated media (public URLs for kit + Blotato)
    MEDIA_BUCKET: str = "rw-media"

    # Media output directory (Railway volume mount)
    MEDIA_DIR: str = "/data/media"

    @model_validator(mode="after")
    def _check_required(self) -> "Settings":
        required = [
            "ANTHROPIC_API_KEY",
            "BLOTATO_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "RADARWINDOW_USER_ID",
        ]
        missing = [k for k in required if not getattr(self, k)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        return self

    @property
    def reddit_subreddits_list(self) -> list[str]:
        return [s.strip() for s in self.REDDIT_SUBREDDITS.split(",") if s.strip()]

    @property
    def github_topics_list(self) -> list[str]:
        return [t.strip() for t in self.GITHUB_TOPICS.split(",") if t.strip()]

    @property
    def web_search_queries_list(self) -> list[str]:
        return [q.strip() for q in self.WEB_SEARCH_QUERIES.split(",") if q.strip()]

    @property
    def niche_avoid_words_list(self) -> list[str]:
        return [w.strip() for w in self.NICHE_AVOID_WORDS.split(",") if w.strip()]

    @property
    def lead_subreddits_list(self) -> list[str]:
        return [s.strip() for s in self.LEADS_SUBREDDITS.split(",") if s.strip()]

    @property
    def lead_queries_list(self) -> list[str]:
        return [q.strip() for q in self.LEADS_QUERIES.split(",") if q.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience alias — only resolves env vars on first attribute access
class _SettingsProxy:
    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings: Settings = _SettingsProxy()  # type: ignore[assignment]
