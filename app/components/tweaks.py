"""Sidebar tweaks panel — theme, accent, density, serif, matrix style (mockup)."""

from __future__ import annotations

import streamlit as st

from app.theme import ACCENT_SWATCHES, MATRIX_STYLES, init_tweak_defaults


def render_tweaks_panel() -> None:
    init_tweak_defaults()
    with st.expander("Tweaks", expanded=False):
        st.caption("Appearance")
        theme = st.radio(
            "Theme",
            ["paper", "dark"],
            index=0 if st.session_state["hkcc_theme"] == "paper" else 1,
            horizontal=True,
            key="tweak_theme_radio",
        )
        if theme != st.session_state["hkcc_theme"]:
            st.session_state["hkcc_theme"] = theme
            st.query_params["theme"] = theme
            st.rerun()

        accent = st.radio(
            "Accent",
            ACCENT_SWATCHES,
            index=ACCENT_SWATCHES.index(st.session_state["hkcc_accent"])
            if st.session_state["hkcc_accent"] in ACCENT_SWATCHES
            else 0,
            horizontal=True,
            format_func=lambda c: "●",
            key="tweak_accent_radio",
        )
        st.session_state["hkcc_accent"] = accent

        st.session_state["hkcc_serif_headings"] = st.toggle(
            "Serif headings",
            value=st.session_state["hkcc_serif_headings"],
            key="tweak_serif_toggle",
        )

        st.caption("Layout")
        st.session_state["hkcc_density"] = st.radio(
            "Density",
            ["comfortable", "compact"],
            index=0 if st.session_state["hkcc_density"] == "comfortable" else 1,
            horizontal=True,
            key="tweak_density_radio",
        )

        st.caption("Evidence matrix")
        st.session_state["hkcc_matrix_style"] = st.radio(
            "Matrix style",
            MATRIX_STYLES,
            index=MATRIX_STYLES.index(st.session_state["hkcc_matrix_style"])
            if st.session_state["hkcc_matrix_style"] in MATRIX_STYLES
            else 0,
            horizontal=True,
            key="tweak_matrix_style_radio",
        )
