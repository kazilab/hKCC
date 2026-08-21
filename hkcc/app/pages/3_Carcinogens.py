"""Browse carcinogens."""

import pandas as pd
import streamlit as st

from hkcc.app.components.agent_table import render_agent_table
from hkcc.app.components.card import card
from hkcc.app.components.embed import html_block
from hkcc.app.data_client import agents_with_evidence
from hkcc.app.page_shell import global_search_query, init_page
from hkcc.app.utils.evidence import count_at_least, ev_legend_html, kcc_coverage
from hkcc.db.evidence_rules import LABEL_OFFSET_SHORT

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
st.caption("Searchable list with mechanistic evidence across the ten KCCs. Click a row to open the profile.")

q_default = global_search_query()

with card("carcinogens-table"):
    c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
    with c1:
        q = st.text_input("Search", value=q_default, placeholder="Name, CAS, type…", label_visibility="collapsed")
        if q != q_default:
            st.query_params["q"] = q
            st.rerun()
    with c2:
        _groups = sorted({(a.get("iarc_group") or "—") for a in agents})
        group = st.selectbox(
            "IARC group",
            ["all", *_groups],
            format_func=lambda g: "All groups" if g == "all" else ("N/C" if g == "—" else f"Group {g}"),
            label_visibility="collapsed",
        )
    with c3:
        types = ["all"] + sorted({a["agent_type"] for a in agents})
        agent_type = st.selectbox("Type", types, format_func=lambda t: "All types" if t == "all" else t)
    with c4:
        sort = st.radio("Sort", ["name", "coverage", "substantial"], horizontal=True, label_visibility="collapsed")

_TRACKS = {"10yr-iarc": "10-yr retrospective (Vol 112–130)", "vol100-kc": "Volume 100 re-review"}
track_filter = st.selectbox(
    "Evidence source",
    ["all", *sorted({a.get("source_track") for a in agents if a.get("source_track")})],
    format_func=lambda s: "All sources" if s == "all" else _TRACKS.get(s, s),
    help=(
        "Scores are derived by different rules per source and are only comparable within one. "
        "Sorting by coverage or substantial evidence across sources compares different scales."
    ),
)

filtered = agents
if q:
    ql = q.lower()
    filtered = [
        a
        for a in filtered
        if ql in a["name"].lower() or ql in (a.get("cas") or "").lower() or ql in a["agent_type"].lower()
    ]
if group != "all":
    filtered = [a for a in filtered if (a.get("iarc_group") or "—") == group]
if agent_type != "all":
    filtered = [a for a in filtered if a["agent_type"] == agent_type]
if track_filter != "all":
    filtered = [a for a in filtered if a.get("source_track") == track_filter]

st.caption(LABEL_OFFSET_SHORT)

if sort in ("coverage", "substantial") and track_filter == "all":
    st.caption(
        "⚠ Sorting across both sources: a score of 3 means two of three model systems in the "
        "10-yr retrospective and two of four information sources in Volume 100."
    )

if sort == "name":
    filtered = sorted(filtered, key=lambda a: a["name"])
elif sort == "coverage":
    filtered = sorted(filtered, key=lambda a: kcc_coverage(a["evidence"]), reverse=True)
else:
    filtered = sorted(filtered, key=lambda a: count_at_least(a["evidence"], 3), reverse=True)

st.caption(f"Showing {len(filtered)} of {len(agents)} agents")

table_rows = []
for a in filtered:
    ev = a["evidence"]
    dirs = a.get("directions") or {}
    scores = [ev.get(kid) for kid in kcc_order]
    # Aligned with scores so the fingerprint can mark protective cells as ↓
    # rather than ordinary score-0 beige on the positive heat ramp.
    directions = [dirs.get(kid) for kid in kcc_order]
    table_rows.append(
        {
            "id": a["id"],
            "name": a["name"],
            "cas": a.get("cas") or "—",
            "agent_type": a["agent_type"],
            "iarc_group": a.get("iarc_group", "—"),
            "sites": a.get("sites", []),
            "scores": scores,
            "directions": directions,
            "evidence": ev,
        }
    )

render_agent_table(table_rows, kcc_shorts=shorts)
html_block(ev_legend_html())

exp1, exp2 = st.columns(2)
# A score without its direction and source is not interpretable, and this export
# carried neither — so a downloaded file could not distinguish a corroborated 3
# from one whose primary systems reported No, nor a 10-yr score from a Volume 100
# score on a different denominator.
export_df = pd.DataFrame(
    [
        {
            "id": a["id"],
            "name": a["name"],
            "cas": a.get("cas"),
            "iarc_group": a.get("iarc_group"),
            "source_track": a.get("source_track"),
            # blank, not 0, where the pair was never evaluated
            **{f"kcc_{k['n']:02d}": a["evidence"].get(k["id"], "") for k in kccs},
            **{
                f"kcc_{k['n']:02d}_direction": (a.get("directions") or {}).get(k["id"], "")
                if a["evidence"].get(k["id"]) is not None
                else ""
                for k in kccs
            },
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
