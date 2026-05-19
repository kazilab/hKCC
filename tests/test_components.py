from app.components.matrix import matrix_heatmap_html
from app.utils.evidence import kcc_coverage


def test_matrix_html_includes_agent():
    kccs = [{"id": "kcc-01", "n": 1, "short": "Electrophilic"}]
    rows = [{"id": "benzene", "name": "Benzene", "iarc_group": "1", "scores": {"kcc-01": 4}}]
    html = matrix_heatmap_html(kccs, rows)
    assert "Benzene" in html
    assert "#7A1F1F" in html  # ev-4 color


def test_kcc_coverage():
    assert kcc_coverage({"kcc-01": 4, "kcc-02": 1, "kcc-03": 2}) == 2
