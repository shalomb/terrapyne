"""Factory functions for creating test API responses.

Replaces static fixtures with parameterizable factories to enable:
- Dynamic test data with custom overrides
- Parametrized testing without fixture explosion
- Reduced cascade failures when API schema changes
"""


def workspace_response(
    id="ws-1a2b3c4d5e6f7g8h",
    name="my-app-dev",
    terraform_version="1.7.0",
    execution_mode="remote",
    auto_apply=False,
    locked=False,
    tag_names=None,
    vcs_repo=None,
    project_id="prj-abc123",
    **attrs,
):
    """Factory for workspace detail response.

    Args:
        id: Workspace ID
        name: Workspace name
        terraform_version: Terraform version
        execution_mode: Execution mode (remote, local, agent)
        auto_apply: Auto-apply flag
        locked: Locked flag
        tag_names: List of tags
        vcs_repo: VCS repository config (dict)
        project_id: Related project ID
        **attrs: Additional attributes to override

    Returns:
        Dict matching TFC API workspace response schema.
    """
    if tag_names is None:
        tag_names = ["dev", "backend"]

    if vcs_repo is None:
        vcs_repo = {
            "identifier": "myorg/my-app",
            "branch": "develop",
            "repository-http-url": "https://github.com/myorg/my-app",
            "oauth-token-id": "ot-1a2b3c4d5e6f7g8h",
            "working-directory": "terraform/",
        }

    workspace_attrs = {
        "name": name,
        "created-at": "2025-03-13T07:50:15.781Z",
        "updated-at": "2025-03-15T10:20:30.456Z",
        "terraform-version": terraform_version,
        "execution-mode": execution_mode,
        "auto-apply": auto_apply,
        "locked": locked,
        "working-directory": "terraform/",
        "tag-names": tag_names,
        "vcs-repo": vcs_repo,
    }
    workspace_attrs.update(attrs)

    return {
        "data": {
            "id": id,
            "type": "workspaces",
            "attributes": workspace_attrs,
            "relationships": {"project": {"data": {"id": project_id, "type": "projects"}}},
        }
    }


def workspace_list_response(workspaces=None):
    """Factory for listing workspaces.

    Args:
        workspaces: List of workspace dicts (from workspace_response["data"]),
                   defaults to dev and prod workspaces

    Returns:
        Dict matching TFC API workspace list response schema.
    """
    if workspaces is None:
        workspaces = [
            workspace_response(
                id="ws-1a2b3c4d5e6f7g8h",
                name="my-app-dev",
                tag_names=["dev", "backend"],
            )["data"],
            workspace_response(
                id="ws-2a3b4c5d6e7f8g9h",
                name="my-app-prod",
                auto_apply=True,
                tag_names=["prod", "backend"],
            )["data"],
        ]

    return {
        "data": workspaces,
        "meta": {
            "pagination": {"total-count": len(workspaces), "current-page": 1, "total-pages": 1}
        },
        "links": {
            "self": "https://app.terraform.io/api/v2/organizations/test-org/workspaces",
            "first": "https://app.terraform.io/api/v2/organizations/test-org/workspaces?page%5Bnumber%5D=1",
            "last": "https://app.terraform.io/api/v2/organizations/test-org/workspaces?page%5Bnumber%5D=1",
            "next": None,
        },
    }


def variable_response(
    id="var-1a2b3c4d5e6f7g8h",
    key="region",
    value="us-east-1",
    category="terraform",
    sensitive=False,
    hcl=False,
    description=None,
    **attrs,
):
    """Factory for variable response.

    Args:
        id: Variable ID
        key: Variable key
        value: Variable value
        category: Category (terraform or env)
        sensitive: Sensitive flag
        hcl: HCL flag
        description: Variable description
        **attrs: Additional attributes to override

    Returns:
        Dict matching TFC API variable response schema.
    """
    var_attrs = {
        "key": key,
        "value": value,
        "category": category,
        "sensitive": sensitive,
        "hcl": hcl,
    }
    if description is not None:
        var_attrs["description"] = description
    var_attrs.update(attrs)

    return {
        "id": id,
        "type": "vars",
        "attributes": var_attrs,
    }


