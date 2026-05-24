from app.components.agent_table import agent_table_html
from app.theme import apply_theme

apply_theme(inject=False)


def test_agent_table_includes_name_and_link():
    rows = [
        {
            "id": "benzene",
            "name": "Benzene",
            "cas": "71-43-2",
            "agent_type": "chemical",
            "iarc_group": "1",
            "sites": ["AML"],
            "scores": [4, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "evidence": {"kcc-01": 4, "kcc-02": 2},
        }
    ]
    html = agent_table_html(rows)
    assert "Benzene" in html
    assert "agent_id=benzene" in html
