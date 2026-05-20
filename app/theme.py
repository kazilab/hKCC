"""Dark editorial theme for Streamlit (matches mockup [data-theme=dark])."""

# Evidence ramp 0–4 (dark)
EV_COLORS: dict[int, str] = {
    0: "#2A2620",
    1: "#5C4A2A",
    2: "#8C6940",
    3: "#B25A35",
    4: "#D85040",
}

THEME = {
    "paper": "#14120E",
    "paper2": "#1C1A14",
    "paper3": "#24211A",
    "ink": "#F0EBE0",
    "ink2": "#D6D0C2",
    "muted": "#9C9586",
    "rule": "#2A2620",
    "accent": "#C25450",
    "teal": "#5A9E9E",
}

HKCC_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&family=Public+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap');

:root {{
  --paper: {THEME["paper"]};
  --paper-2: {THEME["paper2"]};
  --paper-3: {THEME["paper3"]};
  --ink: {THEME["ink"]};
  --ink-2: {THEME["ink2"]};
  --muted: {THEME["muted"]};
  --rule: {THEME["rule"]};
  --accent: {THEME["accent"]};
  --teal: {THEME["teal"]};
}}

/* Streamlit shell */
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

[data-testid="stSidebar"] * {{
  color: var(--ink) !important;
}}

section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stCaption,
[data-testid="stMain"] .stMarkdown p,
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
[data-testid="stMain"] h4, [data-testid="stMain"] label,
[data-testid="stMain"] span, [data-testid="stMain"] div {{
  color: var(--ink);
}}

[data-testid="stMain"] .stCaption, .mono, .lede {{
  color: var(--muted) !important;
}}

.lede {{ color: var(--ink-2) !important; }}

/* Cards, expanders, containers */
[data-testid="stVerticalBlockBorderWrapper"] {{
  background-color: var(--paper-2) !important;
  border-color: var(--rule) !important;
}}

div[data-testid="stExpander"] {{
  background-color: var(--paper-2) !important;
  border-color: var(--rule) !important;
}}

div[data-testid="stExpander"] summary {{
  color: var(--ink) !important;
}}

/* Inputs */
.stTextInput input, .stSelectbox > div > div, .stMultiSelect > div > div,
.stNumberInput input, textarea {{
  background-color: var(--paper-3) !important;
  color: var(--ink) !important;
  border-color: var(--rule) !important;
}}

/* Dataframe */
[data-testid="stDataFrame"] {{
  background-color: var(--paper-2) !important;
}}

[data-testid="stDataFrame"] div {{
  color: var(--ink) !important;
}}

/* Buttons */
div[data-testid="stButton"] > button {{
  background-color: var(--paper-3) !important;
  color: var(--ink) !important;
  border-color: var(--rule) !important;
}}

div[data-testid="stButton"] > button:hover {{
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}}

div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {{
  background-color: var(--accent) !important;
  color: #fff !important;
  border-color: var(--accent) !important;
}}

/* Tabs, radio, metrics */
.stTabs [data-baseweb="tab-list"] {{
  background-color: transparent !important;
}}

.stTabs [data-baseweb="tab"] {{
  color: var(--muted) !important;
}}

.stTabs [aria-selected="true"] {{
  color: var(--ink) !important;
  border-color: var(--accent) !important;
}}

[data-testid="stMetricValue"] {{
  color: var(--ink) !important;
}}

[data-testid="stMetricLabel"] {{
  color: var(--muted) !important;
}}

/* Alerts */
[data-testid="stAlert"] {{
  background-color: var(--paper-3) !important;
  color: var(--ink) !important;
  border-color: var(--rule) !important;
}}

/* Nav pages */
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNav"] span {{
  color: var(--ink-2) !important;
}}

[data-testid="stSidebarNav"] a[aria-current="page"] {{
  color: var(--ink) !important;
  background-color: var(--paper-3) !important;
}}

/* Custom typography */
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

.stat-row {{
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1rem;
  margin: 2rem 0;
}}

.stat .v {{ font-family: "Instrument Serif", serif; font-size: 2rem; color: var(--ink); }}
.stat .l {{ font-size: 0.75rem; color: var(--muted); }}

.kcc-card {{
  background: var(--paper-2);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 1rem;
}}

.hkcc-footer {{
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--rule);
  font-size: 0.8rem;
  color: var(--muted);
}}

/* iframe components sit on dark surround */
iframe {{
  background: var(--paper-2) !important;
}}
"""
