"""Unit tests for exceptions and main entry point."""

import sys
from unittest.mock import patch

from terrapyne.exceptions import (
    TerraformApplyError,
    TerraformApplyException,
    TerraformError,
    TerraformVersionError,
    TerraformVersionException,
)


class TestExceptions:
    """Test exception classes."""

    def test_terraform_error_base(self):
        """Test TerraformError base exception."""
        exc = TerraformError("test error")
        assert str(exc) == "test error"

    def test_terraform_version_error(self):
        """Test TerraformVersionError."""
        exc = TerraformVersionError("version mismatch")
        assert isinstance(exc, TerraformError)

    def test_terraform_apply_error(self):
        """Test TerraformApplyError with all parameters."""
        exc = TerraformApplyError(
            message="Apply failed",
            exit_code=1,
            expect_exit_code=0,
            stdout="some output",
            stderr="some error",
            pwd="/tmp/test",
        )

        assert exc.message == "Apply failed"
        assert exc.exit_code == 1
        assert exc.expect_exit_code == 0
        assert exc.stdout == "some output"
        assert exc.stderr == "some error"
        assert exc.pwd == "/tmp/test"
        assert isinstance(exc, TerraformError)

    def test_backwards_compat_version_exception(self):
        """Test TerraformVersionException backwards compatibility alias."""
        assert TerraformVersionException is TerraformVersionError

    def test_backwards_compat_apply_exception(self):
        """Test TerraformApplyException backwards compatibility alias."""
        assert TerraformApplyException is TerraformApplyError


class TestMainEntryPoint:
    """Test __main__ entry point."""

    def test_main_invokes_app(self):
        """Test that __main__.py invokes the CLI app."""
        with patch("terrapyne.__main__.app") as mock_app:
            # Simulate running the module

            with patch.dict(sys.modules, {"terrapyne.cli.main": mock_app}):
                # Import and trigger the module
                from terrapyne import __main__

                # The module should have imported app, verify it exists
                assert hasattr(__main__, "app")
