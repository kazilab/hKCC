"""Tiny in-process IP rate limiter for write endpoints.

This is intentionally lightweight (single-process, in-memory). For production
behind multiple replicas, layer Cloudflare / Caddy / nginx limits on top.
"""

from __future__ import annotations

import os
import time
from collections import deque

from fastapi import HTTPException, Request, status


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


WINDOW_SECONDS = _env_int("HKCC_CONTRIBUTE_WINDOW_SECONDS", 3600)
MAX_PER_WINDOW = _env_int("HKCC_CONTRIBUTE_MAX_PER_WINDOW", 10)

_hits: dict[str, deque[float]] = {}


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_contribute(request: Request) -> None:
    """FastAPI dependency: raise 429 if the caller exceeds the contribute budget."""
    if MAX_PER_WINDOW <= 0:
        return
    key = _client_key(request)
    now = time.monotonic()
    bucket = _hits.setdefault(key, deque())
    cutoff = now - WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= MAX_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit: {MAX_PER_WINDOW} contributions per {WINDOW_SECONDS}s window.",
        )
    bucket.append(now)


def reset_rate_limit() -> None:
    """Test helper — clears the in-memory bucket."""
    _hits.clear()
