"""Terrapyne - Python SDK for Terraform Cloud / Enterprise.

Library Usage:
    from terrapyne import TFCClient, RunsAPI

    client = TFCClient(organization="my-org")
    runs, total = client.runs.list(workspace_id="ws-123")
"""

__version__ = "0.1.0"

from .api.client import TFCClient
from .api.projects import ProjectAPI
from .api.runs import RunsAPI
from .api.teams import TeamsAPI
from .api.vcs import VCSAPI
from .api.workspace_clone import CloneWorkspaceAPI
from .api.workspaces import WorkspaceAPI
from .core.backend import RemoteBackend
from .core.context import resolve_organization, resolve_workspace
from .core.credentials import TerraformCredentials
from .core.exceptions import (
    TerraformApplyError,
    TerraformError,
    TerraformVersionError,
    TerrapyneError,
    TFCAPIError,
    TFCAuthenticationError,
    TFCConflictError,
    TFCNotFoundError,
    TFCRateLimitError,
    TFCServerError,
    VCSTokenRequiredError,
    WorkspaceAlreadyExistsError,
    WorkspaceNotFoundError,
)
from .core.plan_parser import TerraformPlainTextPlanParser as PlanParser
from .models.plan import Plan
from .models.project import Project
from .models.run import Run
from .models.team import Team
from .models.team_access import TeamProjectAccess
from .models.variable import WorkspaceVariable
from .models.vcs import VCSConnection
from .models.workspace import Workspace, WorkspaceVCS

_DEPRECATED = {
    "Terraform": ("terrapyne.local.Terraform", "terrapyne.local"),
}


def __getattr__(name: str):
    if name in _DEPRECATED:
        import warnings

        _canonical, module = _DEPRECATED[name]
        warnings.warn(
            f"terrapyne.{name} is deprecated; use `from {module} import {name}` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib

        mod = importlib.import_module(".local", package=__name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VCSAPI",
    "CloneWorkspaceAPI",
    "Plan",
    "PlanParser",
    "Project",
    "ProjectAPI",
    "RemoteBackend",
    "Run",
    "RunsAPI",
    "TFCAPIError",
    "TFCAuthenticationError",
    "TFCClient",
    "TFCConflictError",
    "TFCNotFoundError",
    "TFCRateLimitError",
    "TFCServerError",
    "Team",
    "TeamProjectAccess",
    "TeamsAPI",
    "TerraformApplyError",
    "TerraformCredentials",
    "TerraformError",
    "TerraformVersionError",
    "TerrapyneError",
    "VCSConnection",
    "VCSTokenRequiredError",
    "Workspace",
    "WorkspaceAPI",
    "WorkspaceAlreadyExistsError",
    "WorkspaceNotFoundError",
    "WorkspaceVCS",
    "WorkspaceVariable",
    "resolve_organization",
    "resolve_workspace",
]
