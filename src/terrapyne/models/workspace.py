"""Workspace models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from terrapyne.models.utils import parse_iso_datetime


class WorkspaceVCS(BaseModel):
    """VCS connection details for a workspace."""

    branch: str | None = None
    identifier: str | None = Field(None, description="Repository identifier (e.g., org/repo)")
    repository_http_url: str | None = Field(None, alias="repository-http-url")
    oauth_token_id: str | None = Field(None, alias="oauth-token-id")
    working_directory: str | None = Field(None, alias="working-directory")

    model_config = ConfigDict(populate_by_name=True)


class Workspace(BaseModel):
    """Terraform Cloud workspace model."""

    id: str
    name: str
    created_at: datetime | None = Field(None, alias="created-at")
    updated_at: datetime | None = Field(None, alias="updated-at")
    terraform_version: str | None = Field(None, alias="terraform-version")
    working_directory: str | None = Field(None, alias="working-directory")
    auto_apply: bool | None = Field(None, alias="auto-apply")
    execution_mode: str | None = Field(None, alias="execution-mode")
    locked: bool = False

    # VCS
    vcs_repo: WorkspaceVCS | None = Field(None, alias="vcs-repo")

    # Project relationship
    project_id: str | None = None
    project_name: str | None = None

    # Tags
    tag_names: list[str] = Field(default_factory=list, alias="tag-names")

    # Related models (included)
    latest_run: Any | None = None

    # Environment detection (derived from name)
    environment: str | None = None

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], included: list[dict[str, Any]] | None = None
    ) -> "Workspace":
        """Create workspace from TFC API response.

        Args:
            data: API response data dict (should contain 'id', 'type', 'attributes', 'relationships')
            included: Optional list of included resources from the API response

        Returns:
            Workspace instance
        """
        # Extract attributes
        attrs = data.get("attributes", {})

        # Extract VCS repo if present
        vcs_repo = None
        if attrs.get("vcs-repo"):
            vcs_repo = WorkspaceVCS.model_validate(attrs["vcs-repo"])

        # Extract project ID from relationships
        project_id = None
        project_name = None
        relationships = data.get("relationships", {})
        if relationships.get("project", {}).get("data"):
            project_id = relationships["project"]["data"].get("id")

        # Try to find project name in included data
        if included and project_id:
            for item in included:
                if item.get("type") == "projects" and item.get("id") == project_id:
                    project_name = item.get("attributes", {}).get("name")
                    break

        # Extract latest run if present in relationships and included
        latest_run = None
        if relationships.get("latest-run", {}).get("data"):
            run_id = relationships["latest-run"]["data"].get("id")
            if included:
                for item in included:
                    if item.get("type") == "runs" and item.get("id") == run_id:
                        from terrapyne.models.run import Run

                        latest_run = Run.from_api_response(item)
                        break

        # Detect environment from workspace name
        environment = cls._detect_environment(attrs.get("name", ""))

        return cls.model_construct(
            id=data["id"],
            name=attrs.get("name", ""),
            created_at=parse_iso_datetime(attrs.get("created-at")),
            updated_at=parse_iso_datetime(attrs.get("updated-at")),
            terraform_version=attrs.get("terraform-version"),
            working_directory=attrs.get("working-directory"),
            auto_apply=attrs.get("auto-apply"),
            execution_mode=attrs.get("execution-mode"),
            locked=attrs.get("locked", False),
            vcs_repo=vcs_repo,
            project_id=project_id,
            project_name=project_name,
            tag_names=attrs.get("tag-names", []),
            latest_run=latest_run,
            environment=environment,
        )

    @staticmethod
    def _detect_environment(name: str) -> str | None:
        """Detect environment from workspace name.

        Common patterns:
        - tec-xxx-dev-...
        - app-staging-...
        - prod-app-...
        """
        name_lower = name.lower()

        if "prod" in name_lower or "prd" in name_lower:
            return "production"
        elif "stag" in name_lower or "stage" in name_lower:
            return "staging"
        elif "dev" in name_lower:
            return "development"
        elif "test" in name_lower or "tst" in name_lower:
            return "test"
        elif "qa" in name_lower:
            return "qa"

        return None

    @property
    def vcs_branch(self) -> str | None:
        """Get VCS branch."""
        return self.vcs_repo.branch if self.vcs_repo else None

    @property
    def vcs_identifier(self) -> str | None:
        """Get VCS repository identifier."""
        return self.vcs_repo.identifier if self.vcs_repo else None

    @property
    def vcs_url(self) -> str | None:
        """Get VCS repository URL."""
        return self.vcs_repo.repository_http_url if self.vcs_repo else None
