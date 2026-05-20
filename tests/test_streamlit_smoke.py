from pathlib import Path


def test_streamlit_pages_exist():
    root = Path(__file__).resolve().parents[1]
    pages = [
        "1_Overview.py",
        "2_Browse_KCCs.py",
        "3_Carcinogens.py",
        "4_Agent_Detail.py",
        "5_Evidence_Matrix.py",
        "6_Assays.py",
        "7_Literature.py",
        "8_API_Downloads.py",
        "9_About.py",
    ]
    assert (root / "streamlit_app.py").is_file()
    for p in pages:
        assert (root / "app/pages" / p).is_file()


def test_theme_css_has_accent():
    from app.theme import HKCC_CSS, THEME

    assert THEME["accent"] in HKCC_CSS
    assert "Public+Sans" in HKCC_CSS
