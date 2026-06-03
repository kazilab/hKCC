"""Browse KCCs."""

import streamlit as st

from app.components.glyphs import render_glyph
from app.data_client import kcc_stats, list_kccs
from app.page_shell import global_search_query, init_page

THEME, _ = init_page("kccs")

if st.query_params.get("kcc_id"):
    st.session_state["kcc_id"] = st.query_params["kcc_id"]
    st.switch_page("app/pages/2a_KCC_Detail.py")

kccs = list_kccs()
stats = kcc_stats()
q_default = global_search_query()

st.markdown('<p class="mono">The framework</p>', unsafe_allow_html=True)
st.markdown('<h1 class="h-display" style="font-size:2rem">The 14 key characteristics</h1>', unsafe_allow_html=True)
st.caption(
    "Each KCC describes a distinct biological process consistently observed in established carcinogens."
)

q = st.text_input(
    "Search KCCs",
    value=q_default,
    placeholder="Search title, short label, mechanism…",
    label_visibility="collapsed",
    key="kcc_search",
)
if q != q_default:
    st.query_params["q"] = q
    st.rerun()

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

if q:
    ql = q.lower()
    filtered = [
        k
        for k in filtered
        if ql in k["title"].lower()
        or ql in k["short"].lower()
        or ql in k.get("description", "").lower()
        or ql in k.get("mechanism", "").lower()
    ]

if not filtered:
    st.info("No KCCs match the current filters.")
    st.stop()

view = st.radio("View", ["Grid", "List"], horizontal=True, label_visibility="collapsed")

if view == "Grid":
    cols = st.columns(2)
    for i, k in enumerate(filtered):
        s = stats.get(k["id"], {"carc_count": 0, "assay_count": 0})
        color = THEME["teal"] if k["is_extended"] else THEME["accent"]
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
                    if st.button("Open detail →", key=f"kcc_open_{k['id']}", use_container_width=True):
                        st.session_state["kcc_id"] = k["id"]
                        st.query_params["kcc_id"] = k["id"]
                        st.switch_page("app/pages/2a_KCC_Detail.py")
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
    pick = st.selectbox(
        "Open KCC detail",
        options=filtered,
        format_func=lambda k: f"KCC-{k['n']:02d}: {k['title']}",
    )
    if pick and st.button("View KCC detail →", type="primary"):
        st.session_state["kcc_id"] = pick["id"]
        st.query_params["kcc_id"] = pick["id"]
        st.switch_page("app/pages/2a_KCC_Detail.py")
