"""Context detection utilities."""

import json
from pathlib import Path

from terrapyne.core.backend import detect_backend


def get_context_from_tfstate(
    directory: Path | None = None,
) -> tuple[str | None, str | None, str | None]:
    """
    Read context from .terraform/terraform.tfstate.

    This is the preferred context source as it reflects the actual runtime
    configuration used by Terraform after 'terraform init'.

    Args:
        directory: Directory to search (defaults to current directory)

    Returns:
        Tuple of (workspace_name, organization, hostname)
        Returns (None, None, None) if tfstate not found or invalid
    """
    if directory is None:
        directory = Path.cwd()

    tfstate_path = directory / ".terraform" / "terraform.tfstate"

    if not tfstate_path.exists():
        return (None, None, None)

    try:
        with tfstate_path.open() as f:
            data = json.load(f)

        backend_config = data.get("backend", {}).get("config", {})

        # Extract organization and hostname
        org = backend_config.get("organization")
        hostname = backend_config.get("hostname", "app.terraform.io")

        # Handle workspaces - can be either "name" or "prefix"
        workspace_name = None
        workspaces = backend_config.get("workspaces")

        if isinstance(workspaces, dict):
            # Single workspace specified by name
            workspace_name = workspaces.get("name")
            # Note: "prefix" is used for multiple workspaces, we don't handle that here

        return (workspace_name, org, hostname)

    except (json.JSONDecodeError, OSError, KeyError):
        # Silently fail and let caller fall back to terraform.tf
        return (None, None, None)


def get_workspace_context() -> tuple[str | None, str | None, str | None]:
    """
    Detect workspace context with prioritized sources:
    1. .terraform/terraform.tfstate (primary - created by terraform init)
    2. terraform.tf (fallback - for fresh checkouts)

    Returns:
        Tuple of (workspace_name, organization, hostname)
        Returns (None, None, None) if no context detected
    """
    # Try tfstate first (more reliable, reflects actual runtime config)
    workspace, org, hostname = get_context_from_tfstate()

    if workspace or org:
        return (workspace, org, hostname)

    # Fallback to terraform.tf parsing
    backend = detect_backend(Path.cwd())

    if not backend:
        return (None, None, None)

    # Handle workspace name vs prefix
    workspace_name = backend.workspace_name or None

    return (workspace_name, backend.organization, backend.hostname)


def resolve_workspace(workspace_arg: str | None) -> str:
    """Resolve workspace name from argument or context.

    Args:
        workspace_arg: Workspace name from CLI argument (or None)

    Returns:
        Resolved workspace name

    Raises:
        ValueError: If no workspace specified and none detected from context
    """
    if workspace_arg:
        return workspace_arg

    # Try to detect from terraform.tf
    workspace_name, _, _ = get_workspace_context()

    if not workspace_name:
        raise ValueError(
            "No workspace specified and could not detect from context.\n"
            "Either:\n"
            "  1. Run this command from a directory with terraform configuration (terraform.tf or .terraform/terraform.tfstate), or\n"
            "  2. Specify workspace name: --workspace WORKSPACE_NAME"
        )

    return workspace_name


def resolve_organization(org_arg: str | None) -> str | None:
    """Resolve organization from argument or context.

    Args:
        org_arg: Organization from CLI argument (or None)

    Returns:
        Resolved organization or None
    """
    if org_arg:
        return org_arg

    # Try to detect from terraform.tf
    _, organization, _ = get_workspace_context()
    return organization
