"""Theme factory — paper default, dark override."""

from pathlib import Path

from hkcc.app.components.card import CARD_KEY_PREFIX
from hkcc.app.theme import DARK_THEME, PAPER_THEME, get_theme

PAGES_DIR = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages"


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
    from hkcc.app.theme import THEME

    assert THEME["paper"] == PAPER_THEME["paper"]


def test_cards_are_reachable_from_css():
    """A bordered container is only themeable through its ``st-key-`` class.

    Streamlit dropped the ``stVerticalBlockBorderWrapper`` test id the theme used
    to key on, and a bordered container carries nothing else that CSS can select,
    so a card without a key silently renders in Streamlit's own colours.
    """
    for name in ("paper", "dark"):
        _t, css, _ev = get_theme(name)
        assert f'[class*="st-key-{CARD_KEY_PREFIX}"]' in css, name


def test_no_page_builds_a_bordered_container_directly():
    """Every card must go through ``card()``, which supplies that key."""
    offenders = [
        p.name for p in PAGES_DIR.glob("*.py") if "st.container(border=True)" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"use card() from app.components.card instead: {sorted(offenders)}"
