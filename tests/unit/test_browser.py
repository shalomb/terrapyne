"""Unit tests for browser utilities."""

from unittest.mock import patch

from terrapyne.utils.browser import (
    get_run_url,
    get_workspace_url,
    open_url_in_browser,
)


class TestOpenURLInBrowser:
    """Test open_url_in_browser function."""

    @patch("terrapyne.utils.browser._get_browser_commands", return_value=["xdg-open"])
    @patch("terrapyne.utils.browser._try_open_with_command", return_value=True)
    def test_open_url_success_with_first_command(self, mock_try_command, mock_get_commands):
        """Test successful browser open with first available command."""
        result = open_url_in_browser("https://example.com")
        assert result is True

    @patch("terrapyne.utils.browser._get_browser_commands", return_value=["xdg-open"])
    @patch("terrapyne.utils.browser._try_open_with_command", return_value=False)
    @patch("terrapyne.utils.browser._try_open_with_webbrowser", return_value=True)
    def test_open_url_fallback_to_webbrowser(
        self, mock_webbrowser, mock_try_command, mock_get_commands
    ):
        """Test fallback to webbrowser when command fails."""
        result = open_url_in_browser("https://example.com")
        assert result is True

    @patch("terrapyne.utils.browser._get_browser_commands", return_value=["xdg-open"])
    @patch("terrapyne.utils.browser._try_open_with_command", return_value=False)
    @patch("terrapyne.utils.browser._try_open_with_webbrowser", return_value=False)
    def test_open_url_all_methods_fail(self, mock_webbrowser, mock_try_command, mock_get_commands):
        """Test when all open methods fail."""
        result = open_url_in_browser("https://example.com")
        assert result is False

    @patch(
        "terrapyne.utils.browser._get_browser_commands", return_value=["xdg-open", "x-www-browser"]
    )
    @patch("terrapyne.utils.browser._try_open_with_command", side_effect=[False, True])
    def test_open_url_tries_multiple_commands(self, mock_try_command, mock_get_commands):
        """Test that multiple commands are tried."""
        result = open_url_in_browser("https://example.com")
        assert result is True


class TestGetBrowserCommands:
    """Test _get_browser_commands platform detection."""

    def test_linux_commands(self):
        """Test Linux browser commands."""
        from terrapyne.utils.browser import _get_browser_commands

        with patch("sys.platform", "linux"):
            commands = _get_browser_commands()
            assert commands == ["xdg-open", "x-www-browser"]

    def test_macos_commands(self):
        """Test macOS browser commands."""
        from terrapyne.utils.browser import _get_browser_commands

        with patch("sys.platform", "darwin"):
            commands = _get_browser_commands()
            assert commands == ["open"]

    def test_windows_commands(self):
        """Test Windows browser commands."""
        from terrapyne.utils.browser import _get_browser_commands

        with patch("sys.platform", "win32"):
            commands = _get_browser_commands()
            assert commands == ["cmd"]

    def test_unknown_platform(self):
        """Test unknown platform returns empty list."""
        from terrapyne.utils.browser import _get_browser_commands

        with patch("sys.platform", "unknown_os"):
            commands = _get_browser_commands()
            assert commands == []


class TestTryOpenWithCommand:
    """Test _try_open_with_command function."""

    def test_unix_command_success(self):
        """Test successful Unix command execution."""
        from terrapyne.utils.browser import _try_open_with_command

        with patch("subprocess.run") as mock_run:
            result = _try_open_with_command("xdg-open", "https://example.com")

            assert result is True
            mock_run.assert_called_once_with(
                ["xdg-open", "https://example.com"],
                check=True,
                stdout=-3,  # subprocess.DEVNULL
                stderr=-3,
            )

    def test_windows_command_success(self):
        """Test successful Windows command execution."""
        from terrapyne.utils.browser import _try_open_with_command

        with patch("subprocess.run") as mock_run:
            result = _try_open_with_command("cmd", "https://example.com")

            assert result is True
            mock_run.assert_called_once_with(
                ["cmd", "/c", "start", "", "https://example.com"],
                check=True,
                stdout=-3,
                stderr=-3,
            )

    def test_command_not_found(self):
        """Test command not found error."""
        from terrapyne.utils.browser import _try_open_with_command

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _try_open_with_command("nonexistent", "https://example.com")
            assert result is False

    def test_command_permission_denied(self):
        """Test permission denied error."""
        from terrapyne.utils.browser import _try_open_with_command

        with patch("subprocess.run", side_effect=PermissionError):
            result = _try_open_with_command("xdg-open", "https://example.com")
            assert result is False

    def test_command_non_zero_exit(self):
        """Test non-zero exit code."""
        import subprocess

        from terrapyne.utils.browser import _try_open_with_command

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "xdg-open")):
            result = _try_open_with_command("xdg-open", "https://example.com")
            assert result is False


