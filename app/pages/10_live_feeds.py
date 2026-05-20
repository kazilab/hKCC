"""Live feeds — dedicated navigation page."""

import streamlit as st

from app.theme import HKCC_CSS
from app.views.live_feeds import render_live_feeds

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)
render_live_feeds(show_header=True)
