"""Generate Markdown docs from the KCAD seed JSON files.

Outputs:
- ``docs/KCAD_DATA_DICTIONARY.md`` (from ``db/seed/kcad/column_definitions.json``)
- ``docs/KCAD_ABBREVIATIONS.md``   (from ``db/seed/kcad/abbreviations.json``)

Both files cite the source paper (Rigutto et al. 2025, ``baaf026``) explicitly
so the docs always tell the reader where the data came from.

Run manually after editing the seed JSONs::

    python -m pipelines.gen_kcad_docs
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "db" / "seed" / "kcad"
DOCS = REPO / "docs"

CITATION = (
    "> Source: **Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT.**\n"
    "> *Mapping assays to the key characteristics of carcinogens to support\n"
    "> decision-making.* Database (Oxford) **2025**, article `baaf026`.\n"
    "> DOI: [`10.1093/database/baaf026`](https://doi.org/10.1093/database/baaf026)."
)


def _escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", "<br>")


def gen_column_dictionary() -> Path:
    raw = json.loads((SEED / "column_definitions.json").read_text())
    defs = raw.get("definitions", [])
    out = DOCS / "KCAD_DATA_DICTIONARY.md"
    lines = [
        "<!-- This file is auto-generated. Run: python -m pipelines.gen_kcad_docs -->",
        "",
        "# KCAD data dictionary",
        "",
        CITATION,
        "",
        "Definitions for every column in `suppl_data/filtered_table.csv`,",
        "reproduced verbatim from KCManuscript Supplementary Table 2.",
        "",
        "Programmatic access:",
        "",
        "- API: `GET /api/v1/methodology/columns`",
        "- Streamlit UI: `app/pages/9a_Methodology.py`",
        "- DB table: `kcad_column_definitions`",
        "",
        "See also: [`KCAD_ABBREVIATIONS.md`](KCAD_ABBREVIATIONS.md) for the glossary.",
        "",
        "| Column | Definition |",
        "| --- | --- |",
    ]
    for d in defs:
        name = _escape(d.get("column_name", ""))
        defn = _escape(d.get("definition", ""))
        lines.append(f"| `{name}` | {defn} |")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def gen_abbreviations() -> Path:
    raw = json.loads((SEED / "abbreviations.json").read_text())
    abbrevs = raw.get("abbreviations", [])
    out = DOCS / "KCAD_ABBREVIATIONS.md"
    lines = [
        "<!-- This file is auto-generated. Run: python -m pipelines.gen_kcad_docs -->",
        "",
        "# KCAD abbreviations",
        "",
        CITATION,
        "",
        f"{len(abbrevs)} abbreviations used throughout the KCAD dataset,",
        "reproduced verbatim from KCManuscript Supplementary Table 3.",
        "",
        "Programmatic access:",
        "",
        "- API: `GET /api/v1/methodology/abbreviations`",
        "- Streamlit UI: `app/pages/9a_Methodology.py`",
        "- DB table: `kcad_abbreviations`",
        "",
        "| Abbreviation | Expansion |",
        "| --- | --- |",
    ]
    for a in abbrevs:
        abbr = _escape(a.get("abbreviation", ""))
        exp = _escape(a.get("expansion", ""))
        lines.append(f"| `{abbr}` | {exp} |")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    p1 = gen_column_dictionary()
    p2 = gen_abbreviations()
    print(f"Wrote {p1.relative_to(REPO)}")
    print(f"Wrote {p2.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
