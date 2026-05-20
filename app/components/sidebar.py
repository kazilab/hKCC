"""Custom sidebar nav — Browse / Analyze / Build (mockup Sidebar)."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import streamlit as st

from app.components.tweaks import render_tweaks_panel
from app.data_client import (
    list_agents,
    list_assays_count,
    list_kccs,
    list_references_count,
)
from app.theme import THEME
from db.config import get_settings

# (page_key, label, path, count_key or None)
_NAV: list[tuple[str | None, str, str | None, str | None]] = [
    (None, "Browse", None, None),
    ("overview", "Overview", "app/pages/1_Overview.py", None),
    ("kccs", "The 14 KCCs", "app/pages/2_Browse_KCCs.py", "kccs"),
    ("carcinogens", "Carcinogens", "app/pages/3_Carcinogens.py", "agents"),
    (None, "Analyze", None, None),
    ("matrix", "Evidence matrix", "app/pages/5_Evidence_Matrix.py", None),
    ("assays", "Assays & methods", "app/pages/6_Assays.py", "assays"),
    ("literature", "Literature", "app/pages/7_Literature.py", "literature"),
    (None, "Build", None, None),
    ("api", "Data & API", "app/pages/8_API_Downloads.py", None),
    ("live_feeds", "Live feeds", "app/pages/10_live_feeds.py", None),
    ("about", "About hKCC", "app/pages/9_About.py", None),
]


def _counts() -> dict[str, int]:
    try:
        return {
            "kccs": len(list_kccs()),
            "agents": len(list_agents()),
            "assays": list_assays_count(),
            "literature": list_references_count(),
        }
    except Exception:
        return {"kccs": 14, "agents": 26, "assays": 18, "literature": 10}


def render_sidebar() -> None:
    """Render brand, sectioned nav, and footer inside ``st.sidebar``."""
    active = st.session_state.get("hkcc_page", "overview")
    counts = _counts()
    tag = get_settings().hkcc_release_tag
    build = os.environ.get("HKCC_BUILD", "dev")

    accent = THEME["accent"]
    st.markdown(
        f'<p class="brand-serif" style="font-size:1.85rem;margin:0;line-height:1">'
        f'h<span style="color:{accent}">KCC</span></p>'
        f'<p class="mono" style="margin:4px 0 0;font-size:0.65rem;text-transform:none;'
        f'letter-spacing:0.02em">Key characteristics of human carcinogens</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    for sec_label, label, path, count_key in _NAV:
        if path is None:
            st.markdown(
                f'<p class="mono" style="margin:1rem 0 0.35rem;font-size:0.62rem">'
                f"{sec_label}</p>",
                unsafe_allow_html=True,
            )
            continue
        is_active = active == sec_label
        count = counts.get(count_key) if count_key else None
        btn_label = label if count is None else f"{label}  ({count})"
        if st.button(
            btn_label,
            key=f"nav_{sec_label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.switch_page(path)

    render_tweaks_panel()

    st.markdown("---")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    st.caption(f"v{tag} · build {build}")
    st.caption("Curated from IARC monographs and primary literature.")
    st.caption(f"Last sync · {today}")
