from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from ..models import Item, SourceName

log = logging.getLogger(__name__)

_SEARCH_URL = "https://api.github.com/search/repositories"
_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
_PER_PAGE = 10
_PUSHED_DAYS = 30  # only repos with activity this recent — keeps dead giants out


def _pushed_window() -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_PUSHED_DAYS)
    return f"pushed:>{cutoff.date().isoformat()}"


class GitHubSource:
    name = SourceName.GITHUB.value

    def __init__(self, topics: list[str]) -> None:
        self._topics = topics

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        items: list[Item] = []
        for topic in self._topics:
            try:
                items.extend(await self._fetch_topic(client, topic))
            except Exception as exc:
                log.warning("github topic=%s failed: %s", topic, exc)
        # deduplicate by URL (same repo can appear under multiple topics)
        seen: set[str] = set()
        unique = []
        for item in items:
            if item.url not in seen:
                seen.add(item.url)
                unique.append(item)
        return unique

    async def _fetch_topic(self, client: httpx.AsyncClient, topic: str) -> list[Item]:
        params = {
            "q": f"topic:{topic} {_pushed_window()}",
            "sort": "stars",
            "order": "desc",
            "per_page": _PER_PAGE,
        }
        r = await client.get(_SEARCH_URL, params=params, headers=_HEADERS)
        r.raise_for_status()
        repos = r.json().get("items", [])
        items = []
        for repo in repos:
            pushed_at = None
            if repo.get("pushed_at"):
                pushed_at = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
            items.append(
                Item(
                    source=SourceName.GITHUB,
                    title=f"{repo['full_name']} — {repo.get('description', '')}",
                    url=repo["html_url"],
                    raw_score=float(repo.get("stargazers_count", 0)),
                    comment_count=int(repo.get("open_issues_count", 0)),
                    published_at=pushed_at,
                    metadata={
                        "topic": topic,
                        "forks": repo.get("forks_count"),
                        "language": repo.get("language"),
                        "watchers": repo.get("watchers_count"),
                    },
                )
            )
        return items
