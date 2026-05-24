"""hKCC Streamlit entry — custom sidebar + st.navigation fallback."""

from pathlib import Path

import streamlit as st

from api.observability import init_sentry
from app.components.sidebar import render_sidebar
from app.data_client import DataSource, data_source_label, get_data_source
from app.theme import apply_theme, init_tweak_defaults

init_sentry("streamlit")
init_tweak_defaults()

APP_ROOT = Path(__file__).resolve().parent
PAGES_DIR = APP_ROOT / "app" / "pages"


def _page(filename: str, **kwargs) -> st.Page | None:
    path = PAGES_DIR / filename
    if not path.is_file():
        return None
    return st.Page(str(path), **kwargs)


st.set_page_config(
    page_title="hKCC",
    page_icon=":material/science:",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

with st.sidebar:
    if get_data_source() is DataSource.NO_DATA:
        st.info(data_source_label())
    else:
        st.caption(data_source_label())
    st.caption("Data CC-BY 4.0 · Code MIT")
    render_sidebar()

# Detail pages (2a_KCC_Detail, 4_Agent_Detail) must stay registered so
# st.switch_page() can target them from list pages. They are hidden from
# the rail by the stSidebarNav CSS rule in app/theme.py.
_page_defs = [
    ("1_Overview.py", dict(title="Overview", icon=":material/home:", default=True)),
    ("2_Browse_KCCs.py", dict(title="Browse KCCs", icon=":material/grid_view:")),
    ("2a_KCC_Detail.py", dict(title="KCC detail", icon=":material/category:")),
    ("3_Carcinogens.py", dict(title="Carcinogens", icon=":material/biotech:")),
    ("4_Agent_Detail.py", dict(title="Agent profile", icon=":material/person:")),
    ("5_Evidence_Matrix.py", dict(title="Evidence matrix", icon=":material/table_chart:")),
    ("6_Assays.py", dict(title="Assays", icon=":material/lab_research:")),
    ("7_Literature.py", dict(title="Literature", icon=":material/menu_book:")),
    ("8_API_Downloads.py", dict(title="API & downloads", icon=":material/api:")),
    ("9_About.py", dict(title="About", icon=":material/info:")),
]

pages = [p for spec in _page_defs if (p := _page(spec[0], **spec[1])) is not None]

if not pages:
    st.error(f"No pages found under `{PAGES_DIR}`.")
    st.stop()

pg = st.navigation(pages)
pg.run()
