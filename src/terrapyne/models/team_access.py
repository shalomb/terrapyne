"""Team access models for projects and workspaces."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectAccess(BaseModel):
    """Project-level permissions."""

    settings: Literal["read", "update", "delete"] = "read"
    teams: Literal["none", "read", "manage"] = "none"

    model_config = ConfigDict(populate_by_name=True)


class WorkspaceAccess(BaseModel):
    """Workspace-level permissions."""

    create: bool = False
    locking: bool = False
    delete: bool = False
    move: bool = False
    runs: Literal["read", "plan", "apply"] = "read"
    variables: Literal["none", "read", "write"] = "read"
    state_versions: Literal["none", "read", "read-outputs", "write"] = Field(
        "read", alias="state-versions"
    )
    sentinel_mocks: Literal["none", "read"] = Field("none", alias="sentinel-mocks")
    run_tasks: bool = Field(False, alias="run-tasks")

    model_config = ConfigDict(populate_by_name=True)


class TeamProjectAccess(BaseModel):
    """Team access to a project."""

    id: str
    access: Literal["read", "write", "maintain", "admin", "custom"]
    team_id: str
    team_name: str | None = None
    project_id: str
    project_access: ProjectAccess | None = Field(None, alias="project-access")
    workspace_access: WorkspaceAccess | None = Field(None, alias="workspace-access")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> TeamProjectAccess:
        """Create TeamProjectAccess from TFC API response.

        Args:
            data: API response data dict with 'id', 'type', 'attributes', 'relationships'

        Returns:
            TeamProjectAccess instance
        """
        attrs = data.get("attributes", {})
        relationships = data.get("relationships", {})

        # Extract team info
        team_data = relationships.get("team", {}).get("data", {})
        team_id = team_data.get("id", "")

        # Extract project info
        project_data = relationships.get("project", {}).get("data", {})
        project_id = project_data.get("id", "")

        # Parse access permissions
        project_access_data = attrs.get("project-access")
        workspace_access_data = attrs.get("workspace-access")

        return cls.model_construct(
            id=data["id"],
            access=attrs.get("access", "read"),
            team_id=team_id,
            project_id=project_id,
            project_access=ProjectAccess(**project_access_data) if project_access_data else None,
            workspace_access=(
                WorkspaceAccess(**workspace_access_data) if workspace_access_data else None
            ),
        )


class AccessDiff(BaseModel):
    """A single field difference between two access records."""

    field: str
    value_a: Any
    value_b: Any


class TeamProjectAccessComparison(BaseModel):
    """Result of comparing two TeamProjectAccess records."""

    identical: bool
    access_a: TeamProjectAccess
    access_b: TeamProjectAccess
    diffs: list[AccessDiff]

    @classmethod
    def compare(
        cls,
        access_a: TeamProjectAccess,
        access_b: TeamProjectAccess,
    ) -> TeamProjectAccessComparison:
        """Compare two TeamProjectAccess records field by field.

        Args:
            access_a: Reference access record (gold standard)
            access_b: Target access record to compare against

        Returns:
            TeamProjectAccessComparison with identical flag and field-level diffs
        """
        diffs: list[AccessDiff] = []

        # Compare top-level access
        if access_a.access != access_b.access:
            diffs.append(
                AccessDiff(field="access", value_a=access_a.access, value_b=access_b.access)
            )

        # Compare project_access fields
        if access_a.project_access and access_b.project_access:
            for field in ("settings", "teams"):
                val_a = getattr(access_a.project_access, field)
                val_b = getattr(access_b.project_access, field)
                if val_a != val_b:
                    diffs.append(
                        AccessDiff(field=f"project_access.{field}", value_a=val_a, value_b=val_b)
                    )
        elif access_a.project_access != access_b.project_access:
            diffs.append(
                AccessDiff(
                    field="project_access",
                    value_a=access_a.project_access,
                    value_b=access_b.project_access,
                )
            )

        # Compare workspace_access fields
        if access_a.workspace_access and access_b.workspace_access:
            for field in (
                "runs",
                "variables",
                "state_versions",
                "sentinel_mocks",
                "create",
                "locking",
                "delete",
                "move",
                "run_tasks",
            ):
                val_a = getattr(access_a.workspace_access, field)
                val_b = getattr(access_b.workspace_access, field)
                if val_a != val_b:
                    diffs.append(
                        AccessDiff(field=f"workspace_access.{field}", value_a=val_a, value_b=val_b)
                    )
        elif access_a.workspace_access != access_b.workspace_access:
            diffs.append(
                AccessDiff(
                    field="workspace_access",
                    value_a=access_a.workspace_access,
                    value_b=access_b.workspace_access,
                )
            )

        return cls(
            identical=len(diffs) == 0,
            access_a=access_a,
            access_b=access_b,
            diffs=diffs,
        )
