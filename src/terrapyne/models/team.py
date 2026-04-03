"""Team model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from terrapyne.models.utils import parse_iso_datetime


class Team(BaseModel):
    """Terraform Cloud team model."""

    id: str
    name: str
    description: str | None = None
    created_at: datetime | None = Field(None, alias="created-at")
    updated_at: datetime | None = Field(None, alias="updated-at")
    members_count: int | None = Field(None, alias="users-count")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> Team:
        """Create Team instance from TFC API response.

        Args:
            data: API response dict with 'id', 'type', 'attributes'

        Returns:
            Team instance
        """
        attrs = data.get("attributes", {})

        # Parse datetime fields if present
        created_at = None
        if attrs.get("created-at"):
            created_at = parse_iso_datetime(attrs["created-at"])

        updated_at = None
        if attrs.get("updated-at"):
            updated_at = parse_iso_datetime(attrs["updated-at"])

        return cls.model_construct(
            id=data["id"],
            name=attrs.get("name", ""),
            description=attrs.get("description"),
            created_at=created_at,
            updated_at=updated_at,
            members_count=attrs.get("users-count"),
        )
