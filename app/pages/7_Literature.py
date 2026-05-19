"""Literature explorer — mockup screen 8."""

import streamlit as st

from app.data_client import list_references
from app.theme import HKCC_CSS

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)

refs = list_references()
tags = ["all"] + sorted({t for r in refs for t in r.get("tags", [])})

st.markdown('<p class="mono">Literature</p>', unsafe_allow_html=True)
st.markdown(
    f'<h1 class="h-display" style="font-size:2rem">Anchor references ({len(refs)})</h1>',
    unsafe_allow_html=True,
)
st.caption("Publications curators use when scoring evidence.")

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

tag_filter = st.radio("Tag", tags, horizontal=True)
filtered = refs if tag_filter == "all" else [r for r in refs if tag_filter in r.get("tags", [])]

for ref in filtered:
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"**{ref.get('year', '—')}** · {ref['title']}")
            st.caption(f"{ref['authors']} · _{ref['journal']}_ · {ref.get('vol', '')}")
            if ref.get("doi") and ref["doi"] != "—":
                st.markdown(f"[DOI](https://doi.org/{ref['doi'].replace('https://doi.org/', '')})")
        with c2:
            if ref.get("tags"):
                st.caption(", ".join(ref["tags"]))
            st.caption(f"{ref.get('citations', 0)} citations")
