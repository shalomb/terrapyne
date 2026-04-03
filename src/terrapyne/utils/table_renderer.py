"""TableRenderer base class for unified table rendering.

This module provides a base class for rendering TFC entities as Rich tables.
It consolidates the logic from the 11+ render_* functions into a cohesive pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Generic, TypeVar

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from terrapyne.models.plan import Plan
    from terrapyne.models.project import Project
    from terrapyne.models.run import Run
    from terrapyne.models.workspace import Workspace

T = TypeVar("T")  # Generic entity type

console = Console()


class TableRenderer(ABC, Generic[T]):
    """Abstract base class for table renderers.

    Subclasses must implement:
    - get_title(): Return the table title
    - get_columns(): Return list of column names
    - get_row(entity): Return list of values for the entity
    """

    def get_title(self, count: int | None = None) -> str:
        """Get table title. Can be overridden by subclasses."""
        return "Table"

    @abstractmethod
    def get_columns(self) -> list[str]:
        """Return list of column names."""
        pass

    @abstractmethod
    def get_row(self, entity: T) -> list[str]:
        """Return list of values for a single entity."""
        pass

    def add_columns(self, table: Table) -> None:  # type: ignore[name-defined]
        """Add columns to table. Override to customise width/wrap per column."""
        for column in self.get_columns():
            table.add_column(column, style="cyan", no_wrap=False)

    def render(
        self,
        entities: Sequence[T],
        title: str | None = None,
        total_count: int | None = None,
        console_instance: Console | None = None,
    ) -> None:
        """Render entities as a Rich table.

        Args:
            entities: List of entities to render
            title: Optional custom table title
            total_count: Optional total count for pagination info
            console_instance: Optional Console instance (defaults to global console)
        """
        table = Table(
            title=title or self.get_title(),
            show_header=True,
            header_style="bold magenta",
        )

        # Add columns — subclasses may override add_columns() for custom widths
        self.add_columns(table)

        # Add rows
        for entity in entities:
            table.add_row(*self.get_row(entity))

        # Print table
        out_console = console_instance or console
        out_console.print(table)

        # Print pagination info if provided
        if total_count is not None:
            out_console.print(f"\n[dim]Showing: {len(entities)} of {total_count}[/dim]")
        else:
            out_console.print(f"\n[dim]Showing: {len(entities)}[/dim]")


class DetailRenderer(ABC, Generic[T]):
    """Abstract base class for detail renderers (single entity)."""

    @abstractmethod
    def get_title(self, entity: T) -> str:
        """Get title for the detail table."""
        pass

    @abstractmethod
    def get_fields(self, entity: T) -> list[tuple[str, str]]:
        """Return list of (property, value) tuples."""
        pass

    def render(self, entity: T, console_instance: Console | None = None) -> None:
        """Render a single entity with all its details.

        Args:
            entity: Entity to render
            console_instance: Optional Console instance
        """
        table = Table(title=self.get_title(entity), show_header=False, box=None)

        table.add_column("Property", style="bold cyan", width=25)
        table.add_column("Value")

        for property_name, value in self.get_fields(entity):
            table.add_row(property_name, value)

        out_console = console_instance or console
        out_console.print(table)


# Concrete implementations for each entity type


class WorkspaceTableRenderer(TableRenderer["Workspace"]):  # type: ignore
    """Render workspace list as a table."""

    def get_title(self, count: int | None = None) -> str:
        return "Workspaces"

    def get_columns(self) -> list[str]:
        return ["Workspace", "Environment", "TF Version", "VCS Branch", "Locked"]

    def get_row(self, entity: Workspace) -> list[str]:  # type: ignore
        from terrapyne.models.workspace import Workspace

        if not isinstance(entity, Workspace):
            return []

        vcs_branch = (entity.vcs_repo.branch or "N/A") if entity.vcs_repo else "N/A"
        return [
            entity.name,
            entity.environment or "-",
            entity.terraform_version or "-",
            vcs_branch,
            "🔒" if entity.locked else "",
        ]


class WorkspaceDetailRenderer(DetailRenderer["Workspace"]):  # type: ignore
    """Render workspace detail information."""

    def get_title(self, entity: Workspace) -> str:  # type: ignore
        from terrapyne.models.workspace import Workspace

        if not isinstance(entity, Workspace):
            return "Workspace"
        return f"Workspace: {entity.name}"

    def get_fields(self, entity: Workspace) -> list[tuple[str, str]]:  # type: ignore
        from terrapyne.models.workspace import Workspace

        if not isinstance(entity, Workspace):
            return []

        fields: list[tuple[str, str]] = [
            ("ID", entity.id),
            ("Name", entity.name),
        ]

        if entity.project_name:
            fields.append(("Project", entity.project_name))
        elif entity.project_id:
            fields.append(("Project ID", entity.project_id))

        if entity.environment:
            fields.append(("Environment", entity.environment))

        fields.extend(
            [
                ("Terraform Version", entity.terraform_version or "N/A"),
                ("Working Directory", entity.working_directory or "/"),
                ("Execution Mode", entity.execution_mode or "remote"),
                (
                    "Auto Apply",
                    "✅ Enabled" if entity.auto_apply else "❌ Disabled",
                ),
                ("Locked", "🔒 Yes" if entity.locked else "No"),
            ]
        )

        if entity.created_at:
            fields.append(("Created", self._format_datetime(entity.created_at)))

        if entity.tag_names:
            fields.append(("", ""))
            fields.append(("Tags", ", ".join(entity.tag_names)))

        return fields

    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        """Format datetime for display."""
        return dt.strftime("%Y-%m-%d %H:%M:%S")


class RunTableRenderer(TableRenderer["Run"]):  # type: ignore
    """Render run list as a table."""

    def get_title(self, count: int | None = None) -> str:
        return "Runs"

    def get_columns(self) -> list[str]:
        return ["Run ID", "Status", "Created", "Changes", "Created By"]

    def add_columns(self, table: Table) -> None:  # type: ignore[override]
        """Add columns with Run ID forced to no_wrap so IDs are never truncated."""
        # Run ID: fixed width, no wrapping — must be copy-pasteable
        table.add_column("Run ID", style="cyan", no_wrap=True, min_width=22)
        table.add_column("Status", style="cyan", no_wrap=False)
        table.add_column("Created", style="cyan", no_wrap=False)
        table.add_column("Changes", style="cyan", no_wrap=False)
        table.add_column("Created By", style="cyan", no_wrap=False)

    def get_row(self, entity: Run) -> list[str]:  # type: ignore
        from terrapyne.models.run import Run

        if not isinstance(entity, Run):
            return []

        created_str = entity.created_at.strftime("%Y-%m-%d %H:%M:%S") if entity.created_at else "-"

        changes = sum(
            [
                entity.resource_additions or 0,
                entity.resource_changes or 0,
                entity.resource_destructions or 0,
            ]
        )

        return [
            entity.id,
            entity.status,
            created_str,
            str(changes),
            entity.message or "-",
        ]


class RunDetailRenderer(DetailRenderer["Run"]):  # type: ignore
    """Render run detail information."""

    def __init__(
        self,
        workspace_name: str | None = None,
        organization: str | None = None,
        plan: Plan | None = None,  # type: ignore
    ) -> None:
        """Initialize renderer with optional workspace name, organization, and plan."""
        self.workspace_name = workspace_name
        self.organization = organization
        self.plan = plan

    def get_title(self, entity: Run) -> str:  # type: ignore
        from terrapyne.models.run import Run

        if not isinstance(entity, Run):
            return "Run"
        return f"Run: {entity.id}"

    def get_fields(self, entity: Run) -> list[tuple[str, str]]:  # type: ignore
        from terrapyne.models.run import Run

        if not isinstance(entity, Run):
            return []

        fields: list[tuple[str, str]] = [
            ("ID", entity.id),
            (
                "Status",
                f"{entity.status.emoji} {entity.status.value}"
                if hasattr(entity.status, "emoji")
                else str(entity.status),
            ),
        ]

        if self.workspace_name:
            fields.append(("Workspace", self.workspace_name))

        if entity.message:
            fields.append(("Message", entity.message))

        if entity.created_at:
            fields.append(
                (
                    "Created",
                    entity.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

        # Separator before changes
        fields.append(("", ""))

        # Resource changes (from plan if available, otherwise from run)
        resource_additions = 0
        resource_changes = 0
        resource_destructions = 0

        if self.plan:
            resource_additions = self.plan.resource_additions
            resource_changes = self.plan.resource_changes
            resource_destructions = self.plan.resource_destructions
        else:
            resource_additions = entity.resource_additions or 0
            resource_changes = entity.resource_changes or 0
            resource_destructions = entity.resource_destructions or 0

        fields.extend(
            [
                (
                    "Resource Additions",
                    str(resource_additions),
                ),
                ("Resource Changes", str(resource_changes)),
                (
                    "Resource Destructions",
                    str(resource_destructions),
                ),
            ]
        )

        # Separator before run type
        fields.append(("", ""))

        # Run type
        if entity.is_destroy:
            run_type = "destroy"
        elif entity.auto_apply:
            run_type = "plan-and-apply"
        else:
            run_type = "plan-only"
        fields.append(("Type", run_type))

        if entity.auto_apply is not None:
            auto_apply_display = "✅ Yes" if entity.auto_apply else "❌ No"
            fields.append(("Auto Apply", auto_apply_display))

        # Add URL at the end if we have organization and workspace
        if self.organization and self.workspace_name:
            from terrapyne.utils.browser import get_run_url

            url = get_run_url(self.organization, self.workspace_name, entity.id)
            fields.append(("", ""))  # Separator
            fields.append(("URL", url))

        return fields


class ProjectTableRenderer(TableRenderer["Project"]):  # type: ignore
    """Render project list as a table."""

    def __init__(self, workspace_counts: dict[str, int] | None = None) -> None:
        """Initialize renderer with optional workspace counts."""
        self.workspace_counts = workspace_counts or {}

    def get_title(self, count: int | None = None) -> str:
        return "Projects"

    def get_columns(self) -> list[str]:
        return ["Project", "Description", "Workspaces", "Created"]

    def get_row(self, entity: Project) -> list[str]:  # type: ignore
        from terrapyne.models.project import Project

        if not isinstance(entity, Project):
            return []

        created_str = entity.created_at.strftime("%Y-%m-%d") if entity.created_at else "-"

        # Use actual workspace count if provided, otherwise fall back to resource_count
        if entity.id in self.workspace_counts:
            workspace_count = str(self.workspace_counts[entity.id])
        else:
            workspace_count = str(entity.resource_count)

        return [
            entity.name,
            entity.description or "-",
            workspace_count,
            created_str,
        ]


class ProjectDetailRenderer(DetailRenderer["Project"]):  # type: ignore
    """Render project detail information."""

    def __init__(self, workspace_count: int | None = None) -> None:
        """Initialize renderer with optional workspace count."""
        self.workspace_count = workspace_count

    def get_title(self, entity: Project) -> str:  # type: ignore
        from terrapyne.models.project import Project

        if not isinstance(entity, Project):
            return "Project"
        return f"Project: {entity.name}"

    def get_fields(self, entity: Project) -> list[tuple[str, str]]:  # type: ignore
        from terrapyne.models.project import Project

        if not isinstance(entity, Project):
            return []

        fields: list[tuple[str, str]] = [
            ("ID", entity.id),
            ("Name", entity.name),
        ]

        if entity.description:
            fields.append(("Description", entity.description))

        # Use actual workspace count if provided, otherwise fall back to resource_count
        if self.workspace_count is not None:
            fields.append(("Workspaces", str(self.workspace_count)))
        else:
            fields.append(("Workspaces", str(entity.resource_count)))

        if entity.created_at:
            fields.append(
                (
                    "Created",
                    entity.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

        return fields
