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
        workspace_count = str(len(repo["workspaces"]))

        if verbose:
            workspace_names = ", ".join(repo["workspaces"])
            table.add_row(
                repo["identifier"],
                workspace_count,
                workspace_names,
                repo["url"] or "N/A",
            )
        else:
            table.add_row(
                repo["identifier"],
                workspace_count,
                repo["url"] or "N/A",
            )

    console.print(table)

    repo_word = "repository" if len(repos) == 1 else "repositories"
    console.print(f"\n[dim]Showing: {len(repos)} {repo_word}[/dim]")


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
        workspace_counts: Optional dict mapping project_id -> actual workspace count
    """
    renderer = ProjectTableRenderer(workspace_counts=workspace_counts)
    renderer.render(projects, title=title, total_count=total_count, console_instance=console)


def render_project_detail(project: Project, workspaces: Sequence[Workspace]) -> None:
    """Render detailed project information with workspace list.

    Args:
        project: Project instance
        workspaces: List of workspace instances in the project
    """
    renderer = ProjectDetailRenderer(workspace_count=len(workspaces))
    renderer.render(project, console_instance=console)

    # Render workspaces list
    if workspaces:
        console.print()  # Blank line for separation
        render_workspaces(workspaces, f"Workspaces in {project.name}")
    else:
        console.print("\n[dim](No workspaces)[/dim]")


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
    table.add_column("Project Settings", justify="center")
    table.add_column("Project Teams", justify="center")
    table.add_column("Workspace Create", justify="center")

    for access in team_access_list:
        # Team name with ID fallback
        if access.team_name:
            team_display = f"{access.team_name}\n[dim]{access.team_id}[/dim]"
        else:
            team_display = access.team_id

        # Access level with color coding
        access_colors = {
            "read": "blue",
            "write": "green",
            "maintain": "yellow",
            "admin": "red",
            "custom": "magenta",
        }
        access_color = access_colors.get(access.access, "white")
        access_display = f"[{access_color}]{access.access.upper()}[/{access_color}]"

        # Project permissions
        proj_settings = "N/A"
        proj_teams = "N/A"
        if access.project_access:
            proj_settings = access.project_access.settings
            proj_teams = access.project_access.teams

        # Workspace create permission
        workspace_create = "N/A"
        if access.workspace_access:
            workspace_create = "✅" if access.workspace_access.create else "❌"

        table.add_row(
            team_display,
            access_display,
            proj_settings,
            proj_teams,
            workspace_create,
        )

    console.print(table)
    console.print(f"\n[dim]Showing: {len(team_access_list)} team(s)[/dim]")
