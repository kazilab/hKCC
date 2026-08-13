"""Topbar with breadcrumbs and a cross-page search filter."""

from __future__ import annotations

import streamlit as st

BREADCRUMBS: dict[str, list[str]] = {
    "overview": ["Overview"],
    "kccs": ["Browse", "The 10 KCCs"],
    "kcc_detail": ["Browse", "The 10 KCCs", "Detail"],
    "carcinogens": ["Browse", "Carcinogens"],
    "agent_detail": ["Browse", "Carcinogens", "Profile"],
    "matrix": ["Analyze", "Evidence matrix"],
    "assays": ["Analyze", "Assays & methods"],
    "literature": ["Analyze", "Literature"],
    "api": ["Build", "Data & API"],
    "live_feeds": ["Build", "Live feeds"],
    "about": ["About"],
    "methodology": ["About", "Methodology"],
    "iarc_matrix": ["Analyze", "IARC Monograph matrix"],
}


# Pages with their own search input. Rendering the topbar search as well put two
# keyed widgets on one page, both bound to the `q` query parameter and both
# calling st.rerun() when their value differed from it — so each rerun restored
# the other's stale value and triggered another rerun. Typing in either box
# looped until the user navigated away.
PAGES_WITH_OWN_SEARCH = frozenset({"kccs", "carcinogens", "assays"})


def render_topbar(page_key: str) -> None:
    crumbs = list(BREADCRUMBS.get(page_key, ["—"]))
    if page_key == "kcc_detail" and st.session_state.get("hkcc_detail_title"):
        crumbs[-1] = str(st.session_state["hkcc_detail_title"])[:48]
    parts = []
    for i, c in enumerate(crumbs):
        if i:
            parts.append('<span class="sep">/</span>')
        cls = "here" if i == len(crumbs) - 1 else ""
        parts.append(f'<span class="{cls}">{c}</span>')
    crumb_html = "".join(parts)

    q = st.query_params.get("q", "")
    if isinstance(q, list):
        q = q[0] if q else ""
    search_val = q or ""

    show_search = page_key not in PAGES_WITH_OWN_SEARCH
    if not show_search:
        st.markdown(
            f'<div class="hkcc-topbar" style="border:none;padding:0;margin:0">'
            f'<div class="hkcc-crumbs">{crumb_html}</div></div>',
            unsafe_allow_html=True,
        )
        return

    col_crumb, col_search = st.columns([2, 1])
    with col_crumb:
        st.markdown(
            f'<div class="hkcc-topbar" style="border:none;padding:0;margin:0">'
            f'<div class="hkcc-crumbs">{crumb_html}</div></div>',
            unsafe_allow_html=True,
        )
    with col_search:
        new_q = st.text_input(
            "Search",
            value=search_val,
            placeholder="Search carcinogens, KCCs, assays…",
            label_visibility="collapsed",
            key=f"topbar_search_{page_key}",
        )
        st.caption("Filters Overview, KCCs, Carcinogens and Assays")
        if new_q != search_val:
            st.query_params["q"] = new_q
