"""About & methodology."""

import streamlit as st

from hkcc.app.data_client import list_candidate_domains
from hkcc.app.page_shell import init_page
from hkcc.db.config import APP_CONTACT_EMAIL, APP_DEVELOPER, APP_TITLE, get_settings

init_page("about")

st.markdown('<p class="mono">About hKCC</p>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display">An open, versioned, citable record of mechanistic evidence for human carcinogens.</h1>',
    unsafe_allow_html=True,
)

st.info(
    "**Early development (v0.0.x).** The dataset, the schema and the API are still changing "
    "between releases. Evidence scores are derived from published source tables by documented "
    "rules rather than assigned by hand; see the Methodology page before relying on a value."
)

left, right = st.columns(2)
_domains = list_candidate_domains()

with left:
    st.markdown("#### Scope")
    # Counted from the data: the text said "Four" while the database held five
    # (the paper's EMD1-4 plus CD5, which carries its own provenance).
    _paper_domains = [d for d in _domains if d.get("source_ref_id") == "kazi2026-emd"]
    _other_domains = [d for d in _domains if d.get("source_ref_id") != "kazi2026-emd"]
    _domain_phrase = f"{len(_paper_domains)} cross-cutting candidate domains from Kazi et al."
    if _other_domains:
        _domain_phrase += f", plus {', '.join(d['code'] for d in _other_domains)} as a platform candidate"
    st.write(
        "hKCC organises mechanistic evidence linking known and suspected human carcinogens to the "
        f"ten key characteristics framework (Smith et al. 2016). {_domain_phrase} — "
        f"{len(_domains)} in total — sit alongside it as annotations, not as additional "
        "characteristics, and carry no score of their own. "
        "The platform is not a classification authority — IARC groups are reproduced from monographs."
    )
with right:
    st.markdown("#### Scoring")
    st.write(
        "Each evidence score (0–4) is derived from a published source table by a deterministic, "
        "documented rule, and every cell records **the derivation it came from** — the IARC "
        "analysis the score was computed from, not the underlying experiments. Most cells cite "
        "only that analysis; where the KCAD assay library adds study records, they are shown "
        "separately as supporting literature. Releases are versioned; snapshots export as "
        "CSV/JSON/Parquet."
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
    ("01", "Source selection", "Peer-reviewed datasets that map agents to key characteristics."),
    ("02", "Extraction", "Per-(agent, KC) calls and strength labels read from the published tables."),
    ("03", "Deterministic scoring", "A documented rule maps published labels and calls to the 0–4 scale."),
    ("04", "Release & versioning", "Tagged releases exported as CSV/JSON/Parquet."),
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
            "SQLite · SQLAlchemy",
            "Python · PubChem / OpenAlex / EPA CompTox (live lookup)",
            "CC-BY-4.0 (data) · MIT (code)",
        ],
    }
)
