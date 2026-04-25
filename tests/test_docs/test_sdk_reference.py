from pathlib import Path


def test_sdk_reference_includes_state_versions_manager():
    content = Path("docs/reference/sdk.md").read_text()
    assert "client.state_versions" in content
    assert "StateVersionsAPI" in content


def test_sdk_reference_includes_vcs_manager():
    content = Path("docs/reference/sdk.md").read_text()
    assert "client.vcs" in content
    assert "VCSAPI" in content


def test_sdk_reference_models_match_all():
    """All models in terrapyne.models.__all__ must appear in sdk.md."""
    import sys

    sys.path.insert(0, "src")
    from terrapyne.models import __all__ as model_names

    content = Path("docs/reference/sdk.md").read_text()
    for name in model_names:
        assert name in content, f"Model {name!r} missing from sdk.md"