class TestTryOpenWithWebbrowser:
    """Test _try_open_with_webbrowser function."""

    def test_webbrowser_success(self):
        """Test successful webbrowser module open."""
        from terrapyne.utils.browser import _try_open_with_webbrowser

        with patch("webbrowser.open") as mock_open:
            result = _try_open_with_webbrowser("https://example.com")

            assert result is True
            mock_open.assert_called_once_with("https://example.com")

    def test_webbrowser_failure(self):
        """Test webbrowser module failure."""
        from terrapyne.utils.browser import _try_open_with_webbrowser

        with patch("webbrowser.open", side_effect=Exception("Browser error")):
            result = _try_open_with_webbrowser("https://example.com")
            assert result is False


class TestGetWorkspaceURL:
    """Test get_workspace_url URL construction."""

    def test_basic_workspace_url(self):
        """Test basic workspace URL without page."""
        url = get_workspace_url("Takeda", "my-workspace")
        assert url == "https://app.terraform.io/app/Takeda/workspaces/my-workspace"

    def test_workspace_url_with_page_overview(self):
        """Test workspace URL with overview page."""
        url = get_workspace_url("Takeda", "my-workspace", page="overview")
        assert url == "https://app.terraform.io/app/Takeda/workspaces/my-workspace/overview"

    def test_workspace_url_with_page_runs(self):
        """Test workspace URL with runs page."""
        url = get_workspace_url("Takeda", "my-workspace", page="runs")
        assert url == "https://app.terraform.io/app/Takeda/workspaces/my-workspace/runs"

    def test_workspace_url_with_page_states(self):
        """Test workspace URL with states page."""
        url = get_workspace_url("Takeda", "my-workspace", page="states")
        assert url == "https://app.terraform.io/app/Takeda/workspaces/my-workspace/states"

    def test_workspace_url_with_page_variables(self):
        """Test workspace URL with variables page."""
        url = get_workspace_url("Takeda", "my-workspace", page="variables")
        assert url == "https://app.terraform.io/app/Takeda/workspaces/my-workspace/variables"

    def test_workspace_url_with_page_settings(self):
        """Test workspace URL with settings page."""
        url = get_workspace_url("Takeda", "my-workspace", page="settings")
        assert url == "https://app.terraform.io/app/Takeda/workspaces/my-workspace/settings"

    def test_workspace_url_custom_host(self):
        """Test workspace URL with custom host."""
        url = get_workspace_url("MyOrg", "ws", host="tfe.example.com")
        assert url == "https://tfe.example.com/app/MyOrg/workspaces/ws"

    def test_workspace_url_custom_host_with_page(self):
        """Test workspace URL with custom host and page."""
        url = get_workspace_url("MyOrg", "ws", host="tfe.example.com", page="states")
        assert url == "https://tfe.example.com/app/MyOrg/workspaces/ws/states"


class TestGetRunURL:
    """Test get_run_url URL construction."""

    def test_basic_run_url(self):
        """Test basic run URL."""
        url = get_run_url("Takeda", "my-workspace", "run-abc123")
        assert url == "https://app.terraform.io/app/Takeda/workspaces/my-workspace/runs/run-abc123"

    def test_run_url_custom_host(self):
        """Test run URL with custom host."""
        url = get_run_url("MyOrg", "ws", "run-xyz789", host="tfe.example.com")
        assert url == "https://tfe.example.com/app/MyOrg/workspaces/ws/runs/run-xyz789"

    def test_run_url_various_run_ids(self):
        """Test run URL with various run ID formats."""
        run_ids = ["run-123", "run-abc-def", "run-xyz123xyz"]
        for run_id in run_ids:
            url = get_run_url("Takeda", "my-workspace", run_id)
            assert run_id in url
            assert "runs/" in url
