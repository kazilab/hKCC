from app.components.matrix import matrix_heatmap_html
from app.theme import apply_theme

apply_theme(inject=False)


def test_matrix_bar_style_renders_bar():
    kccs = [{"id": "kcc-01", "n": 1, "short": "Geno"}]
    rows = [{"id": "x", "name": "Test", "iarc_group": "1", "scores": {"kcc-01": 3}}]
    html = matrix_heatmap_html(kccs, rows, matrix_style="bar")
    assert "height:75%" in html or "height:75" in html
