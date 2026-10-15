"""Context detection utilities."""

import json
import os
from pathlib import Path

from terrapyne.core.backend import detect_backend
from terrapyne.core.config import TerrapyneConfig, load_config


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


def resolve_workspace(
    workspace_arg: str | None = None,
    config: TerrapyneConfig | None = None,
    profile_name: str | None = None,
) -> str | None:
    """Resolve workspace name from argument, environment, local state, or profile.

    Priority:
    1. Explicit workspace_arg
    2. TFC_WORKSPACE environment variable
    3. Local .terraform/terraform.tfstate or terraform.tf
    4. Active profile default_workspace
    """
    if workspace_arg:
        return workspace_arg

    env_ws = os.getenv("TFC_WORKSPACE")
    if env_ws:
        return env_ws

    # Try to detect from terraform.tf / tfstate
    workspace_name, _, _ = get_workspace_context()
    if workspace_name:
        return workspace_name

    cfg = config if config is not None else load_config()
    profile = cfg.get_profile(profile_name)
    if profile and profile.default_workspace:
        return profile.default_workspace

    return None


def resolve_organization(
    org_arg: str | None = None,
    config: TerrapyneConfig | None = None,
    profile_name: str | None = None,
) -> str | None:
    """Resolve organization from argument, environment, local state, or profile.

    Priority:
    1. Explicit org_arg
    2. TFC_ORG environment variable
    3. Local .terraform/terraform.tfstate or terraform.tf
    4. Active profile organization
    """
    if org_arg:
        return org_arg

    # Priority 1: TFC_ORG environment variable
    env_org = os.getenv("TFC_ORG")
    if env_org:
        return env_org

    # Priority 2: Detect from terraform.tf / tfstate
    _, organization, _ = get_workspace_context()
    if organization:
        return organization

    # Priority 3: Detect from active profile
    cfg = config if config is not None else load_config()
    profile = cfg.get_profile(profile_name)
    if profile and profile.organization:
        return profile.organization

    return None


def resolve_host(
    host_arg: str | None = None,
    config: TerrapyneConfig | None = None,
    profile_name: str | None = None,
) -> str:
    """Resolve Terraform Cloud/Enterprise hostname.

    Priority:
    1. Explicit host_arg (if specified and not default)
    2. TFC_HOST or TFE_HOST environment variable
    3. Local .terraform/terraform.tfstate or terraform.tf hostname (if not default)
    4. Active profile hostname
    5. Default "app.terraform.io"
    """
    if host_arg and host_arg != "app.terraform.io":
        return host_arg

    env_host = os.getenv("TFC_HOST") or os.getenv("TFE_HOST")
    if env_host:
        return env_host

    _, _, hostname = get_workspace_context()
    if hostname and hostname != "app.terraform.io":
        return hostname

    cfg = config if config is not None else load_config()
    profile = cfg.get_profile(profile_name)
    if profile and profile.hostname:
        return profile.hostname

    return host_arg or "app.terraform.io"
