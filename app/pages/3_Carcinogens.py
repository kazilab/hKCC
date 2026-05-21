"""Browse carcinogens — mockup screens 4–5 (list)."""

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.components.agent_table import render_agent_table
from app.data_client import agents_with_evidence
from app.page_shell import global_search_query, init_page
from app.utils.evidence import ev_legend_html, kcc_coverage, total_evidence

THEME, _ = init_page("carcinogens")

# Row click via query param
if st.query_params.get("agent_id"):
    st.session_state["agent_id"] = st.query_params["agent_id"]
    st.switch_page("app/pages/4_Agent_Detail.py")

agents, kccs = agents_with_evidence()
kcc_order = [k["id"] for k in kccs]
shorts = [k["short"] for k in kccs]

st.markdown('<p class="mono">The database</p>', unsafe_allow_html=True)
st.markdown(
    f'<h1 class="h-display" style="font-size:2rem">Carcinogens & suspect agents ({len(agents)})</h1>',
    unsafe_allow_html=True,
)
st.caption("Searchable curated list with mechanistic evidence across 14 KCCs. Click a row to open the profile.")

q_default = global_search_query()

with st.container(border=True):
    c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
    with c1:
        q = st.text_input("Search", value=q_default, placeholder="Name, CAS, type…", label_visibility="collapsed")
        if q != q_default:
            st.query_params["q"] = q
            st.rerun()
    with c2:
        group = st.selectbox(
            "IARC group",
            ["all", "1", "2A", "2B", "—"],
            format_func=lambda g: "All groups" if g == "all" else ("N/C" if g == "—" else f"Group {g}"),
            label_visibility="collapsed",
        )
    with c3:
        types = ["all"] + sorted({a["agent_type"] for a in agents})
        agent_type = st.selectbox("Type", types, format_func=lambda t: "All types" if t == "all" else t)
    with c4:
        sort = st.radio("Sort", ["name", "coverage", "weight"], horizontal=True, label_visibility="collapsed")

filtered = agents
if q:
    ql = q.lower()
    filtered = [
        a
        for a in filtered
        if ql in a["name"].lower()
        or ql in (a.get("cas") or "").lower()
        or ql in a["agent_type"].lower()
    ]
if group != "all":
    filtered = [a for a in filtered if (a.get("iarc_group") or "—") == group]
if agent_type != "all":
    filtered = [a for a in filtered if a["agent_type"] == agent_type]

if sort == "name":
    filtered = sorted(filtered, key=lambda a: a["name"])
elif sort == "coverage":
    filtered = sorted(filtered, key=lambda a: kcc_coverage(a["evidence"]), reverse=True)
else:
    filtered = sorted(filtered, key=lambda a: total_evidence(a["evidence"]), reverse=True)

st.caption(f"Showing {len(filtered)} of {len(agents)} agents")

table_rows = []
for a in filtered:
    ev = a["evidence"]
    scores = [ev.get(kid, 0) for kid in kcc_order]
    table_rows.append(
        {
            "id": a["id"],
            "name": a["name"],
            "cas": a.get("cas", "—"),
            "agent_type": a["agent_type"],
            "iarc_group": a.get("iarc_group", "—"),
            "sites": a.get("sites", []),
            "scores": scores,
            "evidence": ev,
        }
    )

render_agent_table(table_rows, kcc_shorts=shorts)
components.html(ev_legend_html(), height=40)

exp1, exp2 = st.columns(2)
export_df = pd.DataFrame(
    [
        {
            "id": a["id"],
            "name": a["name"],
            "cas": a.get("cas"),
            "iarc_group": a.get("iarc_group"),
            **{f"kcc_{k['n']:02d}": a["evidence"].get(k["id"], 0) for k in kccs},
        }
        for a in filtered
    ]
)
with exp1:
    st.download_button("↓ Export CSV", export_df.to_csv(index=False), "hkcc_agents.csv", "text/csv")
with exp2:
    st.download_button(
        "↓ JSON",
        export_df.to_json(orient="records", indent=2),
        "hkcc_agents.json",
        "application/json",
    )
