"""RunTrigger model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from terrapyne.models.utils import parse_iso_datetime


class RunTrigger(BaseModel):
    """Represents a run trigger relationship between two workspaces."""

    id: str
    source_workspace_id: str
    source_workspace_name: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(
        cls,
        data: dict[str, Any],
        included: list[dict[str, Any]] | None = None,
    ) -> "RunTrigger":
        """Create a RunTrigger from a TFC API response item.

        Args:
            data: Single API resource dict (id, type, attributes, relationships)
            included: Optional list of included resources for name resolution

        Returns:
            RunTrigger instance
        """
        attrs = data.get("attributes", {})
        relationships = data.get("relationships", {})

        source_ws_id = relationships.get("source-workspace", {}).get("data", {}).get("id", "")

        source_ws_name = None
        if included and source_ws_id:
            for item in included:
                if item.get("type") == "workspaces" and item.get("id") == source_ws_id:
                    source_ws_name = item.get("attributes", {}).get("name")
                    break

        return cls.model_construct(
            id=data["id"],
            source_workspace_id=source_ws_id,
            source_workspace_name=source_ws_name,
            created_at=parse_iso_datetime(attrs.get("created-at")),
        )