def workspace_variables_response(variables=None):
    """Factory for listing workspace variables.

    Args:
        variables: List of variable dicts (from variable_response),
                  defaults to region and aws_access_key

    Returns:
        Dict matching TFC API variable list response schema.
    """
    if variables is None:
        variables = [
            variable_response(
                id="var-1a2b3c4d5e6f7g8h",
                key="region",
                value="us-east-1",
                sensitive=False,
            ),
            variable_response(
                id="var-2a3b4c5d6e7f8g9h",
                key="aws_access_key",
                value="***",
                category="env",
                sensitive=True,
            ),
        ]

    return {
        "data": variables,
        "meta": {"pagination": {"total-count": len(variables)}},
    }


def run_response(
    id="run-abc123def456",
    status="applied",
    message="Applied by user",
    is_destroy=False,
    resource_additions=3,
    resource_changes=2,
    resource_destructions=0,
    workspace_id="ws-1a2b3c4d5e6f7g8h",
    **attrs,
):
    """Factory for run response.

    Args:
        id: Run ID
        status: Run status (pending, planning, planned, applying, applied, etc.)
        message: Run message
        is_destroy: Is destroy flag
        resource_additions: Resource additions count
        resource_changes: Resource changes count
        resource_destructions: Resource destructions count
        workspace_id: Related workspace ID
        **attrs: Additional attributes to override

    Returns:
        Dict matching TFC API run response schema.
    """
    run_attrs = {
        "status": status,
        "created-at": "2025-03-15T10:20:30.456Z",
        "updated-at": "2025-03-15T10:25:50.123Z",
        "message": message,
        "auto-apply": False,
        "is-destroy": is_destroy,
        "refresh": True,
        "refresh-only": False,
        "resource-additions": resource_additions,
        "resource-changes": resource_changes,
        "resource-destructions": resource_destructions,
        "target-addrs": [],
        "replace-addrs": [],
    }
    run_attrs.update(attrs)

    return {
        "data": {
            "id": id,
            "type": "runs",
            "attributes": run_attrs,
            "relationships": {"workspace": {"data": {"id": workspace_id, "type": "workspaces"}}},
        }
    }


def run_list_response(runs=None):
    """Factory for listing runs.

    Args:
        runs: List of run dicts (from run_response["data"]),
             defaults to applied and pending runs

    Returns:
        Dict matching TFC API run list response schema.
    """
    if runs is None:
        runs = [
            run_response(
                id="run-abc123def456",
                status="applied",
                message="Applied by user",
            )["data"],
            run_response(
                id="run-def456ghi789",
                status="pending",
                message=None,
                resource_additions=0,
                resource_changes=1,
            )["data"],
        ]

    return {
        "data": runs,
        "meta": {"pagination": {"total-count": len(runs)}},
    }


def project_response(
    id="prj-abc123",
    name="my-infrastructure",
    description="Core infrastructure project",
    resource_count=3,
    organization_id="test-org",
    **attrs,
):
    """Factory for project response.

    Args:
        id: Project ID
        name: Project name
        description: Project description
        resource_count: Resource count
        organization_id: Related organization ID
        **attrs: Additional attributes to override

    Returns:
        Dict matching TFC API project response schema.
    """
    proj_attrs = {
        "name": name,
        "description": description,
        "created-at": "2025-02-01T08:00:00.000Z",
        "resource-count": resource_count,
    }
    proj_attrs.update(attrs)

    return {
        "data": {
            "id": id,
            "type": "projects",
            "attributes": proj_attrs,
            "relationships": {
                "organization": {"data": {"id": organization_id, "type": "organizations"}}
            },
        }
    }


def project_list_response(projects=None):
    """Factory for listing projects.

    Args:
        projects: List of project dicts (from project_response["data"]),
                 defaults to two projects

    Returns:
        Dict matching TFC API project list response schema.
    """
    if projects is None:
        projects = [
            project_response(
                id="prj-abc123",
                name="my-infrastructure",
                description="Core infrastructure project",
                resource_count=3,
            )["data"],
            project_response(
                id="prj-def456",
                name="my-app-infrastructure",
                description="Application infrastructure",
                resource_count=2,
            )["data"],
        ]

    return {
        "data": projects,
        "meta": {"pagination": {"total-count": len(projects)}},
    }


