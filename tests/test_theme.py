"""Theme factory — paper default, dark override."""

from app.theme import DARK_THEME, PAPER_THEME, get_theme


def test_get_theme_paper():
    t, css, ev = get_theme("paper")
    assert t["paper"] == PAPER_THEME["paper"]
    assert ev[4] == "#8B2E2A"
    assert "#F7F4ED" in css


def test_get_theme_dark():
    t, css, ev = get_theme("dark")
    assert t["accent"] == DARK_THEME["accent"]
    assert "#14120E" in css


def test_paper_is_default_module_palette():
    from app.theme import THEME

    assert THEME["paper"] == PAPER_THEME["paper"]
