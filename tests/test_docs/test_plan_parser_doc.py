from pathlib import Path


def test_plan_parser_doc_no_internal_paths():
    content = Path("docs/explanation/plan-parser.md").read_text()
    assert "internal-org" not in content
    assert "Copy Manifest" not in content
    assert "TODO" not in content
    assert "~/internal-org" not in content


def test_plan_parser_doc_has_diataxis_content():
    content = Path("docs/explanation/plan-parser.md").read_text()
    # Must explain what, why, and when
    assert "plan parser" in content.lower() or "Plan Parser" in content
    assert "TFC" in content or "Terraform Cloud" in content
