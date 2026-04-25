from pathlib import Path


def test_cli_reference_no_phantom_health_command():
    """workspace health does not exist in the CLI; must not be documented."""
    content = Path("docs/reference/cli-reference.md").read_text()
    assert "- `health`" not in content
