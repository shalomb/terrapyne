"""Run models."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from terrapyne.models.utils import parse_iso_datetime


class RunStatus(StrEnum):
    """TFC run status values (from go-tfe analysis)."""

    # Planning states
    PENDING = "pending"
    FETCHING = "fetching"
    FETCHING_COMPLETED = "fetching_completed"
    PRE_PLAN_RUNNING = "pre_plan_running"
    PRE_PLAN_COMPLETED = "pre_plan_completed"
    QUEUED = "queued"
    PLAN_QUEUED = "plan_queued"
    PLANNING = "planning"
    PLANNED = "planned"
    COST_ESTIMATING = "cost_estimating"
    COST_ESTIMATED = "cost_estimated"
    POLICY_CHECKING = "policy_checking"
    POLICY_OVERRIDE = "policy_override"
    POLICY_SOFT_FAILED = "policy_soft_failed"
    POLICY_CHECKED = "policy_checked"
    POST_PLAN_RUNNING = "post_plan_running"
    POST_PLAN_COMPLETED = "post_plan_completed"
    CONFIRMED = "confirmed"
    PLANNED_AND_FINISHED = "planned_and_finished"  # Terminal state
    PLANNED_AND_SAVED = "planned_and_saved"  # Terminal state

    # Apply states
    APPLY_QUEUED = "apply_queued"
    APPLYING = "applying"
    APPLIED = "applied"  # Terminal state
    POST_APPLY_RUNNING = "post_apply_running"
    POST_APPLY_COMPLETED = "post_apply_completed"

    # Error/cancel states
    ERRORED = "errored"  # Terminal state
    CANCELED = "canceled"  # Terminal state
    FORCE_CANCELED = "force_canceled"  # Terminal state
    DISCARDED = "discarded"  # Terminal state

    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal (run complete)."""
        return self in {
            self.APPLIED,
            self.PLANNED_AND_FINISHED,
            self.PLANNED_AND_SAVED,
            self.ERRORED,
            self.CANCELED,
            self.FORCE_CANCELED,
            self.DISCARDED,
        }

    @property
    def is_successful(self) -> bool:
        """Check if status indicates success."""
        return self in {self.APPLIED, self.PLANNED_AND_FINISHED, self.PLANNED_AND_SAVED}

    @property
    def is_error(self) -> bool:
        """Check if status indicates error."""
        return self == self.ERRORED

    @property
    def emoji(self) -> str:
        """Get emoji for status."""
        if self.is_successful:
            return "✅"
        elif self.is_error:
            return "❌"
        elif self in {self.CANCELED, self.FORCE_CANCELED, self.DISCARDED}:
            return "🚫"
        elif self in {self.PLANNING, self.APPLYING}:
            return "🔄"
        elif self in {self.PLANNED, self.CONFIRMED, self.POLICY_SOFT_FAILED}:
            return "⏸️"
        else:
            return "⏳"


class Run(BaseModel):
    """Terraform Cloud run model."""

    id: str
    status: RunStatus
    message: str | None = None
    created_at: datetime | None = Field(None, alias="created-at")
    updated_at: datetime | None = Field(None, alias="updated-at")
    auto_apply: bool | None = Field(None, alias="auto-apply")
    is_destroy: bool = Field(False, alias="is-destroy")
    refresh: bool = True
    cost_estimate: dict[str, Any] | None = None
    refresh_only: bool = Field(False, alias="refresh-only")
    replace_addrs: list[str] = Field(default_factory=list, alias="replace-addrs")
    target_addrs: list[str] = Field(default_factory=list, alias="target-addrs")

    # Resource changes (from plan)
    resource_additions: int | None = Field(None, alias="resource-additions")
    resource_changes: int | None = Field(None, alias="resource-changes")
    resource_destructions: int | None = Field(None, alias="resource-destructions")

    # Workspace relationship
    workspace_id: str | None = None

    # Plan relationship
    plan_id: str | None = None

    # Apply relationship
    apply_id: str | None = None

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Run":
        """Create run from TFC API response.

        Args:
            data: API response data dict

        Returns:
            Run instance
        """
        attrs = data.get("attributes", {})

        # Extract workspace ID from relationships
        workspace_id = None
        plan_id = None
        apply_id = None
        relationships = data.get("relationships", {})
        if relationships.get("workspace", {}).get("data"):
            workspace_id = relationships["workspace"]["data"].get("id")
        if relationships.get("plan", {}).get("data"):
            plan_id = relationships["plan"]["data"].get("id")
        if relationships.get("apply", {}).get("data"):
            apply_id = relationships["apply"]["data"].get("id")

        return cls.model_construct(
            id=data["id"],
            status=RunStatus(attrs.get("status", "pending")),
            message=attrs.get("message"),
            created_at=parse_iso_datetime(attrs.get("created-at")),
            updated_at=parse_iso_datetime(attrs.get("updated-at")),
            auto_apply=attrs.get("auto-apply"),
            is_destroy=attrs.get("is-destroy", False),
            refresh=attrs.get("refresh", True),
            refresh_only=attrs.get("refresh-only", False),
            replace_addrs=attrs.get("replace-addrs", []),
            target_addrs=attrs.get("target-addrs", []),
            resource_additions=attrs.get("resource-additions"),
            resource_changes=attrs.get("resource-changes"),
            resource_destructions=attrs.get("resource-destructions"),
            workspace_id=workspace_id,
            plan_id=plan_id,
            apply_id=apply_id,
        )

    @property
    def changes_summary(self) -> str:
        """Get human-readable changes summary (+2 ~1 -0 format)."""
        if self.resource_additions is None:
            return "No changes calculated"

        adds = self.resource_additions or 0
        changes = self.resource_changes or 0
        destroys = self.resource_destructions or 0

        if adds == 0 and changes == 0 and destroys == 0:
            return "No changes"

        return f"+{adds} ~{changes} -{destroys}"
