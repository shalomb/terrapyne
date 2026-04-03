"""Plan models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Plan(BaseModel):
    """Terraform Cloud plan model."""

    id: str
    status: str
    log_read_url: str | None = Field(None, alias="log-read-url")
    has_changes: bool = Field(False, alias="has-changes")
    resource_additions: int = Field(0, alias="resource-additions")
    resource_changes: int = Field(0, alias="resource-changes")
    resource_destructions: int = Field(0, alias="resource-destructions")
    resource_imports: int = Field(0, alias="resource-imports")
    action_invocations: int = Field(0, alias="action-invocations")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Plan":
        """Create plan from TFC API response.

        Args:
            data: API response data dict

        Returns:
            Plan instance
        """
        attrs = data.get("attributes", {})

        return cls.model_construct(
            id=data["id"],
            status=attrs.get("status", "unknown"),
            log_read_url=attrs.get("log-read-url"),
            has_changes=attrs.get("has-changes", False),
            resource_additions=attrs.get("resource-additions", 0),
            resource_changes=attrs.get("resource-changes", 0),
            resource_destructions=attrs.get("resource-destructions", 0),
            resource_imports=attrs.get("resource-imports", 0),
            action_invocations=attrs.get("action-invocations", 0),
        )
