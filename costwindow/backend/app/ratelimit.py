"""Minimal in-memory sliding-window rate limiter.

Enough to blunt brute-force on the auth endpoints without adding a dependency
or external store. Per-process (Railway runs a single container), so it's a
speed bump, not a distributed quota — which is the right level for
register/login abuse. Fails open on any internal error.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_HITS: dict[str, deque] = defaultdict(deque)


def rate_limit(name: str, limit: int, window_s: int):
    """Dependency factory: allow `limit` requests per `window_s` seconds per IP."""

    def _dep(request: Request):
        try:
            ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                  or (request.client.host if request.client else "unknown"))
            key = f"{name}:{ip}"
            now = time.time()
            hits = _HITS[key]
            cutoff = now - window_s
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= limit:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests — please wait a minute and try again.",
                )
            hits.append(now)
            if len(_HITS) > 10000:  # crude memory bound
                _HITS.clear()
        except HTTPException:
            raise
        except Exception:
            return  # fail open

    return _dep
