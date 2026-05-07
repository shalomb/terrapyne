"""Workspace run triggers CLI commands."""

from typing import cast

import typer

from terrapyne.cli.utils import (
    console,
    get_client,
    handle_cli_errors,
    resolve_organization,
    validate_context,
)

app = typer.Typer(help="Manage workspace run trigger relationships")


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def triggers_list(
    ctx: typer.Context,
    workspace: str | None = typer.Argument(None, help="Downstream workspace name"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
):
    """List upstream run trigger sources for a workspace."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        triggers = client.run_triggers.list(ws.id)

        if not triggers:
            console.print("[yellow]No run triggers configured for this workspace.[/yellow]")
            return

        console.print(f"\n[bold]Upstream run triggers for[/bold] {ws_name}:\n")
        for trigger in triggers:
            name = trigger.source_workspace_name or trigger.source_workspace_id
            console.print(f"  • {name}  [dim](id: {trigger.id})[/dim]")


@app.command("add")
@handle_cli_errors
def triggers_add(
    ctx: typer.Context,
    workspace: str | None = typer.Argument(None, help="Downstream workspace name"),
    source: str = typer.Option(
        ..., "--source", "-s", help="Upstream workspace name to add as trigger source"
    ),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
):
    """Add an upstream workspace as a run trigger source."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        source_ws = client.workspaces.get(source, org)

        trigger = client.run_triggers.add(
            workspace_id=ws.id,
            source_workspace_id=source_ws.id,
        )

        source_name = trigger.source_workspace_name or source
        console.print(f"[green]✓[/green] Added run trigger: {source_name} → {ws_name}")
        console.print(f"  [dim]trigger id: {trigger.id}[/dim]")


@app.command("remove")
@handle_cli_errors
def triggers_remove(
    ctx: typer.Context,
    trigger_id: str = typer.Option(..., "--trigger-id", "-t", help="Run trigger ID to remove"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Remove a run trigger by its ID."""
    org = resolve_organization(organization)

    if not force and not typer.confirm(f"Remove run trigger '{trigger_id}'?"):
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit(0)

    with get_client(ctx, organization=org) as client:
        client.run_triggers.remove(run_trigger_id=trigger_id)

    console.print(f"[green]✓[/green] Removed run trigger: {trigger_id}")
