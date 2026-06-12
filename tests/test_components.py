from app.components.matrix import matrix_heatmap_html
from app.theme import apply_theme
from app.utils.evidence import kcc_coverage


def test_matrix_html_includes_agent():
    apply_theme(inject=False)
    kccs = [{"id": "kcc-01", "n": 1, "short": "Electrophilic"}]
    rows = [{"id": "benzene", "name": "Benzene", "iarc_group": "1", "scores": {"kcc-01": 4}}]
    html = matrix_heatmap_html(kccs, rows)
    assert "Benzene" in html
    assert "#8B2E2A" in html  # ev-4 (paper theme default)


def test_kcc_coverage():
    assert kcc_coverage({"kcc-01": 4, "kcc-02": 1, "kcc-03": 2}) == 2
