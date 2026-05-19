"""Inject mockup design tokens into Streamlit."""

HKCC_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&family=Public+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap');

:root {
  --paper: #F7F4ED;
  --paper-2: #EFEADD;
  --ink: #1A1815;
  --muted: #6B6557;
  --rule: #DDD6C5;
  --accent: #8B2E2A;
  --teal: #2D5959;
  --ev-0: #ECE5D2;
  --ev-1: #E6C98A;
  --ev-2: #D89759;
  --ev-3: #B25A35;
  --ev-4: #7A1F1F;
}

html, body, [data-testid="stAppViewContainer"] {
  background-color: var(--paper) !important;
  color: var(--ink);
  font-family: "Public Sans", system-ui, sans-serif;
}

[data-testid="stSidebar"] {
  background-color: var(--paper-2) !important;
  border-right: 1px solid var(--rule);
}

[data-testid="stSidebar"] h1, .brand-serif {
  font-family: "Instrument Serif", "Times New Roman", serif !important;
  letter-spacing: -0.02em;
}

.mono {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.h-display {
  font-family: "Instrument Serif", serif;
  font-size: 2.6rem;
  line-height: 1.05;
  font-weight: 400;
}

.lede { font-size: 1.05rem; color: #3A352D; max-width: 62ch; }

.stat-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1rem;
  margin: 2rem 0;
}
.stat .v { font-family: "Instrument Serif", serif; font-size: 2rem; }
.stat .l { font-size: 0.75rem; color: var(--muted); }

.kcc-card {
  background: var(--paper-2);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 1rem;
  text-align: left;
}

.ev-0 { background: var(--ev-0); }
.ev-1 { background: var(--ev-1); }
.ev-2 { background: var(--ev-2); }
.ev-3 { background: var(--ev-3); }
.ev-4 { background: var(--ev-4); }

div[data-testid="stButton"] > button[kind="primary"] {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
}

.hkcc-footer {
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--rule);
  font-size: 0.8rem;
  color: var(--muted);
}
"""

EV_COLORS = ["#ECE5D2", "#E6C98A", "#D89759", "#B25A35", "#7A1F1F"]
