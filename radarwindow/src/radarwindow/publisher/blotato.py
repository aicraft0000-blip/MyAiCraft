from __future__ import annotations

import logging
from datetime import datetime

import httpx

from ..config import settings
from ..models import Platform, Post

log = logging.getLogger(__name__)

# Blotato v2 API — validated against the live service 2026-07-05.
# Auth header is `blotato-api-key` (NOT Bearer); posts need an accountId and
# a target.targetType; every additionalPosts item must carry mediaUrls.
_BASE = "https://backend.blotato.com/v2"

_PLATFORM_MAP = {
    Platform.X: "twitter",
    Platform.LINKEDIN: "linkedin",
    Platform.INSTAGRAM: "instagram",
}

_X_LIMIT = 280

# Hard rate limit: never send more than 3 posts per minute to Blotato.
# A bug in the caller must not be able to trigger a platform ban.
_MAX_POSTS_PER_MINUTE = 3
_post_count = 0
_window_start: datetime | None = None


def split_for_x(text: str, limit: int = _X_LIMIT) -> list[str]:
    """Split text into tweet-sized chunks at paragraph/sentence boundaries.

    Pure helper (unit-tested). Single chunk when it already fits.
    """
    text = text.strip()
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    # Prefer paragraph breaks, then sentence ends.
    import re
    parts = re.split(r"(\n\n+|(?<=[.!?…])\s+)", text)
    for part in parts:
        if not part or part.isspace() and "\n" not in part:
            part = part or ""
        candidate = current + part
        if len(candidate.strip()) <= limit:
            current = candidate
            continue
        if current.strip():
            chunks.append(current.strip())
        # A single part longer than the limit gets hard-wrapped.
        while len(part.strip()) > limit:
            head = part[:limit].rsplit(" ", 1)[0] or part[:limit]
            chunks.append(head.strip())
            part = part[len(head):]
        current = part
    if current.strip():
        chunks.append(current.strip())
    return chunks


class BlatoPublisher:
    """
    Thin connector to Blotato's scheduling API.
    RadarWindow never calls Blotato directly from anywhere else — all posting
    goes through this class so swapping the provider means changing one file.
    """

    def _account_id(self, platform: Platform) -> str:
        return {
            Platform.X: settings.BLOTATO_TWITTER_ACCOUNT_ID,
            Platform.LINKEDIN: settings.BLOTATO_LINKEDIN_ACCOUNT_ID,
            Platform.INSTAGRAM: settings.BLOTATO_INSTAGRAM_ACCOUNT_ID,
        }[platform]

    async def schedule(self, post: Post, scheduled_for: datetime) -> str:
        """Schedule a post via Blotato. Returns Blotato's submission ID."""
        self._rate_check()
        platform_key = _PLATFORM_MAP[post.platform]
        account_id = self._account_id(post.platform)
        if not account_id:
            raise RuntimeError(f"No Blotato account id configured for {platform_key}")

        media: list[str] = []
        target: dict = {"targetType": platform_key}
        if post.platform == Platform.INSTAGRAM and post.video_public_url:
            # Reels carry the video; the image is baked into it.
            media = [post.video_public_url]
            target["mediaType"] = "reel"
        elif post.image_public_url:
            media = [post.image_public_url]

        if post.platform == Platform.X:
            parts = split_for_x(post.content)
            text = parts[0]
            additional = [{"text": p, "mediaUrls": []} for p in parts[1:]]
        else:
            text, additional = post.content, []

        content: dict = {"platform": platform_key, "text": text, "mediaUrls": media}
        if additional:
            content["additionalPosts"] = additional

        payload = {
            "post": {
                "accountId": str(account_id),
                "target": target,
                "content": content,
            },
            "scheduledTime": scheduled_for.isoformat(),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{_BASE}/posts",
                json=payload,
                headers={
                    "blotato-api-key": settings.BLOTATO_API_KEY,
                    "Content-Type": "application/json",
                },
            )
            r.raise_for_status()
            data = r.json()

        post_id = data.get("postSubmissionId") or data.get("id") or str(data)
        log.info("blotato: scheduled %s post id=%s for %s", platform_key, post_id, scheduled_for)
        return str(post_id)

    async def get_engagement(self, provider_post_id: str) -> dict | None:
        """
        Best-effort engagement fetch. Blotato's analytics surface is limited and
        plan-dependent; if unavailable we return None and the feedback loop simply
        has no data for that post (rather than failing). Swapping to Zernio later
        means filling this in here only.
        """
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{_BASE}/posts/{provider_post_id}",
                    headers={"blotato-api-key": settings.BLOTATO_API_KEY},
                )
                if r.status_code != 200:
                    return None
                d = r.json()
            stats = d.get("analytics") or d
            return {
                "impressions": int(stats.get("impressions", 0) or 0),
                "likes": int(stats.get("likes", 0) or 0),
                "comments": int(stats.get("comments", 0) or 0),
                "shares": int(stats.get("shares", 0) or 0),
                "clicks": int(stats.get("clicks", 0) or 0),
            }
        except Exception as exc:
            log.info("blotato: engagement unavailable for %s (%s)", provider_post_id, exc)
            return None

    def _rate_check(self) -> None:
        global _post_count, _window_start
        now = datetime.now()
        if _window_start is None or (now - _window_start).seconds >= 60:
            _window_start = now
            _post_count = 0
        _post_count += 1
        if _post_count > _MAX_POSTS_PER_MINUTE:
            raise RuntimeError(
                f"Blotato rate limit guard: {_post_count} posts in one minute — aborting to protect accounts"
            )
