"""Backend detection from terraform.tf files."""

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

try:
    import hcl2  # type: ignore

    _hcl2: Any | None = hcl2
except Exception:  # pragma: no cover - optional dependency
    _hcl2 = None

HAS_HCL2 = _hcl2 is not None


class RemoteBackend(BaseModel):
    """Remote backend configuration."""

    hostname: str = "app.terraform.io"
    organization: str
    workspace_name: str | None = None
    workspace_prefix: str | None = None


def find_terraform_tf(start_dir: Path) -> Path | None:
    """Find a terraform .tf file in current or parent directories.

    Prefer a file named `terraform.tf` if present; otherwise return the
    first `*.tf` file found in the directory.
    """
    current = start_dir.resolve()
    while current != current.parent:
        # Prefer an explicit terraform.tf
        tf_file = current / "terraform.tf"
        if tf_file.exists():
            return tf_file
        # Look for any .tf file that contains a remote backend
        candidates = list(current.glob("*.tf"))
        for candidate in candidates:
            try:
                if 'backend "remote"' in candidate.read_text():
                    return candidate
            except Exception:
                continue
        # Fallback: return first .tf file in this directory
        for candidate in candidates:
            return candidate
        current = current.parent
    return None


def parse_backend_hcl(tf_file: Path) -> RemoteBackend | None:
    """Parse backend config from HCL."""
    if not HAS_HCL2:
        return None

    content = tf_file.read_text()
    hcl_loads = getattr(_hcl2, "loads", None)
    if not callable(hcl_loads):
        return None
    try:
        parsed = hcl_loads(content)
    except Exception:
        return None

    # Navigate parsed HCL for terraform -> backend "remote"
    terraform = parsed.get("terraform")
    if not terraform:
        return None

    # terraform can be a list or dict depending on hcl2 parsing
    if isinstance(terraform, list):
        terraform = terraform[0]

    if not isinstance(terraform, dict):
        return None

    backend = terraform.get("backend")
    if not backend or not isinstance(backend, dict):
        return None

    remote_block = backend.get("remote")
    if not remote_block:
        return None

    # remote_block may be list or dict
    if isinstance(remote_block, list):
        remote_block = remote_block[0]

    if not isinstance(remote_block, dict):
        return None

    hostname = remote_block.get("hostname", "app.terraform.io")
    organization = remote_block.get("organization")

    workspaces = remote_block.get("workspaces", {})
    if isinstance(workspaces, dict):
        workspace_name = workspaces.get("name")
        workspace_prefix = workspaces.get("prefix")
    else:
        workspace_name = None
        workspace_prefix = None

    if not organization:
        return None

    return RemoteBackend(
        hostname=hostname,
        organization=organization,
        workspace_name=workspace_name,
        workspace_prefix=workspace_prefix,
    )


def parse_backend_regex(content: str) -> RemoteBackend | None:
    """Fallback regex parsing."""
    # naive regex for organization
    org_match = re.search(r'\borganization\b\s*=\s*"([^"]+)"', content)
    hostname_match = re.search(r'\bhostname\b\s*=\s*"([^"]+)"', content)
    name_match = re.search(r'\bname\b\s*=\s*"([^"]+)"', content)
    prefix_match = re.search(r'\bprefix\b\s*=\s*"([^"]+)"', content)

    if not org_match:
        return None

    hostname = hostname_match.group(1) if hostname_match else "app.terraform.io"
    organization = org_match.group(1)
    workspace_name = name_match.group(1) if name_match else None
    workspace_prefix = prefix_match.group(1) if prefix_match else None

    return RemoteBackend(
        hostname=hostname,
        organization=organization,
        workspace_name=workspace_name,
        workspace_prefix=workspace_prefix,
    )


def detect_backend(path: Path | None = None) -> RemoteBackend | None:
    """Detect remote backend configuration."""
    if path is None:
        path = Path.cwd()

    tf_file = find_terraform_tf(path)
    if not tf_file:
        return None

    # Try HCL parsing first (on the discovered file)
    try:
        parsed = parse_backend_hcl(tf_file)
        if parsed:
            return parsed
    except Exception:
        pass
    # Fallback to regex across all .tf files in the same directory
    content_parts = []
    try:
        for candidate in tf_file.parent.glob("*.tf"):
            try:
                content_parts.append(candidate.read_text())
            except Exception:
                continue
    except Exception:
        # If anything goes wrong, fall back to the single file read
        content_parts = [tf_file.read_text()]

    content = "\n".join(content_parts)
    return parse_backend_regex(content)
