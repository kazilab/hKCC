"""Assays & methods library — mockup screen 7."""

import streamlit as st

from app.data_client import list_assays, list_kccs
from app.page_shell import global_search_query, init_page

init_page("assays")

all_assays = list_assays()
kccs = list_kccs()
kcc_by_id = {k["id"]: k for k in kccs}
q_default = global_search_query()

st.markdown('<p class="mono">Methods</p>', unsafe_allow_html=True)
st.markdown(
    f'<h1 class="h-display" style="font-size:2rem">Assays & methods ({len(all_assays)})</h1>',
    unsafe_allow_html=True,
)
st.caption("Standard wet-lab and high-throughput readouts mapped to one or more KCCs.")

c1, c2, c3 = st.columns(3)
with c1:
    q = st.text_input(
        "Search",
        value=q_default,
        placeholder="Search assays, targets, notes…",
        label_visibility="collapsed",
        key="assay_search",
    )
    if q != q_default:
        st.query_params["q"] = q
        st.rerun()
with c2:
    kcc_filter = st.selectbox(
        "KCC",
        ["all"] + [k["id"] for k in kccs],
        format_func=lambda x: "All KCCs" if x == "all" else f"KCC-{kcc_by_id[x]['n']:02d} · {kcc_by_id[x]['short']}",
    )
with c3:
    throughput_filter = st.selectbox("Throughput", ["all", "High", "Medium", "Low"])

filtered = all_assays
if q:
    ql = q.lower()
    filtered = [
        a
        for a in filtered
        if ql
        in " ".join(
            [
                a.get("name", ""),
                a.get("type", ""),
                a.get("target", ""),
                a.get("throughput", ""),
                a.get("oecd_tg", ""),
                a.get("notes", ""),
                " ".join(
                    f"KCC-{kcc_by_id[kid]['n']:02d} {kcc_by_id[kid]['short']}"
                    for kid in a.get("kcc_ids", [])
                    if kid in kcc_by_id
                ),
            ]
        ).lower()
    ]
if kcc_filter != "all":
    filtered = [a for a in filtered if kcc_filter in a.get("kcc_ids", [])]
if throughput_filter != "all":
    filtered = [a for a in filtered if a["throughput"] == throughput_filter]

st.caption(f"Showing {len(filtered)} / {len(all_assays)}")

cols = st.columns(2)
for i, a in enumerate(filtered):
    with cols[i % 2]:
        with st.container(border=True):
            st.markdown(f"### {a['name']}")
            st.caption(f"{a['type']} · {a['target']}")
            st.write(a.get("notes", ""))
            tags = []
            for kid in a.get("kcc_ids", []):
                k = kcc_by_id.get(kid)
                if k:
                    tags.append(f"KCC-{k['n']:02d} · {k['short']}")
            st.caption("Maps to: " + ", ".join(tags))
            if a.get("oecd_tg") and a["oecd_tg"] != "—":
                st.caption(a["oecd_tg"])
