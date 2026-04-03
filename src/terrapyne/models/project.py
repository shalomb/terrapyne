"""Project models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from terrapyne.models.utils import parse_iso_datetime


class Project(BaseModel):
    """Terraform Cloud project model."""

    id: str
    name: str
    description: str | None = None
    created_at: datetime | None = Field(None, alias="created-at")
    resource_count: int = Field(0, alias="resource-count")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> Project:
        """Create project from TFC API response.

        Args:
            data: API response data dict (should contain 'id', 'type', 'attributes')

        Returns:
            Project instance
        """
        attrs = data.get("attributes", {})

        return cls.model_construct(
            id=data["id"],
            name=attrs.get("name", ""),
            description=attrs.get("description"),
            created_at=parse_iso_datetime(attrs.get("created-at")),
            resource_count=attrs.get("resource-count", 0),
        )
