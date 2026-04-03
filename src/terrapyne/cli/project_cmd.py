"""Project CLI commands."""

from __future__ import annotations

import sys

import typer
from rich.console import Console

from terrapyne.api.client import TFCClient
from terrapyne.api.projects import ProjectAPI
from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.cli.utils import handle_cli_errors, validate_context
from terrapyne.utils.rich_tables import (
    render_project_detail,
    render_project_team_access,
    render_projects,
)

app = typer.Typer(help="Project discovery and management commands", no_args_is_help=True)
console = Console()


@app.command(name="list")
@handle_cli_errors
def list_projects(
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search projects by name"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of projects to display"),
) -> None:
    """List all projects in organization."""
    org, _ = validate_context(organization)

    client = TFCClient(organization=org)
    project_api = ProjectAPI(client)

    projects_iter, total_count = project_api.list(org, search=search)
    projects = list(projects_iter)[:limit]

    if not projects:
        console.print("[yellow]No projects found[/yellow]")
        sys.exit(0)

    # Get actual workspace counts
    workspace_counts = {} if search else project_api.get_workspace_counts(org)

    render_projects(
        projects,
        f"Projects in {org}",
        total_count=total_count,
        workspace_counts=workspace_counts,
    )


@app.command(name="find")
@handle_cli_errors
def find_projects(
    pattern: str = typer.Argument(
        ..., help="Search pattern (supports wildcards: *-MAN, 10234-*, *235*)"
    ),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of projects to display"),
) -> None:
    """Find projects matching a pattern.

    Supports wildcard patterns:
        *-MAN      - Projects ending with -MAN
        10234-*    - Projects starting with 10234-
        *235*      - Projects containing 235

    Examples:
        terrapyne project find "*-PROD"
        terrapyne project find "myapp-*"
        terrapyne project find "*test*"
    """
    org, _ = validate_context(organization)

    client = TFCClient(organization=org)
    project_api = ProjectAPI(client)

    projects_iter, total_count = project_api.list(org, search=pattern)
    projects = list(projects_iter)[:limit]

    if not projects:
        console.print(f"[yellow]No projects found matching '{pattern}'[/yellow]")
        sys.exit(0)

    # Get actual workspace counts
    workspace_counts = project_api.get_workspace_counts(org)

    render_projects(
        projects,
        f"Projects matching '{pattern}' in {org}",
        total_count=total_count,
        workspace_counts=workspace_counts,
    )


@app.command(name="show")
@handle_cli_errors
def show_project(
    project_name: str = typer.Argument(..., help="Project name"),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
) -> None:
    """Show project details and workspaces."""
    org, _ = validate_context(organization)

    client = TFCClient(organization=org)
    project_api = ProjectAPI(client)
    workspace_api = WorkspaceAPI(client)

    # Get project
    project = project_api.get_by_name(project_name, org)

    # Get workspaces in project
    workspaces_iter, _ = workspace_api.list(org, project_id=project.id)
    workspaces = list(workspaces_iter)

    render_project_detail(project, workspaces)


@app.command(name="teams")
@handle_cli_errors
def list_project_teams(
    project_name: str = typer.Argument(..., help="Project name"),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
) -> None:
    """List team access for a project.

    Shows which teams have access to the project and their permission levels.

    Examples:
        terrapyne project teams 92813-MAN
        terrapyne project teams myproject -o my-org
    """
    org, _ = validate_context(organization)

    client = TFCClient(organization=org)
    project_api = ProjectAPI(client)

    # Get project to retrieve project ID
    project = project_api.get_by_name(project_name, org)

    # List team access
    team_access_list = project_api.list_team_access(project.id)

    render_project_team_access(team_access_list, project.name)
