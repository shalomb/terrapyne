"""Unit tests for main CLI entry point."""

from typer.testing import CliRunner

from terrapyne.cli.main import app

runner = CliRunner()


class TestMainCLI:
    """Test main CLI app."""

    def test_version_flag(self):
        """Test --version flag displays version and exits."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "terrapyne version 0.1.0" in result.stdout

    def test_no_subcommand_shows_help(self):
        """Test invoking without subcommand shows help."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Terraform Cloud CLI orchestrator" in result.stdout
        assert "workspace" in result.stdout
        assert "run" in result.stdout

    def test_quiet_mode_suppresses_help(self):
        """Test --quiet flag suppresses help output."""
        result = runner.invoke(app, ["--quiet"])
        # Should exit without printing help
        assert result.exit_code == 0
        # Help should not be printed in quiet mode
        assert (
            "Terraform Cloud CLI orchestrator" not in result.stdout or result.stdout.strip() == ""
        )
