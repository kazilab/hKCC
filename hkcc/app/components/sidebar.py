"""Custom sidebar nav: Browse / Analyze / Build."""

from __future__ import annotations

import os

import streamlit as st

from hkcc.app.components.tweaks import render_tweaks_panel
from hkcc.app.data_client import (
    list_agents,
    list_assays_count,
    list_kccs,
    list_references_count,
)
from hkcc.app.theme import THEME
from hkcc.db.config import APP_CONTACT_EMAIL, APP_DEVELOPER, get_settings

# (page_key, label, path, count_key or None)
_NAV: list[tuple[str | None, str, str | None, str | None]] = [
    (None, "Browse", None, None),
    ("overview", "Overview", "app/pages/1_Overview.py", None),
    ("kccs", "The 10 KCCs", "app/pages/2_Browse_KCCs.py", "kccs"),
    ("carcinogens", "Carcinogens", "app/pages/3_Carcinogens.py", "agents"),
    (None, "Analyze", None, None),
    ("matrix", "Evidence matrix", "app/pages/5_Evidence_Matrix.py", None),
    ("iarc_matrix", "IARC monograph matrix", "app/pages/9b_IARC_Matrix.py", None),
    ("assays", "Assays & methods", "app/pages/6_Assays.py", "assays"),
    ("literature", "Literature", "app/pages/7_Literature.py", "literature"),
    (None, "Build", None, None),
    ("api", "Data & API", "app/pages/8_API_Downloads.py", None),
    ("methodology", "Methodology", "app/pages/9a_Methodology.py", None),
    ("about", "About hKCC", "app/pages/9_About.py", None),
]


def _counts() -> dict[str, int | None]:
    """Live counts for the nav badges.

    On failure every count is ``None`` and the badge is simply omitted. The
    previous fallback returned plausible-looking constants, so a broken database
    produced a sidebar full of numbers that were quietly wrong.
    """
    try:
        return {
            "kccs": len(list_kccs()),
            "agents": len(list_agents()),
            "assays": list_assays_count(),
            "literature": list_references_count(),
        }
    except Exception:  # noqa: BLE001 — the nav must render even with no data
        return {"kccs": None, "agents": None, "assays": None, "literature": None}


def render_sidebar() -> None:
    """Render brand, sectioned nav, and footer inside ``st.sidebar``."""
    active = st.session_state.get("hkcc_page", "overview")
    counts = _counts()
    tag = get_settings().release_tag
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

    for page_key, label, path, count_key in _NAV:
        if path is None:
            # Section divider: its page key is None and the heading is the label.
            st.markdown(
                f'<p class="mono" style="margin:1rem 0 0.35rem;font-size:0.62rem">'
                f"{label}</p>",
                unsafe_allow_html=True,
            )
            continue
        is_active = active == page_key
        count = counts.get(count_key) if count_key else None
        btn_label = label if count is None else f"{label}  ({count})"
        if st.button(
            btn_label,
            key=f"nav_{page_key}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.switch_page(path)

    render_tweaks_panel()

    st.markdown("---")
    st.caption(f"v{tag} · build {build}")
    st.caption(APP_DEVELOPER)
    st.caption(APP_CONTACT_EMAIL)
    st.caption("Derived from IARC monographs and the published source datasets.")
