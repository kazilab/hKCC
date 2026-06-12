"""About & methodology."""

import streamlit as st

from app.page_shell import init_page
from db.config import APP_CONTACT_EMAIL, APP_DEVELOPER, APP_TITLE, get_settings

init_page("about")

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
        "snapshots export as CSV/JSON/Parquet and archive to Zenodo."
    )

st.markdown("#### Project metadata")
st.table(
    {
        "Field": ["Version", "Title", "Developed by", "Contact"],
        "Value": [
            f"v{get_settings().release_tag}",
            APP_TITLE,
            APP_DEVELOPER,
            APP_CONTACT_EMAIL,
        ],
    }
)

st.markdown("---")
st.markdown("#### How an agent enters hKCC")
steps = [
    ("01", "Nomination", "Based on IARC monographs, NTP RoC, or emerging epidemiology."),
    ("02", "Evidence extraction", "Mechanistic statements tagged per KCC with verbatim quotes."),
    ("03", "Independent scoring", "Published scores or two curators score 0–4; disagreements ≥2 escalated."),
    ("04", "Release & versioning", "Releases with Zenodo DOI."),
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
