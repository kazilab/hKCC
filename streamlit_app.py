"""hKCC Streamlit entry — sidebar navigation matching mockup left rail."""

import streamlit as st

from app.theme import HKCC_CSS

st.set_page_config(
    page_title="hKCC",
    page_icon=":material/science:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"<style>{HKCC_CSS}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(
        '<p class="brand-serif" style="font-size:1.75rem;margin:0">h<span style="color:#8B2E2A">KCC</span></p>'
        '<p class="mono">Key characteristics</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("Data CC-BY 4.0 · Code MIT")

pages = [
    st.Page("app/pages/1_Overview.py", title="Overview", icon=":material/home:", default=True),
    st.Page("app/pages/2_Browse_KCCs.py", title="Browse KCCs", icon=":material/grid_view:"),
    st.Page("app/pages/3_Carcinogens.py", title="Carcinogens", icon=":material/biotech:"),
    st.Page("app/pages/4_Agent_Detail.py", title="Agent profile", icon=":material/person:"),
    st.Page("app/pages/5_Evidence_Matrix.py", title="Evidence matrix", icon=":material/table_chart:"),
    st.Page("app/pages/6_Assays.py", title="Assays", icon=":material/lab_research:"),
    st.Page("app/pages/7_Literature.py", title="Literature", icon=":material/menu_book:"),
    st.Page("app/pages/8_API_Downloads.py", title="API & downloads", icon=":material/api:"),
    st.Page("app/pages/9_About.py", title="About", icon=":material/info:"),
]

pg = st.navigation(pages)
pg.run()
