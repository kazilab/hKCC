"""KCAD methodology — source paper, abbreviations glossary, column dictionary."""

from __future__ import annotations

import html

import streamlit as st

from app.data_client import (
    get_source_paper,
    list_abbreviations,
    list_column_definitions,
)
from app.page_shell import init_page

init_page("methodology")

paper = get_source_paper() or {}

st.markdown('<p class="mono">Methodology · KCAD</p>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display" style="font-size:2rem">KCAD source &amp; data dictionary</h1>',
    unsafe_allow_html=True,
)
st.caption(
    "Every assay, annotation and KCAD-derived agent in hKCC is anchored to the "
    "publication below. Browse the column dictionary and abbreviation glossary "
    "to understand how the data was originally encoded."
)

# ── Source paper card ────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("### Source publication")
    if paper:
        title = paper.get("title", "—")
        authors = paper.get("authors", "—")
        journal = paper.get("journal", "—")
        year = paper.get("year", "—")
        vol = paper.get("vol")
        article_id = paper.get("article_id")
        doi = paper.get("doi")
        url = paper.get("url") or (f"https://doi.org/{doi}" if doi else None)

        st.markdown(f"**{title}**")
        st.caption(f"{authors} · _{journal}_ ({year})" + (f", vol. {vol}" if vol else "") + (f", article {article_id}" if article_id else ""))
        if doi:
            st.markdown(
                "DOI: "
                f'<a href="{html.escape(url or "")}" target="_blank" rel="noopener noreferrer">'
                f"<code>{html.escape(doi)}</code></a>"
                " · Database URL: "
                '<a href="https://kcad.cchem.berkeley.edu" target="_blank" rel="noopener noreferrer">'
                "<code>https://kcad.cchem.berkeley.edu</code></a>",
                unsafe_allow_html=True,
            )
    else:
        st.caption(
            "Paper reference row not seeded — run "
            "`python -m pipelines.import_kcad_supplementary`."
        )

# ── Abbreviations ───────────────────────────────────────────────────────────
abbrevs = list_abbreviations()
st.markdown(f"### Abbreviations ({len(abbrevs)})")
st.caption(
    "Sourced from KCManuscript STable3. Used throughout the assay endpoints, "
    "biomarkers and notes."
)
if not abbrevs:
    st.caption(
        "No abbreviations indexed yet — run "
        "`python -m pipelines.import_kcad_supplementary` after applying the "
        "schema migration."
    )
else:
    q = st.text_input(
        "Search abbreviations",
        placeholder="e.g. 8-OHdG, ROS, BAX",
        key="abbrev_search",
    )
    filtered = abbrevs
    if q:
        ql = q.lower()
        filtered = [
            a
            for a in abbrevs
            if ql in a["abbreviation"].lower() or ql in a["expansion"].lower()
        ]
    st.caption(f"Showing {len(filtered)} / {len(abbrevs)}")
    cols = st.columns(2)
    for i, a in enumerate(filtered):
        with cols[i % 2]:
            st.markdown(
                f'<div style="padding:6px 0;border-bottom:1px dotted #ccc">'
                f'<code>{a["abbreviation"]}</code> &nbsp;→&nbsp; {a["expansion"]}'
                f"</div>",
                unsafe_allow_html=True,
            )

# ── Column dictionary ───────────────────────────────────────────────────────
defs = list_column_definitions()
st.markdown(f"### Column dictionary ({len(defs)})")
st.caption(
    "Definitions for every column in `suppl_data/filtered_table.csv` "
    "(KCManuscript STable2). These are surfaced as tooltips on the Assays "
    "page detail view."
)
if not defs:
    st.caption(
        "No column definitions indexed — run "
        "`python -m pipelines.import_kcad_supplementary`."
    )
else:
    for d in defs:
        with st.expander(f"`{d['column_name']}`"):
            st.write(d["definition"])
