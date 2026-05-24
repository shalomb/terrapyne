"""Test SDK namespace deprecation warning."""

import importlib
import sys
import warnings


def test_sdk_namespace_deprecated():
    """Test that importing from terrapyne.sdk issues a deprecation warning."""
    # Evict cached module so the module-level warnings.warn() fires again.
    sys.modules.pop("terrapyne.sdk", None)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        import terrapyne.sdk

        importlib.reload(terrapyne.sdk)

        # Check that a warning was issued
        deprecation_warnings = [
            warning for warning in w if issubclass(warning.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1
        assert "terrapyne.sdk is deprecated" in str(deprecation_warnings[0].message)


def test_sdk_namespace_provides_imports():
    """Test that imports from terrapyne.sdk still work."""
    # Should be able to import without errors
    from terrapyne.sdk import TFCClient, WorkspaceAPI

    assert TFCClient is not None
    assert WorkspaceAPI is not None
