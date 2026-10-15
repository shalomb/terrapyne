"""VCS CLI commands."""

import typer

from terrapyne.cli.context_helpers import get_client, validate_context
from terrapyne.cli.error_handlers import handle_cli_errors
from terrapyne.rendering.logging import console

app = typer.Typer(help="VCS configuration and repository discovery")


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def vcs_list(
    ctx: typer.Context,
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """List VCS connections in an organization."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        # VCSAPI has list_connections() method
        connections = client.vcs.list_connections(org)
        if not connections:
            console.print(f"[yellow]No VCS connections found in {org}[/yellow]")
            return

        from terrapyne.rendering.rich_tables import render_vcs_connections

        render_vcs_connections(connections, f"VCS Connections in {org}")


@app.command("repos")
@handle_cli_errors
def vcs_repos(
    ctx: typer.Context,
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """List available repositories for all VCS connections."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        connections = client.vcs.list_connections(org)
        if not connections:
            console.print(f"[yellow]No VCS connections found in {org}[/yellow]")
            return

        for conn in connections:
            console.print(
                f"\n[bold cyan]Connection: {conn.identifier} ({conn.service_provider})[/bold cyan]"
            )
            try:
                if not conn.id:
                    continue
                repos: list[dict] = client.vcs.list_repositories(conn.id)
                if not repos:
                    console.print("  [dim](No repositories found)[/dim]")
                    continue

                for repo in repos:
                    console.print(f"  • {repo['identifier']}")
            except Exception as e:
                console.print(f"  [red]Error fetching repositories: {e}[/red]")


@app.command("show")
@handle_cli_errors
def vcs_show(
    ctx: typer.Context,
    workspace: str | None = typer.Argument(None, help="Workspace name (auto-detected if omitted)"),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """Show VCS configuration for a workspace."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        # ws_name is checked by validate_context(require_workspace=True)
        if not ws_name:
            raise typer.Exit(1)

        ws = client.workspaces.get(ws_name, org)
        if not ws.vcs_repo:
            console.print(f"[yellow]Workspace '{ws_name}' has no VCS configuration.[/yellow]")
            return

        from terrapyne.rendering.rich_tables import render_workspace_vcs

        render_workspace_vcs(ws)


@app.command("set-repo")
@handle_cli_errors
def vcs_set_repo(
    ctx: typer.Context,
    workspace: str = typer.Argument(..., help="Workspace name"),
    identifier: str = typer.Argument(..., help="New repository identifier (owner/repo)"),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show the change without sending it to Terraform Cloud"
    ),
):
    """Repoint a workspace's VCS repository, keeping its OAuth token and branch.

    Examples:
        # Preview, then apply, after a GitHub repository rename
        tfc vcs set-repo my-ws myorg/new-name --dry-run -o my-org
        tfc vcs set-repo my-ws myorg/new-name -o my-org
    """
    from terrapyne.api.workspaces import validate_repo_identifier

    validate_repo_identifier(identifier)
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        current = client.workspaces.get(workspace, org)
        if not current.vcs_repo:
            raise ValueError(f"Workspace '{workspace}' has no VCS connection.")

        if current.vcs_identifier == identifier:
            console.print(f"{workspace}: already uses {identifier}, nothing to do")
            return

        if dry_run:
            console.print(
                f"[yellow]Dry run:[/yellow] {workspace}: "
                f"{current.vcs_identifier} -> {identifier} (no change sent)"
            )
            return

        client.workspaces.set_vcs_repo(workspace, identifier, org)

    console.print(f"[green]✓[/green] {workspace}: {current.vcs_identifier} -> {identifier}")
