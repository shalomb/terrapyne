"""Terraform Cloud state version models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from terrapyne.models.utils import parse_iso_datetime


class StateVersionOutput(BaseModel):
    """A single output from a state version."""

    name: str
    value: Any = None
    type: str | None = None
    sensitive: bool = False


class StateVersion(BaseModel):
    """Terraform Cloud state version."""

    id: str
    serial: int = 0
    created_at: datetime | None = Field(None, alias="created-at")
    status: str | None = None
    download_url: str | None = Field(None, alias="hosted-state-download-url")
    resource_count: int = Field(0, alias="resource-count")
    providers_count: int = Field(0, alias="providers-count")
    resources_processed: bool = Field(False, alias="resources-processed")
    run_id: str | None = None

    class Config:
        populate_by_name = True

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> StateVersion:
        attrs = data.get("attributes", {})
        run_id = None
        relationships = data.get("relationships", {})
        if relationships.get("run", {}).get("data"):
            run_id = relationships["run"]["data"].get("id")

        return cls.model_construct(
            id=data["id"],
            serial=attrs.get("serial", 0),
            created_at=parse_iso_datetime(attrs.get("created-at")),
            status=attrs.get("status"),
            download_url=attrs.get("hosted-state-download-url"),
            resource_count=attrs.get("resource-count", 0),
            providers_count=attrs.get("providers-count", 0),
            resources_processed=attrs.get("resources-processed", False),
            run_id=run_id,
        )
