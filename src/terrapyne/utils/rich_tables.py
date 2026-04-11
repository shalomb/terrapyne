"""Rich table formatters for TFC data."""

from collections.abc import Sequence
from datetime import UTC, datetime

from rich.console import Console
from rich.table import Table

from terrapyne.models.plan import Plan
from terrapyne.models.project import Project
from terrapyne.models.run import Run
from terrapyne.models.team_access import TeamProjectAccess
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.vcs import VCSConnection
from terrapyne.models.workspace import Workspace
from terrapyne.utils.table_renderer import (
    ProjectDetailRenderer,
    ProjectTableRenderer,
    RunDetailRenderer,
    RunTableRenderer,
    WorkspaceDetailRenderer,
    WorkspaceTableRenderer,
)

console = Console()


def render_workspaces(
    workspaces: Sequence[Workspace], title: str = "Workspaces", total_count: int | None = None
) -> None:
    """Render workspaces as a Rich table.

    Args:
        workspaces: List of workspace instances
        title: Table title
        total_count: Optional total count from API metadata
    """
    renderer = WorkspaceTableRenderer()
    renderer.render(workspaces, title=title, total_count=total_count, console_instance=console)


def render_workspace_detail(workspace: Workspace) -> None:
    """Render detailed workspace information (basic details only).

    Args:
        workspace: Workspace instance
    """
    renderer = WorkspaceDetailRenderer()
    renderer.render(workspace, console_instance=console)


def render_workspace_dashboard(
    workspace: Workspace, latest_run: Run | None = None, active_runs_count: int = 0
) -> None:
    """Render a comprehensive workspace dashboard snapshot.

    Args:
        workspace: Workspace instance
        latest_run: Most recent run instance
        active_runs_count: Number of queued or in-progress runs
    """
    # 1. Main Details Table
    render_workspace_detail(workspace)

    # 2. Health & Activity Snapshot
    console.print()
    snap_table = Table(title="Health & Activity Snapshot", show_header=False, box=None)
    snap_table.add_column("Property", style="bold cyan", width=25)
    snap_table.add_column("Value")

    # Determine health from latest run
    health_status = "Unknown (no runs found)"
    if latest_run:
        status = latest_run.status
        if status.is_successful:
            health_status = f"🟢 Healthy (last run {status.value})"
        elif status.is_error:
            health_status = f"🔴 Unhealthy (last run {status.value})"
        else:
            health_status = f"🟡 Warning (last run {status.value})"

    snap_table.add_row("Health", health_status)
    snap_table.add_row("Queued Runs", str(active_runs_count))

    # VCS Commit Info
    if latest_run and latest_run.commit_sha:
        author = latest_run.commit_author or "Unknown"
        snap_table.add_row("Latest Commit", f"{latest_run.commit_sha[:7]} ({author})")
        snap_table.add_row("Commit Message", latest_run.commit_message or "N/A")

    console.print(snap_table)


def render_workspace_variables(variables: Sequence[WorkspaceVariable]) -> None:
    """Render workspace variables as a Rich table.

    Args:
        variables: List of variable instances
    """
    if not variables:
        console.print("\n[dim](No variables configured)[/dim]")
        return

    console.print()  # Blank line for separation

    table = Table(
        title=f"Variables ({len(variables)})", show_header=True, header_style="bold magenta"
    )

    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Value", max_width=50)
    table.add_column("Category", justify="center")
    table.add_column("Sensitive", justify="center")
    table.add_column("Description", style="dim")

    for var in variables:
        # Category badge
        category_badge = "TF" if var.is_terraform_var else "ENV"
        category_style = "bold blue" if var.is_terraform_var else "bold yellow"

        # Sensitive indicator
        sensitive_indicator = "🔒" if var.sensitive else ""

        # HCL indicator in description
        description = var.description or ""
        if var.hcl:
            description = f"[HCL] {description}" if description else "[HCL]"

        table.add_row(
            var.key,
            var.display_value,
            f"[{category_style}]{category_badge}[/{category_style}]",
            sensitive_indicator,
            description,
        )

    console.print(table)


def render_workspace_vcs(workspace: Workspace) -> None:
    """Render VCS configuration as a separate table.

    Args:
        workspace: Workspace instance
    """
    if not workspace.vcs_repo:
        console.print("\n[dim](No VCS connection)[/dim]")
        return

    console.print()  # Blank line for separation

    table = Table(title="VCS Configuration", show_header=False, box=None)

    table.add_column("Property", style="bold cyan", width=25)
    table.add_column("Value")

    table.add_row("Repository", workspace.vcs_identifier or "N/A")
    table.add_row("Branch", workspace.vcs_branch or "N/A")

    if workspace.vcs_repo.working_directory:
        table.add_row("Working Directory", workspace.vcs_repo.working_directory)

    if workspace.vcs_url:
        table.add_row("Repository URL", workspace.vcs_url)

    if workspace.vcs_repo.oauth_token_id:
        table.add_row("OAuth Token ID", workspace.vcs_repo.oauth_token_id)

    # Show auto-apply status
    table.add_row("Auto Apply", "✅ Enabled" if workspace.auto_apply else "❌ Disabled")

    console.print(table)


def render_runs(runs: Sequence[Run], title: str = "Runs", total_count: int | None = None) -> None:
    """Render runs as a Rich table.

    Args:
        runs: List of run instances
        title: Table title
        total_count: Optional total count from API metadata
    """
    renderer = RunTableRenderer()
    renderer.render(runs, title=title, total_count=total_count, console_instance=console)


