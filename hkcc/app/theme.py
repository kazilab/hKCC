"""hKCC themes: paper (default) and dark."""

from __future__ import annotations

import streamlit as st

# --- Palette definitions -------------------------------------------------------

PAPER_THEME: dict[str, str] = {
    "paper": "#F7F4ED",
    "paper2": "#FFFFFF",
    "paper3": "#EFE9DC",
    "ink": "#1F1B14",
    "ink2": "#3A342A",
    "muted": "#6B6354",  # AA on paper/paper2/paper3 (5.40/5.94/4.91)
    "rule": "#E2DBC9",
    "accent": "#8B2E2A",
    "teal": "#2D5959",
}

PAPER_EV: dict[int, str] = {
    0: "#EFE9DC",
    1: "#E6C9A8",
    2: "#D69A6B",
    3: "#B36344",
    4: "#8B2E2A",
}

DARK_THEME: dict[str, str] = {
    "paper": "#14120E",
    "paper2": "#1C1A14",
    "paper3": "#24211A",
    "ink": "#F0EBE0",
    "ink2": "#D6D0C2",
    "muted": "#9C9586",
    "rule": "#2A2620",
    "accent": "#D97570",  # AA on paper/paper2/paper3 (5.99/5.57/5.15)
    "teal": "#5A9E9E",
}

DARK_EV: dict[int, str] = {
    0: "#2A2620",
    1: "#5C4A2A",
    2: "#8C6940",
    3: "#B25A35",
    4: "#D85040",
}

# Active palette (updated by apply_theme on each rerun)
THEME: dict[str, str] = dict(PAPER_THEME)
EV_COLORS: dict[int, str] = dict(PAPER_EV)
HKCC_CSS: str = ""

ACCENT_SWATCHES = ["#8B2E2A", "#2D5959", "#1E3A8A", "#7A4019"]
MATRIX_STYLES = ["heatmap", "dot", "bar", "number"]


def init_tweak_defaults() -> None:
    """Session defaults for sidebar tweaks (P2-3)."""
    st.session_state.setdefault("hkcc_theme", "paper")
    st.session_state.setdefault("hkcc_accent", ACCENT_SWATCHES[0])
    st.session_state.setdefault("hkcc_density", "comfortable")
    st.session_state.setdefault("hkcc_serif_headings", True)
    st.session_state.setdefault("hkcc_matrix_style", "heatmap")


def _apply_tweak_overrides(base: dict[str, str]) -> dict[str, str]:
    t = dict(base)
    accent = st.session_state.get("hkcc_accent")
    if accent:
        t["accent"] = accent
    return t


def _tweak_extra_css() -> str:
    density = st.session_state.get("hkcc_density", "comfortable")
    serif = st.session_state.get("hkcc_serif_headings", True)
    parts = []
    if density == "compact":
        parts.append(
            """
[data-testid="stMain"] .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
[data-testid="stVerticalBlockBorderWrapper"], [class*="st-key-hkcc-card"] { padding: 0.5rem !important; }
div[data-testid="stButton"] button { padding: 0.25rem 0.5rem !important; }
"""
        )
    if not serif:
        parts.append(
            """
.h-display, .brand-serif { font-family: "Public Sans", system-ui, sans-serif !important; }
"""
        )
    return "\n".join(parts)


def _build_css(t: dict[str, str], *, hide_nav: bool = True) -> str:
    nav_hide = (
        "[data-testid='stSidebarNav'] { display: none !important; }\n"
        if hide_nav
        else ""
    )
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&family=Public+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap');

:root {{
  --paper: {t["paper"]};
  --paper-2: {t["paper2"]};
  --paper-3: {t["paper3"]};
  --ink: {t["ink"]};
  --ink-2: {t["ink2"]};
  --muted: {t["muted"]};
  --rule: {t["rule"]};
  --accent: {t["accent"]};
  --teal: {t["teal"]};
}}

.stApp, [data-testid="stAppViewContainer"], .main, [data-testid="stMain"] {{
  background-color: var(--paper) !important;
  color: var(--ink) !important;
}}

[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {{
  background-color: var(--paper) !important;
}}

[data-testid="stSidebar"], [data-testid="stSidebar"] > div {{
  background-color: var(--paper-2) !important;
  border-right: 1px solid var(--rule);
}}

[data-testid="stSidebar"] * {{ color: var(--ink) !important; }}

section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stCaption,
[data-testid="stMain"] .stMarkdown p,
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
[data-testid="stMain"] h4, [data-testid="stMain"] label,
[data-testid="stMain"] span, [data-testid="stMain"] div {{
  color: var(--ink);
}}

[data-testid="stMain"] .stCaption, .mono, .lede {{ color: var(--muted) !important; }}
.lede {{ color: var(--ink-2) !important; }}

/* Cards. A bordered container has no test id of its own — the border is a
   styled-component prop — so cards are addressed through the `st-key-` class
   Streamlit derives from their key; see components/card.py. The wrapper test id
   is kept for Streamlit <= 1.4x (the requirements floor), where it still
   exists and this one does the work. */
[data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-hkcc-card"] {{
  background-color: var(--paper-2) !important;
  border-color: var(--rule) !important;
}}

