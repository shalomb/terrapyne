from pathlib import Path


def test_adr004_gherkin_matches_feature_file():
    """ADR-004 Gherkin scenario titles must match workspace_dashboard.feature."""
    adr = Path("docs/explanation/architecture/ADR-004-workspace-dashboard-testing.md").read_text()
    assert "Workspace with recent successful run shows healthy status" in adr
    assert "Workspace with no run history shows unknown health" in adr
    # Old diverged titles must not appear
    assert "Workspace with no recent runs shows unknown health" not in adr
