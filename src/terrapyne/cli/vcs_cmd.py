"""VCS CLI commands."""

from __future__ import annotations

import os
import sys

import typer
from rich.console import Console

from terrapyne.api.client import TFCClient
from terrapyne.api.vcs import VCSAPI
from terrapyne.cli.utils import handle_cli_errors, validate_context
from terrapyne.utils.rich_tables import render_vcs_detail, render_vcs_repos

app = typer.Typer(help="VCS operations (repository, branch management)")
console = Console()


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command(name="show")
@handle_cli_errors
def show_vcs(
    workspace: str | None = typer.Argument(None, help="Workspace name"),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
) -> None:
    """Show VCS configuration for workspace."""
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    client = TFCClient(organization=org)
    vcs_api = VCSAPI(client)

    # Get workspace ID
    workspace_obj = client.workspaces.get(workspace_name or "", org)  # type: ignore[arg-type]

    # Get VCS config
    vcs = vcs_api.get_workspace_vcs(workspace_obj.id)

    if not vcs:
        console.print(f"[yellow]Workspace '{workspace_name}' has no VCS connection[/yellow]")
        sys.exit(0)

    # Render VCS details
    render_vcs_detail(vcs, workspace_name or "")  # type: ignore[arg-type]


@app.command(name="update-branch")
@handle_cli_errors
def update_branch(
    branch: str = typer.Argument(..., help="New branch name"),
    workspace: str | None = typer.Option(None, "-w", "--workspace", help="Workspace name"),
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Skip confirmation"),
) -> None:
    """Update VCS branch for workspace."""
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    client = TFCClient(organization=org)
    vcs_api = VCSAPI(client)

    # Get workspace
    workspace_obj = client.workspaces.get(workspace_name or "", org)  # type: ignore[arg-type]

    # Get current VCS config
    current_vcs = vcs_api.get_workspace_vcs(workspace_obj.id)
    if not current_vcs:
        console.print(f"[red]Error: Workspace '{workspace_name}' has no VCS connection[/red]")
        sys.exit(1)

    # Get OAuth token from environment or use the one from workspace
    oauth_token_id = os.getenv("TFC_VCS_OAUTH_TOKEN") or current_vcs.oauth_token_id
    if not oauth_token_id:
        console.print("[red]Error: Cannot determine OAuth token ID[/red]")
        console.print("\nSet your OAuth token:\n  export TFC_VCS_OAUTH_TOKEN='ot-xxxxx'\n")
        sys.exit(1)

    # Confirmation prompt
    if not auto_approve:
        console.print(f"\n[bold]Update VCS branch for workspace:[/bold] {workspace_name}")
        console.print(f"  Repository: {current_vcs.identifier}")
        console.print(f"  Current branch: [yellow]{current_vcs.branch}[/yellow]")
        console.print(f"  New branch: [green]{branch}[/green]")
        confirm = typer.confirm("\nProceed with branch update?", default=False)
        if not confirm:
            console.print("Aborted.")
            sys.exit(0)

    # Update branch
    console.print(f"\nUpdating branch to [green]{branch}[/green]...")
    vcs_api.update_workspace_branch(workspace_obj.id, branch, oauth_token_id)

    console.print("[green]✓[/green] Branch updated successfully")
    console.print(
        f"\nWorkspace URL: https://app.terraform.io/app/{org}/workspaces/{workspace_name}"
    )


@app.command(name="repos")
@handle_cli_errors
def list_repos(
    organization: str | None = typer.Option(None, "-o", "--organization", help="TFC organization"),
    repo: str | None = typer.Option(None, "--repo", help="Filter by repository pattern"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show workspace details"),
) -> None:
    """List GitHub repositories connected to TFC workspaces."""
    org, _ = validate_context(organization)

    client = TFCClient(organization=org)
    vcs_api = VCSAPI(client)

    console.print(f"Discovering repositories in organization: [bold]{org}[/bold]")
    repos = vcs_api.list_repositories(org)

    # Filter by pattern if specified
    if repo:
        repos = [r for r in repos if repo.lower() in r["identifier"].lower()]

    if not repos:
        console.print("[yellow]No GitHub repositories found[/yellow]")
        sys.exit(0)

    # Render repository table
    render_vcs_repos(repos, verbose)
