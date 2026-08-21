"""Evidence matrix heatmap."""

import pandas as pd
import streamlit as st

from hkcc.app.components.embed import html_block
from hkcc.app.components.matrix import render_matrix, to_matrix_row
from hkcc.app.data_client import get_matrix, list_kccs
from hkcc.app.page_shell import init_page
from hkcc.app.theme import MATRIX_STYLES, get_matrix_style
from hkcc.app.utils.evidence import count_at_least, ev_legend_html, kcc_coverage
from hkcc.db.evidence_rules import LABEL_OFFSET_SHORT

init_page("matrix")
default_style = get_matrix_style()

kccs = list_kccs()
matrix = get_matrix()

st.markdown('<p class="mono">Analyze</p>', unsafe_allow_html=True)
st.markdown('<h1 class="h-display" style="font-size:2rem">Evidence matrix · agents × KCCs</h1>', unsafe_allow_html=True)
st.caption(
    "Rows are agents, columns are key characteristics. Cells carry a 0–4 score derived "
    "from published source tables; blank means the pair was never assessed."
)
st.info(
    "**Scores are comparable within a source, not across sources.** The 10-year retrospective "
    "counts three primary model systems; the Volume 100 re-review counts four information "
    "sources. No agent mixes the two, but a 3 does not mean the same thing in both — see the "
    "Methodology page. The downloadable CSV carries `source_track`, `direction`, "
    "`iarc_data_role` and `source_count` for every cell."
)

c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    sort_by = st.selectbox(
        "Sort",
        ["name", "coverage", "substantial"],
        format_func=lambda s: {"name": "A–Z", "coverage": "Coverage (≥2)", "substantial": "Substantial (≥3)"}[s],
    )
with c2:
    # Built from the data: a hard-coded list silently hid Group 3 and the
    # unclassified agents from this filter.
    _groups = sorted({(r.get("iarc_group") or "—") for r in matrix["rows"]})
    group_filter = st.selectbox(
        "IARC group",
        ["all", *_groups],
        format_func=lambda g: "All groups" if g == "all" else ("Not classified" if g == "—" else f"Group {g}"),
    )
with c3:
    style_index = MATRIX_STYLES.index(default_style) if default_style in MATRIX_STYLES else 0
    matrix_style = st.selectbox("Style", MATRIX_STYLES, index=style_index)
    if matrix_style != st.session_state.get("hkcc_matrix_style"):
        st.session_state["hkcc_matrix_style"] = matrix_style

rows = matrix["rows"]
if group_filter != "all":
    rows = [r for r in rows if (r.get("iarc_group") or "—") == group_filter]

if sort_by == "name":
    rows = sorted(rows, key=lambda r: r["agent_name"])
elif sort_by == "coverage":
    rows = sorted(rows, key=lambda r: kcc_coverage(r["scores"]), reverse=True)
else:
    rows = sorted(rows, key=lambda r: count_at_least(r["scores"], 3), reverse=True)

# Renames only, carrying every other field through: listing the keys by hand is
# what dropped `directions` and `data_roles` from the rendered heat map.
# Carcinogens warns when a cross-source sort is active; this page sorts the same
# way and said nothing. Sorting by coverage or substantial evidence over the
# whole matrix ranks 10-yr cells (3 model systems) against Volume 100 cells
# (4 information sources) as if the numbers were the same measurement.
if sort_by in ("coverage", "substantial") and len({t for r in rows for t in r.get("source_tracks", {}).values()}) > 1:
    st.caption(
        "⚠ Sorting across both sources: a score of 3 means two of three model systems in the "
        "10-yr retrospective and two of four information sources in Volume 100. Filter by "
        "IARC group or compare within a source before reading the order as a ranking."
    )

matrix_rows = [to_matrix_row(r) for r in rows]

render_matrix(kccs, matrix_rows, matrix_style=matrix_style)
html_block(ev_legend_html())
# Kept on every page that shows a score, not only Methodology: the offset
# is the single easiest thing to misread when comparing against the paper.
st.caption(LABEL_OFFSET_SHORT)

long_rows = []
for r in rows:
    directions = r.get("directions", {})
    tracks = r.get("source_tracks", {})
    roles = r.get("data_roles", {})
    counts = r.get("source_counts", {})
    for kid, score in r["scores"].items():
        count = counts.get(kid)
        long_rows.append(
            {
                "agent": r["agent_id"],
                "kcc": kid,
                "evidence": score,
                # A score is only comparable within its track, and only
                # interpretable together with its direction.
                "direction": directions.get(kid, "positive"),
                "source_track": tracks.get(kid, ""),
                # "Not used" means the IARC working group did not use this data
                # in its evaluation, even where the score is 3 or 4. The export
                # is what gets cited, so the caveat travels with it.
                "iarc_data_role": roles.get(kid, ""),
                # Raw count behind the score (3 systems / 4 sources). Empty when
                # the cell was scored from a strength label rather than a count.
                "source_count": "" if count is None else count,
            }
        )
st.download_button("↓ Matrix CSV", pd.DataFrame(long_rows).to_csv(index=False), "hkcc_matrix.csv", "text/csv")
