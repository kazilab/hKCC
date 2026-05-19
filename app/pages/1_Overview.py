"""Overview — mockup screen 1."""

import streamlit as st

from app.components.glyphs import render_glyph
from app.data_client import (
    kcc_stats,
    list_agents,
    list_assays_count,
    list_kccs,
    list_references_count,
)
from app.theme import HKCC_CSS

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)

kccs = list_kccs()
agents = list_agents()
stats = kcc_stats()

group1 = sum(1 for a in agents if a.get("iarc_group") == "1")

st.markdown('<span class="mono">Live · hKCC v0.1</span>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="h-display">A mechanistic atlas for the '
    '<em style="font-style:italic;color:#8B2E2A">14 key characteristics</em> '
    "of human carcinogens.</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="lede">hKCC is an open, curated database that organises mechanistic evidence '
    "linking known and suspected carcinogens to the key characteristics framework proposed by "
    "Smith et al. (2016) and extended in the years since.</p>",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Browse the KCCs →", type="primary"):
        st.switch_page("app/pages/2_Browse_KCCs.py")
with c2:
    if st.button("Open evidence matrix"):
        st.switch_page("app/pages/5_Evidence_Matrix.py")
with c3:
    if st.button("API & downloads"):
        st.switch_page("app/pages/8_API_Downloads.py")

stat_cols = st.columns(6)
for col, (val, label) in zip(
    stat_cols,
    [
        (len(kccs), "Key characteristics"),
        (len(agents), "Curated agents"),
        (group1, "IARC Group 1"),
        (list_assays_count(), "Mapped assays"),
        (list_references_count(), "Source references"),
        ("CC-BY", "License"),
    ],
):
    with col:
        st.markdown(f'<p class="brand-serif" style="font-size:2rem;margin:0">{val}</p>', unsafe_allow_html=True)
        st.caption(label)

st.markdown("---")
st.markdown("#### Fourteen key characteristics")
cols = st.columns(4)
for i, k in enumerate(kccs):
    s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
    with cols[i % 4]:
        with st.container(border=True):
            c_left, c_right = st.columns([1, 4])
            with c_left:
                render_glyph(k["icon"], size=22, color="#8B2E2A" if not k["is_extended"] else "#2D5959")
            with c_right:
                st.caption(f"{k['n']:02d}")
                st.markdown(f"**{k['title']}**")
                st.caption(f"{s['carc_count']} agents · {s['assay_count']} assays")
                if k["is_extended"]:
                    st.caption("New addition")
