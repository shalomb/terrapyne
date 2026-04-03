"""Workspace variable models."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class WorkspaceVariable(BaseModel):
    """Terraform Cloud workspace variable model."""

    id: str
    key: str
    value: str | None = None
    description: str | None = None
    category: str  # "terraform" or "env"
    hcl: bool = False
    sensitive: bool = False

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "WorkspaceVariable":
        """Create variable from TFC API response.

        Args:
            data: API response data dict

        Returns:
            WorkspaceVariable instance
        """
        attrs = data.get("attributes", {})

        return cls.model_construct(
            id=data["id"],
            key=attrs.get("key", ""),
            value=attrs.get("value"),
            description=attrs.get("description"),
            category=attrs.get("category", "terraform"),
            hcl=attrs.get("hcl", False),
            sensitive=attrs.get("sensitive", False),
        )

    @property
    def display_value(self) -> str:
        """Get display value (masked if sensitive)."""
        if self.sensitive:
            return "••••••••"
        return self.value or ""

    @property
    def is_terraform_var(self) -> bool:
        """Check if this is a Terraform variable."""
        return self.category == "terraform"

    @property
    def is_env_var(self) -> bool:
        """Check if this is an environment variable."""
        return self.category == "env"
