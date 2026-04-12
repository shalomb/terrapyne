"""Run models."""

import builtins
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from terrapyne.models.utils import parse_iso_datetime


class RunStatus(StrEnum):
    """TFC run status values (based on live API feedback)."""

    # Planning states
    PENDING = "pending"
    FETCHING = "fetching"
    FETCHING_COMPLETED = "fetching_completed"
    PRE_PLAN_RUNNING = "pre_plan_running"
    PRE_PLAN_COMPLETED = "pre_plan_completed"
    QUEUING = "queuing"
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
    POST_PLAN_COMPLETED = "post_plan_completed"  # Usually terminal enough for activity tracking
    CONFIRMED = "confirmed"
    PLANNED_AND_FINISHED = "planned_and_finished"  # Terminal state
    PLANNED_AND_SAVED = "planned_and_saved"  # Terminal state

    # Apply states
    QUEUING_APPLY = "queuing_apply"
    APPLY_QUEUED = "apply_queued"
    APPLYING = "applying"
    APPLIED = "applied"  # Terminal state
    PRE_APPLY_RUNNING = "pre_apply_running"
    PRE_APPLY_COMPLETED = "pre_apply_completed"
    POST_APPLY_RUNNING = "post_apply_running"
    POST_APPLY_COMPLETED = "post_apply_completed"  # Terminal state

    # Drift detection / Health assessment
    ASSESSING = "assessing"
    ASSESSED = "assessed"  # Terminal state for drift detection

    # Sentinel / Policy
    TF_POLICY_CHECKED = "tf_policy_checked"
    TF_POLICY_OVERRIDE = "tf_policy_override"

    # Error/cancel states
    ERRORED = "errored"  # Terminal state
    CANCELED = "canceled"  # Terminal state
    FORCE_CANCELED = "force_canceled"  # Terminal state
    DISCARDED = "discarded"  # Terminal state

    @staticmethod
    def get_active_statuses() -> builtins.list[str]:
        """Get list of active (non-terminal) statuses."""
        return [
            RunStatus.PENDING,
            RunStatus.FETCHING,
            RunStatus.FETCHING_COMPLETED,
            RunStatus.PRE_PLAN_RUNNING,
            RunStatus.PRE_PLAN_COMPLETED,
            RunStatus.QUEUING,
            RunStatus.PLAN_QUEUED,
            RunStatus.PLANNING,
            RunStatus.COST_ESTIMATING,
            RunStatus.COST_ESTIMATED,
            RunStatus.POLICY_CHECKING,
            RunStatus.POLICY_OVERRIDE,
            RunStatus.POLICY_SOFT_FAILED,
            RunStatus.POLICY_CHECKED,
            RunStatus.POST_PLAN_RUNNING,
            RunStatus.CONFIRMED,
            RunStatus.QUEUING_APPLY,
            RunStatus.APPLY_QUEUED,
            RunStatus.APPLYING,
            RunStatus.PRE_APPLY_RUNNING,
            RunStatus.PRE_APPLY_COMPLETED,
            RunStatus.POST_APPLY_RUNNING,
            RunStatus.ASSESSING,
        ]

    @property
    def is_awaiting_approval(self) -> bool:
        """Check if status indicates the run is waiting for manual approval."""
        return self in {
            self.PLANNED,
            self.COST_ESTIMATED,
            self.POLICY_CHECKED,
            self.POLICY_SOFT_FAILED,
        }

    @property
    def is_terminal(self) -> bool:
        """Check if status is terminal (run complete)."""
        return self in {
            self.APPLIED,
            self.PLANNED_AND_FINISHED,
            self.PLANNED_AND_SAVED,
            self.POST_PLAN_COMPLETED,
            self.POST_APPLY_COMPLETED,
            self.ASSESSED,
            self.ERRORED,
            self.CANCELED,
            self.FORCE_CANCELED,
            self.DISCARDED,
        }

    @property
    def is_successful(self) -> bool:
        """Check if status indicates success or a successful plan ready for approval."""
        return (
            self
            in {
                self.APPLIED,
                self.PLANNED_AND_FINISHED,
                self.PLANNED_AND_SAVED,
                self.POST_APPLY_COMPLETED,
            }
            or self.is_awaiting_approval
        )

    @property
    def is_error(self) -> bool:
        """Check if status indicates error."""
        return self == self.ERRORED

    @property
    def emoji(self) -> str:
        """Get status emoji."""
        if self.is_successful:
            return "🟢"
        if self.is_error:
            return "🔴"
        if self in {self.CANCELED, self.FORCE_CANCELED, self.DISCARDED}:
            return "⚪"
        return "🟡"


