"""Tiny in-process IP rate limiter for write endpoints.

This is intentionally lightweight (single-process, in-memory). For production
behind multiple replicas, layer Cloudflare / Caddy / nginx limits on top.

``X-Forwarded-For`` is **not** trusted by default. The header is written by the
client, so keying the bucket on it lets anyone reset their own budget by
rotating the value. It is only consulted when ``HKCC_TRUSTED_PROXY_HOPS`` says
how many reverse proxies sit in front of the API, and then only the hop that a
trusted proxy actually appended is used.
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
# Number of reverse proxies between the internet and this process. 0 (default)
# means the API is reached directly, so X-Forwarded-For is ignored entirely.
TRUSTED_PROXY_HOPS = _env_int("HKCC_TRUSTED_PROXY_HOPS", 0)

_hits: dict[str, deque[float]] = {}


def _client_key(request: Request) -> str:
    """Identify the caller, resisting header spoofing.

    With no trusted proxy the peer address is the only trustworthy identifier.
    Behind ``n`` trusted proxies, the useful entry is the ``n``-th from the
    right of ``X-Forwarded-For``: everything to its left was supplied by the
    caller and can say anything.
    """
    peer = request.client.host if request.client else "unknown"
    if TRUSTED_PROXY_HOPS <= 0:
        return peer

    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if len(parts) >= TRUSTED_PROXY_HOPS:
        return parts[-TRUSTED_PROXY_HOPS]
    # Header shorter than the configured chain — it did not come through the
    # expected proxies, so fall back to the peer rather than trusting it.
    return peer


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
