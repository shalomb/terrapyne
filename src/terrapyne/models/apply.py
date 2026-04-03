"""Apply models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Apply(BaseModel):
    """Terraform Cloud apply model."""

    id: str
    status: str
    log_read_url: str | None = Field(None, alias="log-read-url")
    resource_additions: int | None = Field(None, alias="resource-additions")
    resource_changes: int | None = Field(None, alias="resource-changes")
    resource_destructions: int | None = Field(None, alias="resource-destructions")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Apply":
        """Create apply from TFC API response."""
        attrs = data.get("attributes", {})
        return cls.model_construct(
            id=data["id"],
            status=attrs.get("status", "unknown"),
            log_read_url=attrs.get("log-read-url"),
            resource_additions=attrs.get("resource-additions"),
            resource_changes=attrs.get("resource-changes"),
            resource_destructions=attrs.get("resource-destructions"),
        )
