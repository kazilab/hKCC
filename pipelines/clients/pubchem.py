"""PubChem PUG REST — compound search, properties, bioassay summary."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def _get_json(url: str, *, timeout: float = 30.0) -> dict[str, Any]:
    r = httpx.get(url, timeout=timeout, headers={"User-Agent": "hKCC/0.1 (research; +https://github.com)"})
    r.raise_for_status()
    return r.json()


def search_compound_by_name(name: str, *, max_results: int = 10) -> list[int]:
    """Return PubChem CIDs for a name search."""
    q = quote(name.strip())
    url = f"{PUBCHEM_BASE}/compound/name/{q}/cids/JSON"
    data = _get_json(url)
    ids = data.get("IdentifierList", {}).get("CID", [])
    if isinstance(ids, int):
        ids = [ids]
    return ids[:max_results]


def get_compound_properties(cid: int, properties: list[str] | None = None) -> dict[str, Any]:
    props = properties or ["MolecularFormula", "MolecularWeight", "CanonicalSMILES", "IUPACName", "XLogP"]
    p = ",".join(props)
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/{p}/JSON"
    data = _get_json(url)
    rows = data.get("PropertyTable", {}).get("Properties", [])
    return rows[0] if rows else {}


def assay_summary_table(cid: int, *, max_rows: int = 50) -> tuple[list[str], list[dict[str, str]]]:
    """Bioassay summary from PubChem (aggregates many screening programs; includes Tox21-style assays)."""
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/assaysummary/JSON"
    data = _get_json(url)
    table = data.get("Table", {})
    cols = table.get("Columns", {}).get("Column", [])
    if isinstance(cols, str):
        cols = [cols]
    rows_raw = table.get("Row", [])
    if isinstance(rows_raw, dict):
        rows_raw = [rows_raw]
    out: list[dict[str, str]] = []
    for row in rows_raw[:max_rows]:
        cells = row.get("Cell", [])
        if isinstance(cells, str):
            cells = [cells]
        rec: dict[str, str] = {}
        for i in range(max(len(cols), len(cells))):
            key = cols[i] if i < len(cols) else f"col_{i}"
            rec[key] = str(cells[i]) if i < len(cells) else ""
        out.append(rec)
    return cols, out


def pubchem_compound_url(cid: int) -> str:
    return f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"

def pubchem_bioassay_url(cid: int) -> str:
    return f"https://pubchem.ncbi.nlm.nih.gov/#query=CID{cid}"
