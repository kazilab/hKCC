from hkcc.app.components.ref_card import ref_card_html
from hkcc.app.theme import apply_theme

apply_theme(inject=False)


def test_ref_card_contains_title():
    html = ref_card_html(
        {
            "id": "smith2016",
            "year": 2016,
            "authors": "Smith MT",
            "title": "Key characteristics of carcinogens",
            "journal": "EHP",
            "vol": "124",
            "doi": "10.1289/ehp.1509912",
            "citations": 100,
            "tags": ["Foundational"],
            "kcc_ids": [],
        }
    )
    assert "Key characteristics" in html
    assert "2016" in html
    assert "font-style:italic" in html
