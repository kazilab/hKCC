"""Assays & methods library — mockup screen 7."""

import streamlit as st

from app.data_client import annotations_for_assay, list_assays, list_kccs
from app.page_shell import global_search_query, init_page

init_page("assays")

all_assays = list_assays()
kccs = list_kccs()
kcc_by_id = {k["id"]: k for k in kccs}
q_default = global_search_query()

source_counts: dict[str, int] = {}
for a in all_assays:
    source_counts[a.get("source", "mockup")] = source_counts.get(a.get("source", "mockup"), 0) + 1

st.markdown('<p class="mono">Methods</p>', unsafe_allow_html=True)
st.markdown(
    f'<h1 class="h-display" style="font-size:2rem">Assays & methods ({len(all_assays)})</h1>',
    unsafe_allow_html=True,
)
breakdown = " · ".join(f"{n} {src}" for src, n in sorted(source_counts.items()))
st.caption(f"Standard wet-lab and high-throughput readouts mapped to one or more KCCs. {breakdown}")

c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
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
    throughput_filter = st.selectbox("Throughput", ["all", "High", "Medium", "Low", "high", "medium", "low"])
with c4:
    source_options = ["all", *sorted(source_counts)]
    source_filter = st.selectbox(
        "Source",
        source_options,
        format_func=lambda s: "All sources" if s == "all" else f"{s} ({source_counts.get(s, 0)})",
    )

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
    filtered = [a for a in filtered if (a.get("throughput") or "").lower() == throughput_filter.lower()]
if source_filter != "all":
    filtered = [a for a in filtered if a.get("source", "mockup") == source_filter]

st.caption(f"Showing {len(filtered)} / {len(all_assays)}")

PAGE_SIZE = 60
if len(filtered) > PAGE_SIZE:
    n_pages = (len(filtered) - 1) // PAGE_SIZE + 1
    page = st.number_input("Page", min_value=1, max_value=n_pages, value=1, step=1)
    start = (page - 1) * PAGE_SIZE
    page_rows = filtered[start : start + PAGE_SIZE]
    st.caption(f"Page {page}/{n_pages} · rows {start + 1}–{start + len(page_rows)}")
else:
    page_rows = filtered

cols = st.columns(2)
for i, a in enumerate(page_rows):
    with cols[i % 2]:
        with st.container(border=True):
            chip = ""
            if a.get("source") and a["source"] != "mockup":
                chip = (
                    f' <span style="font-size:9px;padding:2px 6px;border:1px solid #aaa;'
                    f'border-radius:3px;color:#666;text-transform:uppercase">{a["source"]}</span>'
                )
            st.markdown(f"### {a['name']}{chip}", unsafe_allow_html=True)
            target = a.get("target") or "—"
            st.caption(f"{a['type']} · {target}")
            if a.get("notes"):
                st.write(a["notes"])
            tags = []
            for kid in a.get("kcc_ids", []):
                k = kcc_by_id.get(kid)
                if k:
                    tags.append(f"KCC-{k['n']:02d} · {k['short']}")
            if tags:
                st.caption("Maps to: " + ", ".join(tags))
            if a.get("oecd_tg") and a["oecd_tg"] != "—":
                st.caption(a["oecd_tg"])
            if a.get("source") == "kcad":
                with st.expander("KCAD study annotations"):
                    anns = annotations_for_assay(a["id"], limit=20)
                    if not anns:
                        st.caption("No annotations indexed yet.")
                    for ann in anns:
                        chem = ann.get("monograph_chem") or "—"
                        org = ann.get("organism") or "—"
                        tissue = ann.get("tissue") or "—"
                        cf = ann.get("cell_format") or "—"
                        st.markdown(
                            f"- **{chem}** · {org} · {tissue} · {cf}"
                            + (f" · ref `{ann['reference_id']}`" if ann.get("reference_id") else "")
                        )
