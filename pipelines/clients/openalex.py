"""OpenAlex API — literature / citation discovery."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

OPENALEX_BASE = "https://api.openalex.org"


def search_works(
    query: str,
    *,
    mailto: str = "hkcc@example.org",
    per_page: int = 15,
) -> list[dict[str, Any]]:
    """Search works; pass a real mailto for OpenAlex polite pool."""
    q = quote(query.strip())
    url = f"{OPENALEX_BASE}/works?search={q}&per-page={per_page}&mailto={quote(mailto)}"
    r = httpx.get(url, timeout=30.0, headers={"User-Agent": f"hKCC/0.1 (mailto:{mailto})"})
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    simplified = []
    for w in results:
        simplified.append(
            {
                "title": w.get("display_name") or w.get("title"),
                "year": w.get("publication_year"),
                "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                "cited_by_count": w.get("cited_by_count"),
                "id": w.get("id", ""),
                "type": w.get("type"),
            }
        )
    return simplified


def openalex_work_url(openalex_id: str) -> str:
    return openalex_id if openalex_id.startswith("http") else f"https://openalex.org/{openalex_id}"