class Run(BaseModel):
    """Run model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    status: RunStatus
    message: str | None = None
    created_at: datetime | None = Field(None, alias="created-at")
    auto_apply: bool = Field(False, alias="auto-apply")
    is_destroy: bool = Field(False, alias="is-destroy")

    # Relationships
    workspace_id: str | None = None
    plan_id: str | None = None
    apply_id: str | None = None
    configuration_version_id: str | None = None

    # Enrichment: Commit info (extracted from configuration-version)
    commit_sha: str | None = Field(None, alias="commit-sha")
    commit_message: str | None = Field(None, alias="commit-message")
    commit_author: str | None = Field(None, alias="commit-author")

    # Resource change counts
    additions: int | None = None
    changes: int | None = None
    destructions: int | None = None

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], included: list[dict[str, Any]] | None = None
    ) -> "Run":
        """Create run from TFC API response.

        Args:
            data: API response data dict
            included: Optional list of included resources from the API response

        Returns:
            Run instance

        Raises:
            KeyError: If required fields (id, status) are missing
        """
        # Validate core fields are present
        if "id" not in data:
            raise KeyError("Run API response missing 'id'")

        attrs = data.get("attributes", {})
        if "status" not in attrs:
            raise KeyError(f"Run {data['id']} API response missing 'status'")

        # Extract relationships
        workspace_id = None
        plan_id = None
        apply_id = None
        configuration_version_id = None

        rels = data.get("relationships", {})
        if "workspace" in rels:
            workspace_id = rels["workspace"].get("data", {}).get("id")
        if "plan" in rels:
            plan_id = rels["plan"].get("data", {}).get("id")
        if "apply" in rels:
            apply_id = rels["apply"].get("data", {}).get("id")
        if "configuration-version" in rels:
            configuration_version_id = rels["configuration-version"].get("data", {}).get("id")

        # Extract commit info and resource counts from included resources
        commit_sha = None
        commit_message = None
        commit_author = None
        additions = attrs.get("resource-additions")
        changes = attrs.get("resource-changes")
        destructions = attrs.get("resource-destructions")

        if included:
            for item in included:
                # Commit info
                if (
                    item.get("type") == "configuration-versions"
                    and item.get("id") == configuration_version_id
                ):
                    cv_attrs = item.get("attributes", {})
                    if "ingress-attributes" in cv_attrs:
                        ingress = cv_attrs["ingress-attributes"]
                        commit_sha = ingress.get("commit-sha")
                        commit_message = ingress.get("commit-message")
                        commit_author = ingress.get("commit-author")

                # Resource counts from plan (overrides run attributes if present)
                if item.get("type") == "plans" and item.get("id") == plan_id:
                    p_attrs = item.get("attributes", {})
                    if p_attrs.get("resource-additions") is not None:
                        additions = p_attrs.get("resource-additions")
                    if p_attrs.get("resource-changes") is not None:
                        changes = p_attrs.get("resource-changes")
                    if p_attrs.get("resource-destructions") is not None:
                        destructions = p_attrs.get("resource-destructions")

        return cls.model_construct(
            id=data["id"],
            status=RunStatus(attrs["status"]),
            message=attrs.get("message"),
            created_at=parse_iso_datetime(attrs.get("created-at")),
            auto_apply=attrs.get("auto-apply", False),
            is_destroy=attrs.get("is-destroy", False),
            workspace_id=workspace_id,
            plan_id=plan_id,
            apply_id=apply_id,
            configuration_version_id=configuration_version_id,
            commit_sha=commit_sha,
            commit_message=commit_message,
            commit_author=commit_author,
            additions=additions,
            changes=changes,
            destructions=destructions,
        )

    @property
    def resource_additions(self) -> int | None:
        """Extract resource additions from plan summary."""
        return self.additions

    @property
    def resource_changes(self) -> int | None:
        """Extract resource changes from plan summary."""
        return self.changes

    @property
    def resource_destructions(self) -> int | None:
        """Extract resource destructions from plan summary."""
        return self.destructions

    @property
    def is_awaiting_approval(self) -> bool:
        """Check if run is waiting for human approval."""
        return self.status.is_awaiting_approval

    @property
    def status_display(self) -> str:
        """Get formatted status string with emoji."""
        return f"{self.status.emoji} {self.status.value}"

    @property
    def change_summary(self) -> str:
        """Get short summary of changes (e.g., '+1 ~2 -0')."""
        adds = self.resource_additions or 0
        changes = self.resource_changes or 0
        destroys = self.resource_destructions or 0

        if adds == 0 and changes == 0 and destroys == 0:
            return "No changes"

        return f"+{adds} ~{changes} -{destroys}"
