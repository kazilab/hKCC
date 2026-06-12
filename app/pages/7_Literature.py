"""Literature explorer."""

import streamlit as st

from app.components.ref_card import render_ref_cards
from app.data_client import list_literature_references
from app.page_shell import init_page

init_page("literature")

refs = list_literature_references()
tags = ["all"] + sorted({t for r in refs for t in r.get("tags", [])})

source_counts: dict[str, int] = {}
for r in refs:
    source_counts[r.get("source", "unknown")] = source_counts.get(r.get("source", "unknown"), 0) + 1

st.markdown('<p class="mono">Literature</p>', unsafe_allow_html=True)
st.markdown(
    f'<h1 class="h-display" style="font-size:2rem">Anchor references ({len(refs)})</h1>',
    unsafe_allow_html=True,
)
breakdown = " · ".join(f"{n} {src}" for src, n in sorted(source_counts.items()))
st.caption(f"Publications curators use when scoring evidence. {breakdown}")

years = [r["year"] for r in refs if r.get("year")]
if years:
    min_y, max_y = min(years), max(years)
    year_counts: dict[int, int] = {y: 0 for y in range(min_y, max_y + 1)}
    for y in years:
        year_counts[y] += 1
    max_c = max(year_counts.values()) or 1
    hist_cols = st.columns(min(len(year_counts), 12) or 1)
    for i, (y, c) in enumerate(year_counts.items()):
        with hist_cols[i % len(hist_cols)]:
            st.progress(c / max_c if max_c else 0)
            st.caption(str(y) if y % 5 == 0 or y == max_y else "")

c1, c2 = st.columns([3, 2])
with c1:
    tag_filter = st.radio("Tag", tags, horizontal=True)
with c2:
    source_options = ["all", *sorted(source_counts)]
    source_filter = st.selectbox(
        "Source",
        source_options,
        format_func=lambda s: "All sources" if s == "all" else f"{s} ({source_counts.get(s, 0)})",
    )

filtered = refs
if tag_filter != "all":
    filtered = [r for r in filtered if tag_filter in r.get("tags", [])]
if source_filter != "all":
    filtered = [r for r in filtered if r.get("source", "unknown") == source_filter]

st.caption(f"Showing {len(filtered)} references")

PAGE_SIZE = 30
if len(filtered) > PAGE_SIZE:
    n_pages = (len(filtered) - 1) // PAGE_SIZE + 1
    page = st.number_input("Page", min_value=1, max_value=n_pages, value=1, step=1, key="lit_page")
    start = (page - 1) * PAGE_SIZE
    page_rows = filtered[start : start + PAGE_SIZE]
    st.caption(f"Page {page}/{n_pages} · rows {start + 1}–{start + len(page_rows)}")
else:
    page_rows = filtered

render_ref_cards(page_rows)
