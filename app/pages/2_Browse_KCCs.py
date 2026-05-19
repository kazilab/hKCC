"""Browse KCCs — mockup screens 2–3."""

import streamlit as st

from app.components.glyphs import render_glyph
from app.data_client import kcc_stats, list_kccs
from app.theme import HKCC_CSS

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)

kccs = list_kccs()
stats = kcc_stats()

st.markdown('<p class="mono">The framework</p>', unsafe_allow_html=True)
st.markdown('<h1 class="h-display" style="font-size:2rem">The 14 key characteristics</h1>', unsafe_allow_html=True)
st.caption(
    "Each KCC describes a distinct biological process consistently observed in established carcinogens."
)

filter_set = st.radio(
    "Filter",
    ["All", "Original 10", "New additions (4)"],
    horizontal=True,
    label_visibility="collapsed",
)
if filter_set == "Original 10":
    filtered = [k for k in kccs if not k["is_extended"]]
elif filter_set == "New additions (4)":
    filtered = [k for k in kccs if k["is_extended"]]
else:
    filtered = kccs

view = st.radio("View", ["Grid", "List"], horizontal=True, label_visibility="collapsed")

if view == "Grid":
    cols = st.columns(2)
    for i, k in enumerate(filtered):
        s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
        color = "#2D5959" if k["is_extended"] else "#8B2E2A"
        with cols[i % 2]:
            with st.container(border=True):
                g1, g2 = st.columns([1, 8])
                with g1:
                    render_glyph(k["icon"], size=26, color=color)
                with g2:
                    st.caption(f"KCC-{k['n']:02d}")
                    st.markdown(f"### {k['title']}")
                    st.write(k["description"])
                    st.caption(f"{s['carc_count']} agents · {s['assay_count']} assays")
                    if k["is_extended"]:
                        st.caption("Extended set")
else:
    rows = []
    for k in filtered:
        s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
        rows.append(
            {
                "ID": f"KCC-{k['n']:02d}",
                "Title": k["title"],
                "Short": k["short"],
                "Agents": s["carc_count"],
                "Assays": s["assay_count"],
                "Set": "Extended" if k["is_extended"] else "Original",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

# Detail panel
st.markdown("---")
st.subheader("KCC detail")
choice = st.selectbox(
    "Select a characteristic",
    options=filtered,
    format_func=lambda k: f"KCC-{k['n']:02d}: {k['title']}",
)
if choice:
    color = "#2D5959" if choice["is_extended"] else "#8B2E2A"
    c1, c2 = st.columns([1, 10])
    with c1:
        render_glyph(choice["icon"], size=32, color=color)
    with c2:
        st.markdown(f"## {choice['title']}")
        st.write(choice["description"])
        st.markdown("**Mechanism**")
        st.write(choice["mechanism"])
