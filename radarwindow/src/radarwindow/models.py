from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SourceName(str, Enum):
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    GITHUB = "github"
    POLYMARKET = "polymarket"
    WEBSEARCH = "websearch"
    RSS = "rss"


class Platform(str, Enum):
    X = "x"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"


class BriefStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    ARCHIVED = "archived"


class PostStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"


class SignalMood(str, Enum):
    RISING = "rising"
    BULLISH = "bullish"
    CAUTIONARY = "cautionary"
    NEUTRAL = "neutral"


class LeadStatus(str, Enum):
    PENDING = "pending"      # found + drafted, waiting for the owner to review/post
    APPROVED = "approved"    # the owner posted the reply manually — done
    DISMISSED = "dismissed"  # not a real fit, or skipped on review


class Item(BaseModel):
    """Raw item fetched from a single source."""

    id: UUID = Field(default_factory=uuid4)
    source: SourceName
    title: str
    url: str
    raw_score: float  # upvotes / stars / engagements as provided by the source
    comment_count: int = 0
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoredItem(BaseModel):
    """Item with normalised velocity + volume scores attached."""

    item: Item
    # Velocity = engagement per unit time (40% weight). Volume = raw engagement (60% weight).
    # Both normalised 0–1 across the full batch before weighting.
    volume_score: float
    velocity_score: float
    combined_score: float  # 0.6 * volume_score + 0.4 * velocity_score


class Brief(BaseModel):
    """The weekly intelligence brief produced by synthesis.py."""

    id: UUID = Field(default_factory=uuid4)
    run_date: datetime = Field(default_factory=_now)
    content_md: str
    signal_mood: SignalMood = SignalMood.NEUTRAL
    status: BriefStatus = BriefStatus.DRAFT
    # Quality gate fields
    quality_score: float | None = None
    revision_count: int = 0
    niche_voice_passed: bool = False
    # Timestamps
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Digest(BaseModel):
    """Daily signal digest — radar + scoring only, no synthesis pass."""

    id: UUID = Field(default_factory=uuid4)
    run_date: datetime = Field(default_factory=_now)
    content_md: str
    signals: list[dict[str, Any]] = Field(default_factory=list)
    source_health: dict[str, int] | None = None
    created_at: datetime = Field(default_factory=_now)


class Post(BaseModel):
    """Per-platform content draft derived from a Brief."""

    id: UUID = Field(default_factory=uuid4)
    brief_id: UUID
    platform: Platform
    content: str
    status: PostStatus = PostStatus.DRAFT
    # Rich media — paths are local Railway volume paths; public_url is set before Blotato call
    image_path: str | None = None
    audio_path: str | None = None
    video_path: str | None = None
    image_public_url: str | None = None
    audio_public_url: str | None = None
    video_public_url: str | None = None
    # Blotato scheduling
    blotato_post_id: str | None = None
    scheduled_for: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class Lead(BaseModel):
    """A public post where someone voices a pain one of the owner's products solves,
    plus a drafted, helpful reply queued for MANUAL review.

    RadarWindow never sends these. The draft-and-queue design keeps a human on
    the last step: automated replies to strangers are spam, get accounts banned,
    and can't be authentically helpful. The pipeline finds the thread and writes
    a first draft; the owner reads it, edits it, and posts it in their own words.
    """

    id: UUID = Field(default_factory=uuid4)
    source: SourceName
    product: str                 # which product genuinely fits: "costwindow" | "radarwindow"
    url: str                     # link straight to the thread/post to reply to
    title: str
    excerpt: str = ""            # the person's own words that signalled the pain
    author: str | None = None
    fit_score: float = 0.0       # 0–1: classifier's honest confidence the product fits
    rationale: str = ""          # one line — why this is a real fit, not a stretch
    draft_reply: str = ""        # helpful-first reply; product mentioned only if it fits
    status: LeadStatus = LeadStatus.PENDING
    created_at: datetime = Field(default_factory=_now)


class AuditEntry(BaseModel):
    """One row in the immutable audit log of all scheduling / posting actions."""

    id: UUID = Field(default_factory=uuid4)
    brief_id: UUID
    platform: Platform
    action: str  # e.g. "scheduled", "posted", "failed", "skipped"
    blotato_response_id: str | None = None
    scheduled_for: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    detail: dict[str, Any] = Field(default_factory=dict)
