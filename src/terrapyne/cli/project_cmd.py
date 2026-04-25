"""Project CLI commands."""

from __future__ import annotations

import contextlib
import sys

import typer

from terrapyne.cli.utils import (
    console,
    get_client,
    handle_cli_errors,
    resolve_project_context,
    validate_context,
)
from terrapyne.rendering.rich_tables import (
    render_project_detail,
    render_project_team_access,
    render_projects,
)

app = typer.Typer(help="Project discovery and management commands")


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def project_list(
    ctx: typer.Context,
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of projects to show"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
) -> None:
    """List all projects in the organization."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        projects_iter, total_count = client.projects.list(org)
        projects = list(projects_iter)[:limit]

        if not projects:
            if output_format == "json":
                from terrapyne.cli.utils import emit_json

                emit_json([])
                return
            console.print(f"[yellow]No projects found in {org}[/yellow]")
            return

        if output_format == "json":
            from terrapyne.cli.utils import emit_json

            emit_json([p.model_dump() for p in projects])
            return

        # Fetch workspace counts for each project
        # In a real scenario with many projects, we might want to optimize this
        workspace_counts: dict[str, int] = {}
        for project in projects:
            _, count = client.workspaces.list(org, project_id=project.id)
            workspace_counts[project.id] = count or 0

        render_projects(
            projects,
            f"Projects in {org}",
            total_count=total_count,
            workspace_counts=workspace_counts,
        )


@app.command(name="find")
@handle_cli_errors
def find_projects(
    ctx: typer.Context,
    pattern: str = typer.Argument(
        ..., help="Search pattern (supports wildcards: *-MAN, 10234-*, *235*)"
    ),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of projects to display"),
) -> None:
    """Find projects matching a pattern."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        projects_iter, total_count = client.projects.list(org, search=pattern)
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
    ctx: typer.Context,
    project_name: str | None = typer.Argument(
        None, help="Project name (auto-detected from context if available)"
    ),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
) -> None:
    """Show project details and workspaces."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        # Resolve project from name or context
        org, project = resolve_project_context(client, org, project_name)

        # Get workspaces in project
        # Include latest_run to count active runs across project (Task 1c)
        workspaces_iter, _ = client.workspaces.list(
            org, project_id=project.id, include="latest_run"
        )
        workspaces = list(workspaces_iter)

        # Count active runs across all workspaces in project (Task 1c)
        from terrapyne.models.run import RunStatus

        active_statuses = RunStatus.get_active_statuses()
        # Add 'awaiting approval' statuses to active count for health dashboard
        active_statuses.extend(
            [
                RunStatus.PLANNED,
                RunStatus.COST_ESTIMATED,
                RunStatus.POLICY_CHECKED,
                RunStatus.POLICY_SOFT_FAILED,
            ]
        )

        active_runs_count = 0
        for ws in workspaces:
            if ws.latest_run and ws.latest_run.status in active_statuses:
                active_runs_count += 1

        if output_format == "json":
            from terrapyne.cli.utils import emit_json

            emit_json(
                {
                    "id": project.id,
                    "name": project.name,
                    "organization": org,
                    "workspace_count": len(workspaces),
                    "active_runs_count": active_runs_count,
                    "workspaces": [
                        {
                            "id": ws.id,
                            "name": ws.name,
                            "latest_run": ws.latest_run.id if ws.latest_run else None,
                            "status": ws.latest_run.status if ws.latest_run else None,
                        }
                        for ws in workspaces
                    ],
                }
            )
            return

        render_project_detail(project, workspaces, active_runs_count=active_runs_count)


@app.command(name="teams")
@handle_cli_errors
def list_project_teams(
    ctx: typer.Context,
    project_name: str | None = typer.Argument(
        None, help="Project name (auto-detected from context if available)"
    ),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
) -> None:
    """List teams with access to a project."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        org, project = resolve_project_context(client, org, project_name)

        team_access = client.projects.list_team_access(project.id)
        render_project_team_access(team_access, project.name)


@app.command(name="costs")
@handle_cli_errors
def project_costs(
    ctx: typer.Context,
    project_name: str = typer.Argument(..., help="Project name"),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """Aggregate cost estimates across a project."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        project = client.projects.get_by_name(project_name, org)
        workspaces_iter, _ = client.workspaces.list(org, project_id=project.id)
        workspaces = list(workspaces_iter)

        total_monthly = 0.0

        for ws in workspaces:
            cost_estimate = client.runs.get_latest_cost_estimate(ws.id)
            if cost_estimate:
                proposed = cost_estimate.get("proposed-monthly-cost") or cost_estimate.get(
                    "monthly", "0.0"
                )
                with contextlib.suppress(ValueError):
                    total_monthly += float(proposed)

        console.print(f"Total project estimated monthly cost: ${total_monthly:,.2f}")
