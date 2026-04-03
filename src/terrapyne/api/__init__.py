"""Terraform Cloud API client."""

from .client import TFCClient
from .workspaces import WorkspaceAPI

# Ensure WorkspaceAPI is attached to TFCClient
__all__ = ["TFCClient", "WorkspaceAPI"]