def render_run_detail(
    run: Run,
    workspace_name: str | None = None,
    organization: str | None = None,
    plan: "Plan | None" = None,  # type: ignore
) -> None:
    """Render detailed run information.

    Args:
        run: Run instance
        workspace_name: Optional workspace name for display
        organization: Optional organization name for URL construction
        plan: Optional plan with resource counts
    """
    renderer = RunDetailRenderer(
        workspace_name=workspace_name, organization=organization, plan=plan
    )
    renderer.render(run, console_instance=console)


def _format_datetime(dt: datetime) -> str:
    """Format datetime for display.

    Args:
        dt: Datetime object

    Returns:
        Formatted string
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2h ago').

    Args:
        dt: Datetime object

    Returns:
        Relative time string
    """
    now = datetime.now(UTC)
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    delta = now - dt

    if delta.days > 365:
        years = delta.days // 365
        return f"{years}y ago"
    elif delta.days > 30:
        months = delta.days // 30
        return f"{months}mo ago"
    elif delta.days > 0:
        return f"{delta.days}d ago"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours}h ago"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes}m ago"
    else:
        return "just now"


def render_vcs_detail(vcs: VCSConnection, workspace_name: str) -> None:
    """Render VCS connection details.

    Args:
        vcs: VCSConnection instance
        workspace_name: Workspace name for title
    """
    table = Table(title=f"VCS Configuration: {workspace_name}", show_header=False, box=None)

    table.add_column("Property", style="bold cyan", width=25)
    table.add_column("Value")

    table.add_row("Repository", vcs.identifier)

    # Show branch (empty string means default branch)
    branch_display = vcs.branch if vcs.branch else "(default branch)"
    table.add_row("Branch", branch_display)

    if vcs.tags_regex:
        table.add_row("Tags Regex", vcs.tags_regex)

    working_dir = vcs.working_directory or "(root)"
    table.add_row("Working Directory", working_dir)

    if vcs.repository_http_url:
        table.add_row("Repository URL", vcs.repository_http_url)

    if vcs.service_provider:
        table.add_row("Service Provider", vcs.service_provider)

    submodules_display = "✅ Enabled" if vcs.ingress_submodules else "❌ Disabled"
    table.add_row("Ingress Submodules", submodules_display)

    table.add_row("OAuth Token ID", vcs.masked_oauth_token)

    console.print(table)


def render_vcs_repos(repos: list[dict], verbose: bool = False) -> None:
    """Render GitHub repositories table.

    Args:
        repos: List of repository dicts with identifier, url, workspaces
        verbose: Show workspace details
    """
    table = Table(title="GitHub Repositories", show_header=True, header_style="bold magenta")

    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("Workspaces", justify="right")

    if verbose:
        table.add_column("Workspace Names", style="dim", max_width=50)

    table.add_column("URL", style="blue")

    for repo in repos:
        workspace_count = str(len(repo.get("workspaces", [])))
        row = [repo["identifier"], workspace_count]
        if verbose:
            row.append(", ".join(repo.get("workspaces", [])))
        row.append(repo.get("url", "N/A"))
        table.add_row(*row)

    console.print(table)


def render_project_detail(
    project: Project, workspaces: Sequence[Workspace], active_runs_count: int = 0
) -> None:
    """Render project details and workspaces.

    Args:
        project: Project instance
        workspaces: List of workspaces in project
        active_runs_count: Total active runs across all workspaces in project
    """
    # 1. Project details
    renderer = ProjectDetailRenderer()
    renderer.render(project, console_instance=console)

    # 2. Project Snapshot
    console.print()
    snap_table = Table(title="Project Snapshot", show_header=False, box=None)
    snap_table.add_column("Property", style="bold cyan", width=25)
    snap_table.add_column("Value")

    snap_table.add_row("Workspaces", str(len(workspaces)))
    snap_table.add_row("Active Runs", str(active_runs_count))

    # Health summary
    # For now, just show a count of locked workspaces as an indicator
    locked_count = sum(1 for ws in workspaces if ws.locked)
    health_str = "🟢 Healthy"
    if locked_count > 0:
        health_str = f"🟡 Warning ({locked_count} workspaces locked)"
    snap_table.add_row("Status", health_str)

    console.print(snap_table)

    # 3. Workspaces table
    if workspaces:
        console.print()
        render_workspaces(workspaces, title=f"Workspaces in {project.name}")
    else:
        console.print("\n[dim](No workspaces in this project)[/dim]")


def render_projects(
    projects: Sequence[Project],
    title: str = "Projects",
    total_count: int | None = None,
    workspace_counts: dict[str, int] | None = None,
) -> None:
    """Render projects as a Rich table.

    Args:
        projects: List of project instances
        title: Table title
        total_count: Optional total count from API metadata
        workspace_counts: Optional mapping of project ID to workspace count
    """
    renderer = ProjectTableRenderer(workspace_counts=workspace_counts)
    renderer.render(projects, title=title, total_count=total_count, console_instance=console)


def render_project_team_access(
    team_access_list: Sequence[TeamProjectAccess], project_name: str
) -> None:
    """Render project team access as a Rich table.

    Args:
        team_access_list: List of TeamProjectAccess instances
        project_name: Project name for title
    """
    if not team_access_list:
        console.print("\n[dim](No team access configured)[/dim]")
        return

    console.print()  # Blank line for separation

    table = Table(
        title=f"Team Access for {project_name}", show_header=True, header_style="bold magenta"
    )

    table.add_column("Team", style="cyan")
    table.add_column("Access Level")
    table.add_column("Runs")
    table.add_column("Variables")
    table.add_column("State Versions")
    table.add_column("Sentinel")

    for access in team_access_list:
        wa = access.workspace_access
        table.add_row(
            access.team_name or access.team_id,
            access.access,
            wa.runs if wa else "-",
            wa.variables if wa else "-",
            wa.state_versions if wa else "-",
            wa.sentinel_mocks if wa else "-",
        )

    console.print(table)