def team_response(
    id="team-123",
    name="backend-team",
    description="Backend engineering team",
    organization_id="test-org",
    **attrs,
):
    """Factory for team response.

    Args:
        id: Team ID
        name: Team name
        description: Team description
        organization_id: Related organization ID
        **attrs: Additional attributes to override

    Returns:
        Dict matching TFC API team response schema.
    """
    team_attrs = {
        "name": name,
        "description": description,
        "created-at": "2025-01-15T08:00:00.000Z",
    }
    team_attrs.update(attrs)

    return {
        "data": {
            "id": id,
            "type": "teams",
            "attributes": team_attrs,
            "relationships": {
                "organization": {"data": {"id": organization_id, "type": "organizations"}}
            },
        }
    }


def team_project_access_response(
    id="tprj-abc123",
    access="admin",
    team_id="team-123",
    project_id="prj-abc123",
    project_access=None,
    workspace_access=None,
    **attrs,
):
    """Factory for team project access response.

    Args:
        id: Access ID
        access: Access level (read, write, admin)
        team_id: Related team ID
        project_id: Related project ID
        project_access: Project access config dict
        workspace_access: Workspace access config dict
        **attrs: Additional attributes to override

    Returns:
        Dict matching TFC API team project access response schema.
    """
    if project_access is None:
        project_access = {
            "settings": "delete",
            "teams": "manage",
            "variable-sets": "write",
        }
    if workspace_access is None:
        workspace_access = {
            "create": True,
            "delete": True,
            "move": True,
            "locking": True,
            "runs": "apply",
            "variables": "write",
            "state-versions": "write",
            "run-tasks": True,
        }

    access_attrs = {
        "access": access,
        "project-access": project_access,
        "workspace-access": workspace_access,
    }
    access_attrs.update(attrs)

    return {
        "data": {
            "id": id,
            "type": "team-projects",
            "attributes": access_attrs,
            "relationships": {
                "team": {
                    "data": {"id": team_id, "type": "teams"},
                    "links": {"related": f"https://app.terraform.io/api/v2/teams/{team_id}"},
                },
                "project": {"data": {"id": project_id, "type": "projects"}},
            },
        }
    }


def team_project_access_list_response(accesses=None):
    """Factory for listing team project accesses.

    Args:
        accesses: List of access dicts (from team_project_access_response["data"]),
                 defaults to admin and read accesses

    Returns:
        Dict matching TFC API team project access list response schema.
    """
    if accesses is None:
        accesses = [
            team_project_access_response(
                id="tprj-abc123",
                access="admin",
                team_id="team-123",
            )["data"],
            team_project_access_response(
                id="tprj-def456",
                access="read",
                team_id="team-456",
                project_access={
                    "settings": "read",
                    "teams": "none",
                    "variable-sets": "none",
                },
                workspace_access={
                    "create": False,
                    "delete": False,
                    "move": False,
                    "locking": False,
                    "runs": "read",
                    "variables": "read",
                    "state-versions": "read",
                    "run-tasks": False,
                },
            )["data"],
        ]

    return {
        "data": accesses,
        "meta": {"pagination": {"total-count": len(accesses)}},
    }


# Error responses (stateless, no factory needed)
def error_not_found():
    """Mock error response for not found."""
    return {
        "errors": [
            {
                "status": 404,
                "title": "not found",
                "detail": "Resource not found",
            }
        ]
    }


def error_unauthorized():
    """Mock error response for unauthorized."""
    return {
        "errors": [
            {
                "status": 401,
                "title": "unauthorized",
                "detail": "Invalid or missing token",
            }
        ]
    }


def error_forbidden():
    """Mock error response for forbidden."""
    return {
        "errors": [
            {
                "status": 403,
                "title": "forbidden",
                "detail": "Not authorized to access this resource",
            }
        ]
    }
