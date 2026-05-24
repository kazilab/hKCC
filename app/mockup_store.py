"""In-memory dataset from mockup data.js (no Postgres required)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from db.seed.parse_mockup import load_mockup_data


def _norm_kccs(raw: list[dict]) -> list[dict]:
    return [
        {
            "id": k["id"],
            "n": k["n"],
            "title": k["title"],
            "short": k["short"],
            "description": k.get("desc") or k.get("description", ""),
            "mechanism": k.get("mechanism", ""),
            "icon": k["icon"],
            "is_extended": bool(k.get("isNew")),
            "examples": k.get("examples", []),
        }
        for k in raw
    ]


def _norm_agents(raw: list[dict]) -> list[dict]:
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "cas": c.get("cas") or "—",
            "iarc_group": c.get("group") or "—",
            "agent_type": c["type"],
            "summary": c["summary"],
            "sites": c.get("sites", []),
            "evidence": c.get("evidence", {}),
        }
        for c in raw
    ]


def _norm_assays(raw: list[dict]) -> list[dict]:
    return [
        {
            "id": a["id"],
            "name": a["name"],
            "type": a["type"],
            "target": a["target"],
            "throughput": a["throughput"],
            "oecd_tg": a.get("oecd") or "—",
            "notes": a.get("notes") or "",
            "kcc_ids": a.get("kccs", []),
        }
        for a in raw
    ]


def _norm_references(raw: list[dict]) -> list[dict]:
    out = []
    for r in raw:
        kccs_field = r.get("kccs")
        if kccs_field == "all":
            kcc_ids: list[str] = []
        elif isinstance(kccs_field, list):
            kcc_ids = kccs_field
        else:
            kcc_ids = []
        tags = [r["tag"]] if r.get("tag") else []
        out.append(
            {
                "id": r["id"],
                "year": r.get("year"),
                "authors": r["authors"],
                "title": r["title"],
                "journal": r["journal"],
                "vol": r.get("vol") or "",
                "doi": r.get("doi") or "—",
                "citations": r.get("cites") or 0,
                "tags": tags,
                "kcc_ids": kcc_ids,
            }
        )
    return sorted(out, key=lambda x: x.get("year") or 0, reverse=True)


def _build_matrix(kccs: list[dict], agents: list[dict]) -> dict[str, Any]:
    kcc_ids = [k["id"] for k in kccs]
    rows = []
    for a in agents:
        ev = a.get("evidence", {})
        rows.append(
            {
                "agent_id": a["id"],
                "agent_name": a["name"],
                "iarc_group": a.get("iarc_group"),
                "scores": {kid: ev.get(kid, 0) for kid in kcc_ids},
            }
        )
    return {"kcc_ids": kcc_ids, "rows": rows}


def _kcc_stats(kccs: list[dict], agents: list[dict], assays: list[dict]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {k["id"]: {"carc_count": 0, "assay_count": 0} for k in kccs}
    for a in agents:
        for kid, score in a.get("evidence", {}).items():
            if score > 0 and kid in stats:
                stats[kid]["carc_count"] += 1
    for assay in assays:
        for kid in assay.get("kcc_ids", []):
            if kid in stats:
                stats[kid]["assay_count"] += 1
    return stats


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    raw = load_mockup_data()
    kccs = _norm_kccs(raw["kccs"])
    agents = _norm_agents(raw["carcinogens"])
    assays = _norm_assays(raw["assays"])
    references = _norm_references(raw["literature"])
    return {
        "kccs": kccs,
        "agents": agents,
        "assays": assays,
        "references": references,
        "matrix": _build_matrix(kccs, agents),
        "stats": _kcc_stats(kccs, agents, assays),
    }
