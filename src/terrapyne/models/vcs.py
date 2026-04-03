"""VCS connection models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VCSConnection(BaseModel):
    """VCS connection configuration for a workspace."""

    identifier: str = Field(..., description="Repository identifier (owner/repo)")
    branch: str | None = Field(None, description="VCS branch")
    ingress_submodules: bool = Field(
        False, alias="ingress-submodules", description="Include submodules"
    )
    oauth_token_id: str = Field(..., alias="oauth-token-id", description="OAuth token ID")
    repository_http_url: str | None = Field(
        None, alias="repository-http-url", description="Repository URL"
    )
    service_provider: Literal["github", "gitlab", "bitbucket", "azure-devops"] | None = Field(
        None, alias="service-provider"
    )
    display_identifier: str | None = Field(
        None, alias="display-identifier", description="Display name"
    )
    tags_regex: str | None = Field(None, alias="tags-regex", description="Tags regex pattern")
    working_directory: str | None = Field(
        None, alias="working-directory", description="Working directory in repo"
    )

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict) -> VCSConnection:
        """Parse VCS connection from TFC API response.

        Args:
            data: VCS repo attributes dict from workspace API response

        Returns:
            VCSConnection instance
        """
        return cls.model_validate(data)

    @property
    def github_url(self) -> str | None:
        """Get GitHub repository URL if applicable."""
        if self.service_provider == "github" and self.repository_http_url:
            return self.repository_http_url
        return None

    @property
    def owner(self) -> str | None:
        """Extract owner from identifier."""
        if "/" in self.identifier:
            return self.identifier.split("/")[0]
        return None

    @property
    def repo_name(self) -> str | None:
        """Extract repo name from identifier."""
        if "/" in self.identifier:
            return self.identifier.split("/")[1]
        return None

    @property
    def masked_oauth_token(self) -> str:
        """Return masked OAuth token ID for display."""
        if self.oauth_token_id and len(self.oauth_token_id) > 3:
            return f"{self.oauth_token_id[:3]}***"
        return "***"
