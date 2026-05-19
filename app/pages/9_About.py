"""About & methodology — mockup screen 10."""

import streamlit as st

from app.theme import HKCC_CSS

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)

st.markdown('<p class="mono">About hKCC</p>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display">An open, versioned, citable mechanism atlas for human carcinogens.</h1>',
    unsafe_allow_html=True,
)

left, right = st.columns(2)
with left:
    st.markdown("#### Scope")
    st.write(
        "hKCC organises mechanistic evidence linking known and suspected human carcinogens to the "
        "14 key characteristics framework (Smith et al. 2016, plus four extended characteristics). "
        "The platform is not a classification authority — IARC groups are reproduced from monographs."
    )
with right:
    st.markdown("#### Curation")
    st.write(
        "Each evidence score (0–4) is linked to citations at the cell level. Releases are versioned; "
        "snapshots export as CSV/JSON/Parquet and archive to Zenodo. Curator UI and ORCID auth ship in v2."
    )

st.markdown("---")
st.markdown("#### How an agent enters hKCC")
steps = [
    ("01", "Nomination", "Based on IARC monographs, NTP RoC, or emerging epidemiology."),
    ("02", "Evidence extraction", "Mechanistic statements tagged per KCC with verbatim quotes."),
    ("03", "Independent scoring", "Two curators score 0–4; disagreements ≥2 escalated."),
    ("04", "Release & versioning", "Quarterly releases with Zenodo DOI."),
]
cols = st.columns(4)
for col, (n, title, desc) in zip(cols, steps):
    with col:
        st.caption(f"STEP {n}")
        st.markdown(f"**{title}**")
        st.write(desc)

st.markdown("---")
st.markdown("#### Stack")
st.table(
    {
        "Layer": ["Frontend", "API", "Database", "Pipelines", "License"],
        "Technology": [
            "Streamlit · custom HTML components",
            "FastAPI · Pydantic",
            "PostgreSQL 16 · SQLAlchemy · Alembic",
            "Python · PubChem / ToxCast / OpenAlex (planned)",
            "CC-BY-4.0 (data) · MIT (code)",
        ],
    }
)
