"""Terrapyne - Python SDK for Terraform Cloud / Enterprise.

Library Usage:
    from terrapyne import TFCClient, RunsAPI

    client = TFCClient(organization="my-org")
    runs, total = client.runs.list(workspace_id="ws-123")
"""

__version__ = "0.0.1"

from . import exceptions
from .api.client import TFCClient
from .api.projects import ProjectAPI
from .api.runs import RunsAPI
from .api.teams import TeamsAPI
from .api.vcs import VCSAPI
from .api.workspace_clone import CloneWorkspaceAPI
from .api.workspaces import WorkspaceAPI
from .core.backend import RemoteBackend
from .core.credentials import TerraformCredentials
from .core.plan_parser import TerraformPlainTextPlanParser as PlanParser
from .models.plan import Plan
from .models.project import Project
from .models.run import Run
from .models.team import Team
from .models.team_access import TeamProjectAccess
from .models.variable import WorkspaceVariable
from .models.vcs import VCSConnection
from .models.workspace import Workspace, WorkspaceVCS
from .terrapyne import Terraform
from .utils.context import resolve_organization, resolve_workspace

__all__ = [
    "TFCClient",
    "RunsAPI",
    "WorkspaceAPI",
    "ProjectAPI",
    "TeamsAPI",
    "VCSAPI",
    "CloneWorkspaceAPI",
    "PlanParser",
    "Plan",
    "Project",
    "Run",
    "Team",
    "TeamProjectAccess",
    "Workspace",
    "WorkspaceVCS",
    "WorkspaceVariable",
    "VCSConnection",
    "RemoteBackend",
    "TerraformCredentials",
    "Terraform",
    "exceptions",
    "resolve_organization",
    "resolve_workspace",
]
