from pathlib import Path


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
    ]
    assert (root / "streamlit_app.py").is_file()
    for p in pages:
        assert (root / "app/pages" / p).is_file()


def test_theme_css_has_accent():
    from app.theme import apply_theme

    theme, _ = apply_theme(inject=False)
    _, css, _ = __import__("app.theme", fromlist=["get_theme"]).get_theme("paper")
    assert theme["accent"] == "#8B2E2A"
    assert "Public+Sans" in css
