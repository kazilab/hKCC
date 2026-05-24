"""Static API sample bodies for the Data & API explorer (from screens/api.jsx)."""

from __future__ import annotations

ENDPOINTS: dict[str, dict] = {
    "agents": {
        "method": "GET",
        "path": "/api/v1/agents",
        "desc": "List all curated agents with metadata and KCC evidence vectors.",
        "sample": """{
  "count": 26,
  "items": [
    {
      "id": "benzene",
      "name": "Benzene",
      "cas": "71-43-2",
      "iarc_group": "1",
      "sites": ["AML", "lymphoma"],
      "summary": "..."
    }
  ]
}""",
    },
    "kccs": {
        "method": "GET",
        "path": "/api/v1/kccs",
        "desc": "All 14 key characteristics with mechanism notes.",
        "sample": """{
  "count": 14,
  "items": [
    {
      "id": "kcc-02",
      "n": 2,
      "title": "Genotoxicity",
      "short": "Genotoxic",
      "is_extended": false
    }
  ]
}""",
    },
    "matrix": {
        "method": "GET",
        "path": "/api/v1/matrix",
        "desc": "Full agent × KCC evidence matrix.",
        "sample": """{
  "kcc_ids": ["kcc-01", "kcc-02"],
  "rows": [
    {
      "agent_id": "benzene",
      "agent_name": "Benzene",
      "iarc_group": "1",
      "scores": {"kcc-01": 4, "kcc-02": 4}
    }
  ]
}""",
    },
    "assays": {
        "method": "GET",
        "path": "/api/v1/assays",
        "desc": "Assay library mapped to KCCs.",
        "sample": """[
  {
    "id": "ames",
    "name": "Ames test",
    "type": "In vitro",
    "kcc_ids": ["kcc-02"]
  }
]""",
    },
    "contribute": {
        "method": "POST",
        "path": "/api/v1/contribute",
        "desc": "Submit a score proposal (queued for curator review in v2).",
        "sample": """{
  "agent_id": "benzene",
  "kcc_id": "kcc-02",
  "proposed_score": 3,
  "rationale": "New evidence from ...",
  "submitter_email": "researcher@example.org"
}""",
    },
}

AUTH_TIERS = [
    {
        "tier": "PUBLIC",
        "title": "Anonymous",
        "body": "Read-only access to all curated data. No key required.",
        "limit": "100 req / hour · IP-throttled",
    },
    {
        "tier": "RESEARCHER",
        "title": "Free API key",
        "body": "Higher rate limits, webhook subscriptions on dataset updates.",
        "limit": "10 000 req / hour · ORCID auth (v2)",
    },
    {
        "tier": "CURATOR",
        "title": "Write access",
        "body": "Submit revisions to evidence scores. Requires editorial board invite.",
        "limit": "By application (v2)",
    },
]

QUICKSTART = {
    "Python": '''import httpx

r = httpx.get("http://localhost:8000/api/v1/matrix")
matrix = r.json()
print(matrix["rows"][0])''',
    "R": '''library(httr)
library(jsonlite)

m <- fromJSON("http://localhost:8000/api/v1/matrix")
head(m$rows)''',
}
