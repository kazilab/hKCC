"""Export hKCC data from the SQLite DB into a single JSON the bundle ships with.

Self-contained: uses only the Python standard library (``sqlite3``), so it runs
without the project's runtime dependencies installed. It reads the version from
``pyproject.toml`` — the single source of truth — and mirrors the shapes the
Streamlit ``app/data_client.py`` produces, so the React bundle renders the same
data the live app does.

Usage:
    python standalone/scripts/export_data.py            # uses ../../hkcc.db
    python standalone/scripts/export_data.py path/to.db
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tomllib
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "hkcc.db"
OUT = Path(__file__).resolve().parents[1] / "src" / "data.json"

DEVELOPER = "Data Analysis Team @KaziLab.se"
CONTACT = "hkcc@kazilab.se"


def _version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def main() -> None:
    if not DB_PATH.is_file():
        raise SystemExit(f"DB not found: {DB_PATH}")
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    def rows(sql: str, *args) -> list[sqlite3.Row]:
        return list(db.execute(sql, args))

    # --- KCCs ------------------------------------------------------------
    kccs = [
        {
            "id": r["id"],
            "n": r["n"],
            "title": r["title"],
            "short": r["short"],
            "description": r["description"],
            "mechanism": r["mechanism"],
            "icon": r["icon"],
            "is_extended": bool(r["is_extended"]),
        }
        for r in rows("SELECT * FROM kccs ORDER BY n")
    ]

    # --- Evidence: per-agent {kcc_id: score} and per-cell reference ids ---
    ev_id_to_refs: dict[int, list[str]] = defaultdict(list)
    for r in rows("SELECT evidence_id, reference_id FROM evidence_citations"):
        ev_id_to_refs[r["evidence_id"]].append(r["reference_id"])

    evidence_by_agent: dict[str, dict[str, int]] = defaultdict(dict)
    evrefs_by_agent: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for r in rows("SELECT id, agent_id, kcc_id, score, n_refs FROM evidence"):
        evidence_by_agent[r["agent_id"]][r["kcc_id"]] = r["score"]
        refs = ev_id_to_refs.get(r["id"], [])
        if refs:
            evrefs_by_agent[r["agent_id"]][r["kcc_id"]] = refs

    # --- Agent -> linked KCAD reference ids (agent_references) ------------
    agent_refs: dict[str, list[str]] = defaultdict(list)
    for r in rows("SELECT agent_id, reference_id FROM agent_references"):
        agent_refs[r["agent_id"]].append(r["reference_id"])

    # --- Agents ----------------------------------------------------------
    agents = [
        {
            "id": r["id"],
            "name": r["name"],
            "cas": r["cas"] or "—",
            "iarc_group": r["iarc_group"] or "—",
            "agent_type": r["agent_type"],
            "summary": r["summary"],
            "monograph_volume": r["monograph_volume"],
            "evaluation_year": r["evaluation_year"],
            "evidence": evidence_by_agent.get(r["id"], {}),
            "evidence_refs": evrefs_by_agent.get(r["id"], {}),
            "ref_ids": agent_refs.get(r["id"], []),
        }
        for r in rows("SELECT * FROM agents ORDER BY name")
    ]

    # --- References (tags + kcc links) -----------------------------------
    tags_by_ref: dict[str, list[str]] = defaultdict(list)
    for r in rows("SELECT reference_id, tag FROM reference_tags"):
        tags_by_ref[r["reference_id"]].append(r["tag"])
    kccs_by_ref: dict[str, list[str]] = defaultdict(list)
    for r in rows("SELECT reference_id, kcc_id FROM reference_kccs"):
        kccs_by_ref[r["reference_id"]].append(r["kcc_id"])

    references = [
        {
            "id": r["id"],
            "year": r["year"],
            "authors": r["authors"],
            "title": r["title"],
            "journal": r["journal"],
            "vol": r["vol"] or "",
            "doi": r["doi"] or "—",
            "pmid": r["pmid"],
            "citations": r["citations"] or 0,
            "source": r["source"],
            "article_id": r["article_id"],
            "url": r["url"],
            "tags": tags_by_ref.get(r["id"], []),
            "kcc_ids": kccs_by_ref.get(r["id"], []),
        }
        for r in rows("SELECT * FROM 'references' ORDER BY year DESC")
    ]

    # --- Assays (+ kcc links, subgroups, study designs) ------------------
    akccs: dict[str, list[str]] = defaultdict(list)
    for r in rows("SELECT assay_id, kcc_id FROM assay_kccs"):
        akccs[r["assay_id"]].append(r["kcc_id"])
    asub: dict[str, list[dict]] = defaultdict(list)
    for r in rows("SELECT assay_id, kcc_id, subgroup FROM assay_kc_subgroups"):
        asub[r["assay_id"]].append({"kcc_id": r["kcc_id"], "subgroup": r["subgroup"]})
    adesign: dict[str, list[dict]] = defaultdict(list)
    for r in rows("SELECT assay_id, kcc_id, design, source FROM assay_study_designs"):
        adesign[r["assay_id"]].append({"kcc_id": r["kcc_id"], "design": r["design"], "source": r["source"]})

    assays = [
        {
            "id": r["id"],
            "name": r["name"],
            "name_alt": r["name_alt"],
            "type": r["type"],
            "target": r["target"],
            "throughput": r["throughput"],
            "oecd_tg": r["oecd_tg"] or "—",
            "notes": r["notes"] or "",
            "source": r["source"],
            "granularity": r["granularity"],
            "kcc_ids": akccs.get(r["id"], []),
            "subgroups": asub.get(r["id"], []),
            "study_designs": adesign.get(r["id"], []),
        }
        for r in rows("SELECT * FROM assays ORDER BY name")
    ]

    abbreviations = [
        {"abbreviation": r["abbreviation"], "expansion": r["expansion"]}
        for r in rows("SELECT abbreviation, expansion FROM kcad_abbreviations ORDER BY abbreviation")
    ]
    column_definitions = [
        {"column_name": r["column_name"], "definition": r["definition"]}
        for r in rows("SELECT column_name, definition FROM kcad_column_definitions ORDER BY column_name")
    ]

    payload = {
        "meta": {
            "version": _version(),
            "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
            "developer": DEVELOPER,
            "contact": CONTACT,
            "counts": {
                "agents": len(agents),
                "kccs": len(kccs),
                "assays": len(assays),
                "references": len(references),
            },
        },
        "kccs": kccs,
        "agents": agents,
        "references": references,
        "assays": assays,
        "abbreviations": abbreviations,
        "columnDefinitions": column_definitions,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT.relative_to(ROOT)}  ({kb:.0f} KB)  v{payload['meta']['version']}")
    print(f"  agents={len(agents)} kccs={len(kccs)} assays={len(assays)} refs={len(references)}")


if __name__ == "__main__":
    main()
