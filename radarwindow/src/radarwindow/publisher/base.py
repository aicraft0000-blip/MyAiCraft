from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..models import Post


class Publisher(Protocol):
    """
    Swap the posting layer by changing one file.
    RadarWindow calls schedule() — never Blotato directly.
    """

    async def schedule(self, post: Post, scheduled_for: datetime) -> str:
        """Schedule a post. Returns the provider's post ID."""
        ...

    async def get_engagement(self, provider_post_id: str) -> dict | None:
        """
        Return engagement metrics for a previously scheduled post, or None if
        the provider doesn't expose them. Powers the feedback loop. Shape:
        {impressions, likes, comments, shares, clicks}.
        """
        ...
