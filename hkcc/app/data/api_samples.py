"""Reference material for the Data & API page.

Sample bodies are trimmed copies of real responses — ``tests/test_api_samples.py``
asserts their shape still matches what the routers return, so the documentation
cannot drift from the API the way the previous hand-written envelopes did.
"""

from __future__ import annotations

ENDPOINTS: dict[str, dict] = {
    "agents": {
        "method": "GET",
        "path": "/api/v1/agents",
        "desc": "All agents with IARC classification and monograph metadata. Returns a JSON array.",
        "sample": """[
  {
    "id": "benzene-iarc",
    "name": "Benzene",
    "cas": "71-43-2",
    "iarc_group": "1",
    "agent_type": "Industrial chemical",
    "summary": "IARC Monograph Volume 29, Sup 7, 100F, 120, Group 1.",
    "last_review": null,
    "sites": [],
    "monograph_volume": "29, Sup 7, 100F, 120",
    "monograph_pub_year": "2018",
    "evaluation_year": 2017,
    "source_ref_id": "kcad-paper-rigutto-2025"
  }
]""",
    },
    "kccs": {
        "method": "GET",
        "path": "/api/v1/kccs",
        "desc": "The ten established key characteristics — the reference ontology. Returns a JSON array.",
        "sample": """[
  {
    "id": "kcc-02",
    "n": 2,
    "title": "Genotoxicity",
    "short": "Genotoxic",
    "description": "Is genotoxic ...",
    "mechanism": "Direct or indirect DNA damage ...",
    "icon": "helix",
    "is_extended": false
  }
]""",
    },
    "matrix": {
        "method": "GET",
        "path": "/api/v1/matrix",
        "desc": "The full agent × KCC score matrix. `scores` omits pairs that were never evaluated.",
        "sample": """{
  "kcc_ids": ["kcc-01", "kcc-02", "..."],
  "rows": [
    {
      "agent_id": "benzene-iarc",
      "agent_name": "Benzene",
      "iarc_group": "1",
      "scores": {"kcc-01": 4, "kcc-02": 4, "kcc-03": 4}
    }
  ]
}""",
    },
    "assays": {
        "method": "GET",
        "path": "/api/v1/assays",
        "desc": "Assay library mapped to KCCs. Filters: source, design, subgroup.",
        "sample": """[
  {
    "id": "kcad-ames-assay",
    "name": "Ames test",
    "name_alt": null,
    "type": "in vitro",
    "target": "Mutagenicity",
    "throughput": "medium",
    "oecd_tg": "471",
    "source": "kcad",
    "granularity": "assay",
    "source_ref_id": "kcad-paper-rigutto-2025",
    "kcc_ids": ["kcc-02"],
    "subgroups": [],
    "study_designs": []
  }
]""",
    },
    "domains": {
        "method": "GET",
        "path": "/api/v1/domains",
        "desc": (
            "Layer 2: cross-cutting candidate domains. Each parents onto one or more KCCs and "
            "carries no score of its own — an observation is counted once, against its KCC."
        ),
        "sample": """[
  {
    "id": "emd2",
    "code": "EMD2",
    "n": 2,
    "title": "Microbiome-mediated disposition and host response",
    "short": "Microbiome",
    "definition": "Exposure changes microbial function, or ...",
    "minimum_evidence": "Functional metagenomics or metabolomics, ...",
    "key_exclusions": "Taxonomic shifts or diversity indices alone ...",
    "status": "candidate",
    "source_ref_id": "kazi2026-emd",
    "primary_kcc_ids": ["kcc-01", "kcc-06", "kcc-07", "kcc-08", "kcc-10"],
    "secondary_kcc_ids": [],
    "assay_ids": ["kcc-microbiome-16s"],
    "reference_ids": []
  }
]""",
    },
    "monograph": {
        "method": "GET",
        "path": "/api/v1/monograph/strengths",
        "desc": "Per-(agent, KC) standardized strength labels, with the IARC mechanistic data role.",
        "sample": """[
  {
    "agent_id": "benzene-iarc",
    "kcc_id": "kcc-02",
    "strength_label": "Strong",
    "data_role": "Supportive",
    "iarc_group": "1",
    "source_ref_id": "rusyn2024-tenyears"
  }
]""",
    },
    "contribute": {
        "method": "POST",
        "path": "/api/v1/contribute",
        "desc": (
            "Propose a revision to an **existing** score. Queued as a pending revision for "
            "curator review. **Revisions only in v0** — a pair with no evidence row cannot "
            "receive a proposal and returns 404, which covers the 866 unassessed pairs."
        ),
        "sample": """// request
{
  "agent_id": "benzene-iarc",
  "kcc_id": "kcc-02",
  "proposed_score": 3,
  "rationale": "New evidence from ...",
  "submitter_name": "A. Researcher"
}

// response
{
  "revision_id": 1,
  "status": "pending",
  "message": "Proposal recorded for curator review (v2 workflow)."
}""",
    },
}

# What the API actually enforces today. Every number here is read from the
# running configuration rather than aspirational.
ACCESS_NOTES = [
    {
        "title": "No authentication",
        "body": (
            "Every read endpoint is public and unauthenticated. There are no API keys, "
            "no accounts and no per-user quotas."
        ),
    },
    {
        "title": "Read limits",
        "body": (
            "Reads are not throttled by the application. If you plan sustained bulk access, "
            "download a release bundle instead of crawling the API."
        ),
    },
    {
        "title": "Writes",
        "body": (
            "`POST /contribute` is open but rate-limited per client IP, and the pending queue "
            "is capped. Submissions are proposals only — they never change a published score. "
            "**It revises existing scores only:** a pair with no evidence row returns 404, so "
            "the 866 unassessed pairs cannot receive proposals in this version."
        ),
    },
]

QUICKSTART_TEMPLATE = {
    "Python": """import httpx

BASE = "{base}"
matrix = httpx.get(f"{{BASE}}/api/v1/matrix").json()
print(matrix["rows"][0])""",
    "R": """library(jsonlite)

base <- "{base}"
m <- fromJSON(paste0(base, "/api/v1/matrix"))
head(m$rows)""",
}


def quickstart(base_url: str) -> dict[str, str]:
    """Snippets pointing at ``base_url`` rather than a hard-coded localhost."""
    return {lang: tpl.format(base=base_url) for lang, tpl in QUICKSTART_TEMPLATE.items()}
