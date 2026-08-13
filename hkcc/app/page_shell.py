"""Shared page bootstrap: theme, topbar, active nav key."""

from __future__ import annotations

import streamlit as st

from hkcc.app.components.topbar import render_topbar
from hkcc.app.theme import apply_theme


def init_page(page_key: str) -> tuple[dict, dict[int, str]]:
    """Apply theme, set active sidebar page, render topbar. Returns (THEME, EV_COLORS)."""
    st.session_state["hkcc_page"] = page_key
    theme, ev = apply_theme()
    render_topbar(page_key)
    return theme, ev


def global_search_query() -> str:
    """Topbar search value synced via query param ``q``."""
    q = st.query_params.get("q", "")
    if isinstance(q, list):
        return q[0] if q else ""
    return q or ""
