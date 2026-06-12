"""Sidebar tweaks panel: theme, accent, density, serif, matrix style."""

from __future__ import annotations

import streamlit as st

from app.theme import ACCENT_SWATCHES, MATRIX_STYLES, init_tweak_defaults


def _render_accent_swatches() -> None:
    """Colored swatches for accent picker (replaces identical-bullet radio)."""
    prev_accent = st.session_state["hkcc_accent"]
    selected_idx = (
        ACCENT_SWATCHES.index(prev_accent) + 1
        if prev_accent in ACCENT_SWATCHES
        else 1
    )

    swatch_css_parts = [
        # Shape every swatch button as a small circle, hide its label.
        '.st-key-hkcc-accent-row div[data-testid="stButton"] > button {'
        " width:28px!important; height:28px!important; min-height:28px!important;"
        " padding:0!important; border-radius:999px!important;"
        " color:transparent!important; margin:0 auto;"
        " transition:transform 0.12s ease, box-shadow 0.12s ease; }",
        '.st-key-hkcc-accent-row div[data-testid="stButton"] > button:hover {'
        " transform:scale(1.08); }",
        # Ring around the currently-selected swatch.
        f'.st-key-hkcc-accent-row div[data-testid="column"]:nth-of-type({selected_idx})'
        ' div[data-testid="stButton"] > button {'
        " box-shadow:0 0 0 2px var(--paper-2),0 0 0 4px var(--ink)!important; }",
    ]
    for i, hex_color in enumerate(ACCENT_SWATCHES, start=1):
        swatch_css_parts.append(
            f'.st-key-hkcc-accent-row div[data-testid="column"]:nth-of-type({i})'
            ' div[data-testid="stButton"] > button {'
            f" background:{hex_color}!important; border-color:{hex_color}!important; }}"
        )
    st.markdown("<style>" + "".join(swatch_css_parts) + "</style>", unsafe_allow_html=True)

    st.caption("Accent")
    with st.container(key="hkcc-accent-row"):
        cols = st.columns(len(ACCENT_SWATCHES))
        for i, hex_color in enumerate(ACCENT_SWATCHES):
            if cols[i].button(
                " ",
                key=f"tweak_accent_btn_{i}",
                help=hex_color,
                use_container_width=True,
            ):
                if hex_color != prev_accent:
                    st.session_state["hkcc_accent"] = hex_color
                    st.rerun()


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

        _render_accent_swatches()

        prev_serif = st.session_state["hkcc_serif_headings"]
        serif = st.toggle(
            "Serif headings",
            value=prev_serif,
            key="tweak_serif_toggle",
        )
        st.session_state["hkcc_serif_headings"] = serif
        if serif != prev_serif:
            st.rerun()

        st.caption("Layout")
        prev_density = st.session_state["hkcc_density"]
        density = st.radio(
            "Density",
            ["comfortable", "compact"],
            index=0 if prev_density == "comfortable" else 1,
            horizontal=True,
            key="tweak_density_radio",
        )
        st.session_state["hkcc_density"] = density
        if density != prev_density:
            st.rerun()

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
