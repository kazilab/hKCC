"""Generate the KCAD Markdown references from the database.

Outputs:
- ``docs/KCAD_DATA_DICTIONARY.md`` (from ``kcad_column_definitions``)
- ``docs/KCAD_ABBREVIATIONS.md``   (from ``kcad_abbreviations``)

``hkcc.db`` is the single source of truth for both; there is no parallel seed
file to keep in sync. Rows are emitted in insertion order (``rowid``), which
preserves the ordering of the published supplementary tables — the column
dictionary in particular is grouped by topic, not alphabetically.

Both files cite the source paper (Rigutto et al. 2025, ``baaf026``) explicitly
so the docs always tell the reader where the data came from.

Run manually after the database changes::

    python -m pipelines.gen_kcad_docs
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from hkcc.db.config import REPO_ROOT
from hkcc.db.session import engine

# Dev tool: writes into the checkout's docs/ when run from a clone, else ./docs.
REPO = REPO_ROOT or Path.cwd()
DOCS = REPO / "docs"

CITATION = (
    "> Source: **Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT.**\n"
    "> *Mapping assays to the key characteristics of carcinogens to support\n"
    "> decision-making.* Database (Oxford) **2025**, article `baaf026`.\n"
    "> DOI: [`10.1093/database/baaf026`](https://doi.org/10.1093/database/baaf026)."
)


def _escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", "<br>")


def _rows(table: str, *columns: str) -> list[tuple[str, ...]]:
    """Fetch ``columns`` from ``table`` in stored order."""
    cols = ", ".join(f'"{c}"' for c in columns)
    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(text(f'SELECT {cols} FROM "{table}" ORDER BY rowid'))]


def gen_column_dictionary() -> Path:
    defs = _rows("kcad_column_definitions", "column_name", "definition")
    out = DOCS / "KCAD_DATA_DICTIONARY.md"
    lines = [
        "<!-- This file is auto-generated. Run: python -m pipelines.gen_kcad_docs -->",
        "",
        "# KCAD data dictionary",
        "",
        CITATION,
        "",
        "Definitions for every column of the KCAD annotation table,",
        "reproduced verbatim from Supplementary Table 2 of the source paper.",
        "",
        "Programmatic access:",
        "",
        "- API: `GET /api/v1/methodology/columns`",
        "- Streamlit UI: `hkcc/app/pages/9a_Methodology.py`",
        "- DB table: `kcad_column_definitions`",
        "",
        "See also: [`KCAD_ABBREVIATIONS.md`](KCAD_ABBREVIATIONS.md) for the glossary.",
        "",
        "| Column | Definition |",
        "| --- | --- |",
    ]
    for name, defn in defs:
        lines.append(f"| `{_escape(name or '')}` | {_escape(defn or '')} |")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def gen_abbreviations() -> Path:
    abbrevs = _rows("kcad_abbreviations", "abbreviation", "expansion")
    out = DOCS / "KCAD_ABBREVIATIONS.md"
    lines = [
        "<!-- This file is auto-generated. Run: python -m pipelines.gen_kcad_docs -->",
        "",
        "# KCAD abbreviations",
        "",
        CITATION,
        "",
        f"{len(abbrevs)} abbreviations used throughout the KCAD dataset,",
        "reproduced verbatim from Supplementary Table 3 of the source paper.",
        "",
        "Programmatic access:",
        "",
        "- API: `GET /api/v1/methodology/abbreviations`",
        "- Streamlit UI: `hkcc/app/pages/9a_Methodology.py`",
        "- DB table: `kcad_abbreviations`",
        "",
        "| Abbreviation | Expansion |",
        "| --- | --- |",
    ]
    for abbr, exp in abbrevs:
        lines.append(f"| `{_escape(abbr or '')}` | {_escape(exp or '')} |")
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
