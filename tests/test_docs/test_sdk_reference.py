from pathlib import Path


def test_sdk_reference_includes_state_versions_manager():
    content = Path("docs/reference/sdk.md").read_text()
    assert "client.state_versions" in content
    assert "StateVersionsAPI" in content


def test_sdk_reference_includes_vcs_manager():
    content = Path("docs/reference/sdk.md").read_text()
    assert "client.vcs" in content
    assert "VCSAPI" in content
