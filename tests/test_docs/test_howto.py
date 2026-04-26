from pathlib import Path


def test_howto_list_workspaces_calls_list():
    content = Path("docs/how-to/list-workspaces-by-project.md").read_text()
    assert "list(workspaces)" in content


def test_howto_list_workspaces_notes_nullable_total():
    content = Path("docs/how-to/list-workspaces-by-project.md").read_text()
    assert "None" in content or "nullable" in content.lower() or "may be" in content
