import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "hkcc" / "app" / "pages"


def _registered_pages() -> set[str]:
    """Filenames listed in streamlit_app.py's _page_defs."""
    source = (ROOT / "hkcc" / "streamlit_app.py").read_text(encoding="utf-8")
    block = source.split("_page_defs = [", 1)[1].split("]", 1)[0]
    return set(re.findall(r'"([^"]+\.py)"', block))


def _page_files() -> set[str]:
    return {p.name for p in PAGES_DIR.glob("*.py") if p.name != "__init__.py"}


def test_every_page_file_is_registered_in_navigation():
    """An unregistered page is unreachable — the IARC matrix shipped that way."""
    missing = _page_files() - _registered_pages()
    assert not missing, f"pages present but not in st.navigation: {sorted(missing)}"


def test_navigation_has_no_entries_without_a_file():
    dangling = _registered_pages() - _page_files()
    assert not dangling, f"navigation lists pages that do not exist: {sorted(dangling)}"


def test_sidebar_links_point_at_real_pages():
    from hkcc.app.components.sidebar import _NAV

    for _key, label, path, _count in _NAV:
        if path is None:
            continue
        assert (ROOT / "hkcc" / path.removeprefix("app/")).is_file() or (
            ROOT / "hkcc" / path
        ).is_file(), f"sidebar entry {label!r} points at missing page {path}"


def test_streamlit_pages_exist():
    root = Path(__file__).resolve().parents[1]
    pages = [
        "1_Overview.py",
        "2_Browse_KCCs.py",
        "2a_KCC_Detail.py",
        "3_Carcinogens.py",
        "4_Agent_Detail.py",
        "5_Evidence_Matrix.py",
        "6_Assays.py",
        "7_Literature.py",
        "8_API_Downloads.py",
        "9_About.py",
        "9a_Methodology.py",
        "9b_IARC_Matrix.py",
    ]
    assert (root / "hkcc/streamlit_app.py").is_file()
    for p in pages:
        assert (root / "hkcc/app/pages" / p).is_file()


def test_theme_css_has_accent():
    from hkcc.app.theme import apply_theme

    theme, _ = apply_theme(inject=False)
    _, css, _ = __import__("hkcc.app.theme", fromlist=["get_theme"]).get_theme("paper")
    assert theme["accent"] == "#8B2E2A"
    assert "Public+Sans" in css
