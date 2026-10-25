from __future__ import annotations

from typing import Protocol

import httpx

from ..models import Item


class Source(Protocol):
    name: str

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        ...
