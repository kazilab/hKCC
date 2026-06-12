"""EPA CCTE / CompTox — optional API key; always provide dashboard links."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

# Public dashboard (no key). Exact routes may change; this is the main entry.
COMPTOX_DASHBOARD = "https://comptox.epa.gov/dashboard/"
CCTE_DOCS = "https://www.epa.gov/comptox-tools/computational-toxicology-and-exposure-apis-about"

# If EPA exposes this pattern with X-Api-Key, callers can try; 404/401 is handled gracefully.
CCTE_API_BASE = "https://api-ccte.epa.gov"


def comptox_search_url(query: str) -> str:
    """Deep-link style search into CompTox (query in fragment; user completes search if needed)."""
    return f"{COMPTOX_DASHBOARD}?search={quote(query)}"


def try_chemical_keyword_search(keyword: str, api_key: str | None) -> dict[str, Any]:
    """
    Optional live CCTE call when user provides an API key (request from EPA).
    Endpoint may vary by API version — failures return a structured error.
    """
    if not api_key or not api_key.strip():
        return {
            "ok": False,
            "skipped": True,
            "message": "No CCTE API key configured. Request a free key from EPA (see docs link below).",
        }
    # Candidate path used in some CCTE deployments; safe to fail without breaking the app.
    url = f"{CCTE_API_BASE}/chemical/chem/search/chemical?keyword={quote(keyword)}"
    try:
        r = httpx.get(
            url,
            timeout=25.0,
            headers={"X-Api-Key": api_key.strip(), "Accept": "application/json"},
        )
        if r.status_code == 200:
            return {"ok": True, "data": r.json()}
        return {"ok": False, "status_code": r.status_code, "body_preview": r.text[:500]}
    except httpx.HTTPError as e:
        return {"ok": False, "error": str(e)}
