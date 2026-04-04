"""Project CLI commands."""

from __future__ import annotations

import contextlib
import sys

import typer
from rich.console import Console

from terrapyne.api.client import TFCClient
from terrapyne.api.projects import ProjectAPI
from terrapyne.api.workspaces import WorkspaceAPI
from terrapyne.cli.utils import (
    handle_cli_errors,
    resolve_project_context,
    validate_context,
)
from terrapyne.utils.rich_tables import (
    render_project_detail,
    render_project_team_access,
    render_projects,
)

app = typer.Typer(help="Project discovery and management commands")
console = Console()


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command(name="list")
@handle_cli_errors
def list_projects(
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search projects by name"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of projects to display"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
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

    if output_format == "json":
        from terrapyne.cli.utils import emit_json

        emit_json(
            [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "created_at": p.created_at,
                    "resource_count": p.resource_count,
                }
                for p in projects
            ]
        )
        return

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
    workspace_counts: dict[str, int] = {}  # skip expensive count for find results

    render_projects(
        projects,
        f"Projects matching '{pattern}' in {org}",
        total_count=total_count,
        workspace_counts=workspace_counts,
    )


@app.command(name="show")
@handle_cli_errors
def show_project(
    project_name: str | None = typer.Argument(
        None, help="Project name (auto-detected from context if available)"
    ),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
) -> None:
    """Show project details and workspaces."""
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # Resolve project from name or context
        org, project = resolve_project_context(client, org, project_name)

        workspace_api = WorkspaceAPI(client)

        # Get workspaces in project
        workspaces_iter, _ = workspace_api.list(org, project_id=project.id)
        workspaces = list(workspaces_iter)

        render_project_detail(project, workspaces)


@app.command(name="teams")
@handle_cli_errors
def list_project_teams(
    project_name: str | None = typer.Argument(
        None, help="Project name (auto-detected from context if available)"
    ),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
) -> None:
    """List team access for a project.

    Shows which teams have access to the project and their permission levels.

    Examples:
        terrapyne project teams 92813-MAN
        terrapyne project teams myproject -o my-org
        # Show teams for current workspace's project
        terrapyne project teams
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # Resolve project from name or context
        org, project = resolve_project_context(client, org, project_name)

        project_api = ProjectAPI(client)

        # List team access
        team_access_list = project_api.list_team_access(project.id)

        render_project_team_access(team_access_list, project.name)


@app.command("costs")
@handle_cli_errors
def project_costs(
    project_name: str | None = typer.Argument(
        None, help="Project name (auto-detected from context if available)"
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """Aggregate cost estimates across a project."""
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # Resolve project from name or context
        org, project = resolve_project_context(client, org, project_name)

        workspaces, _ = client.workspaces.list(org, project_id=project.id)

        total_monthly = 0.0

        for ws in workspaces:
            cost_estimate = client.runs.get_latest_cost_estimate(ws.id)
            if cost_estimate:
                cost = cost_estimate.get("monthly", "0.0")
                with contextlib.suppress(ValueError):
                    total_monthly += float(cost)

        console.print(f"Total project estimated monthly cost: ${total_monthly:.2f}")
