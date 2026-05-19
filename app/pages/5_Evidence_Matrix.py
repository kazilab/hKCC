"""Evidence matrix heatmap — mockup screen 6."""

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.components.matrix import render_matrix
from app.data_client import get_matrix, list_kccs
from app.theme import HKCC_CSS
from app.utils.evidence import ev_legend_html, kcc_coverage, total_evidence

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)

kccs = list_kccs()
matrix = get_matrix()

st.markdown('<p class="mono">Analyze</p>', unsafe_allow_html=True)
st.markdown('<h1 class="h-display" style="font-size:2rem">Evidence matrix · agents × KCCs</h1>', unsafe_allow_html=True)
st.caption("Rows are agents, columns are key characteristics. Cell values are curated 0–4 evidence scores.")

c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    sort_by = st.selectbox("Sort", ["name", "coverage", "weight"], format_func=lambda s: {"name": "A–Z", "coverage": "Coverage", "weight": "Evidence weight"}[s])
with c2:
    group_filter = st.selectbox("IARC group", ["all", "1", "2A", "2B"])
with c3:
    matrix_style = st.selectbox("Style", ["heatmap", "number", "dot"])

rows = matrix["rows"]
if group_filter != "all":
    rows = [r for r in rows if r.get("iarc_group") == group_filter]

if sort_by == "name":
    rows = sorted(rows, key=lambda r: r["agent_name"])
elif sort_by == "coverage":
    rows = sorted(rows, key=lambda r: kcc_coverage(r["scores"]), reverse=True)
else:
    rows = sorted(rows, key=lambda r: total_evidence(r["scores"]), reverse=True)

matrix_rows = [
    {"id": r["agent_id"], "name": r["agent_name"], "iarc_group": r.get("iarc_group"), "scores": r["scores"]}
    for r in rows
]

render_matrix(kccs, matrix_rows, matrix_style=matrix_style)
components.html(ev_legend_html(), height=40)

long_rows = []
for r in rows:
    for kid, score in r["scores"].items():
        long_rows.append({"agent": r["agent_id"], "kcc": kid, "evidence": score})
st.download_button("↓ Matrix CSV", pd.DataFrame(long_rows).to_csv(index=False), "hkcc_matrix.csv", "text/csv")
