"""Ensure no Pydantic V2 deprecation warnings from our models."""

import warnings

import pytest


def test_no_pydantic_v2_deprecation_warnings():
    """Importing all models must not trigger PydanticDeprecatedSince20 warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        try:
            # Import every model module — the ones we own
            import terrapyne.models.run
            import terrapyne.models.state_version
            import terrapyne.models.team
            import terrapyne.models.variable
            import terrapyne.models.workspace  # noqa: F401
        except Exception as e:
            if (
                "PydanticDeprecatedSince20" in str(type(e).__name__)
                or "deprecated" in str(e).lower()
            ):
                pytest.fail(f"Pydantic V2 deprecation warning raised as error: {e}")
            raise
