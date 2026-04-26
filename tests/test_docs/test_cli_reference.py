from pathlib import Path


def test_cli_reference_documents_health_command():
    """workspace health exists in the CLI and must be documented."""
    content = Path("docs/reference/cli-reference.md").read_text()
    assert "- `health`" in content