div[data-testid="stExpander"] {{
  background-color: var(--paper-2) !important;
  border-color: var(--rule) !important;
}}
div[data-testid="stExpander"] summary {{ color: var(--ink) !important; }}

.stTextInput input, .stSelectbox > div > div, .stMultiSelect > div > div,
.stNumberInput input, textarea {{
  background-color: var(--paper-3) !important;
  color: var(--ink) !important;
  border-color: var(--rule) !important;
}}

[data-testid="stDataFrame"] {{ background-color: var(--paper-2) !important; }}
[data-testid="stDataFrame"] div {{ color: var(--ink) !important; }}

/* Descendant, not direct child: a button carrying `help=` is wrapped in a
   tooltip host, which breaks `> button`. The primary rule lists both the
   historical and the current base-button test ids. */
div[data-testid="stButton"] button {{
  background-color: var(--paper-3) !important;
  color: var(--ink) !important;
  border-color: var(--rule) !important;
}}
div[data-testid="stButton"] button:hover {{
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}}
div[data-testid="stButton"] button[kind="primary"],
div[data-testid="stButton"] button[data-testid="baseButton-primary"],
div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {{
  background-color: var(--accent) !important;
  color: #fff !important;
  border-color: var(--accent) !important;
}}

.stTabs [data-baseweb="tab-list"] {{ background-color: transparent !important; }}
.stTabs [data-baseweb="tab"] {{ color: var(--muted) !important; }}
.stTabs [aria-selected="true"] {{
  color: var(--ink) !important;
  border-color: var(--accent) !important;
}}

[data-testid="stMetricValue"] {{ color: var(--ink) !important; }}
[data-testid="stMetricLabel"] {{ color: var(--muted) !important; }}

[data-testid="stAlert"] {{
  background-color: var(--paper-3) !important;
  color: var(--ink) !important;
  border-color: var(--rule) !important;
}}

{nav_hide}

.brand-serif {{
  font-family: "Instrument Serif", "Times New Roman", serif !important;
  letter-spacing: -0.02em;
  color: var(--ink) !important;
}}
.mono {{
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted) !important;
}}
.h-display {{
  font-family: "Instrument Serif", serif;
  font-size: 2.6rem;
  line-height: 1.05;
  font-weight: 400;
  color: var(--ink) !important;
}}
.eyebrow {{
  font-family: "JetBrains Mono", monospace;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}}
.hkcc-topbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0 1.25rem;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 1rem;
}}
.hkcc-crumbs {{
  font-family: "JetBrains Mono", monospace;
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}}
.hkcc-crumbs .here {{ color: var(--ink); }}
.hkcc-crumbs .sep {{ margin: 0 0.35rem; opacity: 0.5; }}
iframe {{ background: var(--paper-2) !important; }}
"""


def get_theme(name: str) -> tuple[dict[str, str], str, dict[int, str]]:
    if name == "dark":
        t = DARK_THEME
        ev = DARK_EV
    else:
        t = PAPER_THEME
        ev = PAPER_EV
    theme = dict(t)
    return theme, _build_css(theme), dict(ev)


def resolve_theme() -> str:
    qp = st.query_params.get("theme", "")
    if isinstance(qp, list):
        qp = qp[0] if qp else ""
    if qp in ("paper", "dark"):
        st.session_state["hkcc_theme"] = qp
    return st.session_state.get("hkcc_theme", "paper")


def apply_theme(*, inject: bool = True) -> tuple[dict[str, str], dict[int, str]]:
    """Resolve theme, update module globals, inject CSS. Call once per page rerun."""
    global THEME, EV_COLORS, HKCC_CSS
    init_tweak_defaults()
    name = resolve_theme()
    base_theme, _, ev = get_theme(name)
    theme = _apply_tweak_overrides(base_theme)
    css = _build_css(theme)
    css = css + _tweak_extra_css()
    THEME.clear()
    THEME.update(theme)
    EV_COLORS.clear()
    EV_COLORS.update(ev)
    HKCC_CSS = css
    if inject:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    return theme, ev


def get_matrix_style() -> str:
    init_tweak_defaults()
    style = st.session_state.get("hkcc_matrix_style", "heatmap")
    return style if style in MATRIX_STYLES else "heatmap"
