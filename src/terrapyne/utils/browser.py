"""Browser integration utilities."""

import subprocess
import sys
import webbrowser
from typing import Literal


def open_url_in_browser(url: str) -> bool:
    """
    Open URL in default browser with cross-platform support.

    Tries platform-specific commands first (more reliable), then falls back
    to Python's webbrowser module.

    Supported platforms:
    - Linux: xdg-open, x-www-browser
    - macOS: open
    - Windows: start (via cmd)

    Args:
        url: The URL to open

    Returns:
        True if browser launched successfully, False otherwise

    Example:
        >>> if not open_url_in_browser("https://example.com"):
        ...     print("Could not open browser")
    """
    # Determine platform-specific browser commands
    browser_commands = _get_browser_commands()

    # Try each browser command
    for browser_cmd in browser_commands:
        if _try_open_with_command(browser_cmd, url):
            return True

    # Fallback to Python's webbrowser module
    return _try_open_with_webbrowser(url)


def _get_browser_commands() -> list[str]:
    """Get platform-specific browser launcher commands."""
    if sys.platform == "linux":
        return ["xdg-open", "x-www-browser"]
    elif sys.platform == "darwin":
        return ["open"]
    elif sys.platform == "win32":
        # On Windows, use 'cmd /c start' to avoid shell popup
        return ["cmd"]
    else:
        # Unknown platform, let webbrowser handle it
        return []


def _try_open_with_command(command: str, url: str) -> bool:
    """
    Try to open URL with a specific command.

    Args:
        command: Browser launcher command (e.g., "xdg-open", "open")
        url: URL to open

    Returns:
        True if successful, False otherwise
    """
    try:
        if command == "cmd":
            # Windows: cmd /c start "" "URL"
            # Empty string after start is the window title
            subprocess.run(
                ["cmd", "/c", "start", "", url],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # Unix-like systems
            subprocess.run(
                [command, url],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
        return False


def _try_open_with_webbrowser(url: str) -> bool:
    """
    Fallback: try to open URL with Python's webbrowser module.

    Args:
        url: URL to open

    Returns:
        True if successful, False otherwise
    """
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def get_workspace_url(
    organization: str,
    workspace: str,
    host: str = "app.terraform.io",
    page: Literal["overview", "runs", "states", "variables", "settings"] | None = None,
) -> str:
    """
    Construct Terraform Cloud workspace URL.

    Args:
        organization: TFC organization name
        workspace: Workspace name
        host: TFC hostname (default: app.terraform.io)
        page: Specific workspace page to open (optional)

    Returns:
        Fully qualified workspace URL

    Examples:
        >>> get_workspace_url("my-org", "my-workspace")
        'https://app.terraform.io/app/my-org/workspaces/my-workspace'

        >>> get_workspace_url("my-org", "my-workspace", page="runs")
        'https://app.terraform.io/app/my-org/workspaces/my-workspace/runs'

        >>> get_workspace_url("MyOrg", "ws", host="tfe.example.com", page="states")
        'https://tfe.example.com/app/MyOrg/workspaces/ws/states'
    """
    base_url = f"https://{host}/app/{organization}/workspaces/{workspace}"

    if page:
        return f"{base_url}/{page}"

    return base_url


def get_run_url(
    organization: str,
    workspace: str,
    run_id: str,
    host: str = "app.terraform.io",
) -> str:
    """
    Construct Terraform Cloud run URL.

    Args:
        organization: TFC organization name
        workspace: Workspace name
        run_id: Run ID (e.g., "run-xyz123")
        host: TFC hostname (default: app.terraform.io)

    Returns:
        Fully qualified run URL

    Example:
        >>> get_run_url("my-org", "my-workspace", "run-abc123")
        'https://app.terraform.io/app/my-org/workspaces/my-workspace/runs/run-abc123'
    """
    return f"https://{host}/app/{organization}/workspaces/{workspace}/runs/{run_id}"
