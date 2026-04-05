"""State version CLI commands."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from terrapyne.api.client import TFCClient
from terrapyne.cli.utils import validate_context
from terrapyne.core.state_diff import (
    DEFAULT_FIELDS,
    diff_state_resources,
    extract_rows,
    format_diff_unified,
    parse_state_resources,
)

app = typer.Typer(help="State version commands")
console = Console()


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


def _parse_since(since: str) -> datetime:
    """Parse a --since value into a timezone-aware datetime."""
    try:
        dt = datetime.fromisoformat(since)
    except ValueError:
        console.print(
            f"[red]Error: Cannot parse date '{since}'. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).[/red]"
        )
        raise typer.Exit(1) from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _parse_fields(fields: str | None) -> list[str]:
    return [f.strip() for f in fields.split(",")] if fields else DEFAULT_FIELDS


def _parse_types(types: str | None) -> set[str] | None:
    return {t.strip() for t in types.split(",")} if types else None


def _require_download_url(sv: Any) -> str:
    """Extract download URL from a state version, or exit with error."""
    if not sv.download_url:
        console.print(
            f"[red]Error: State version {sv.id} has no download URL "
            f"(status: {sv.status}). The state may still be processing.[/red]"
        )
        raise typer.Exit(1)
    return sv.download_url


@app.command("list")
def state_list(
    workspace: str | None = typer.Argument(None, help="Workspace name"),
    organization: str | None = typer.Option(None, "-o", "--organization"),
    limit: int = typer.Option(20, "-n", "--limit", help="Max versions to show"),
) -> None:
    """List state versions for a workspace."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(ws_name or "", org)
        versions, total = client.state_versions.list(ws.id, limit=limit)

    table = Table(title=f"State versions for {ws_name}")
    table.add_column("#", style="dim")
    table.add_column("ID")
    table.add_column("Serial", justify="right")
    table.add_column("Created")
    table.add_column("Status")
    table.add_column("Resources", justify="right")
    table.add_column("Run ID", style="dim")

    for i, sv in enumerate(versions, 1):
        created = sv.created_at.strftime("%Y-%m-%d %H:%M") if sv.created_at else ""
        table.add_row(
            str(i),
            sv.id,
            str(sv.serial),
            created,
            sv.status or "",
            str(sv.resource_count),
            sv.run_id or "",
        )

    console.print(table)
    if total is not None:
        console.print(f"[dim]Showing {min(limit, total)} of {total} state versions[/dim]")


@app.command("show")
def state_show(
    target: str | None = typer.Argument(
        None, help="State version ID (sv-*), workspace name, or workspace ID (ws-*)"
    ),
    workspace: str | None = typer.Option(None, "-w", "--workspace"),
    organization: str | None = typer.Option(None, "-o", "--organization"),
) -> None:
    """Show state version metadata. Defaults to latest for the workspace."""
    org, ws_name = validate_context(organization, workspace)

    with TFCClient(organization=org) as client:
        if target and target.startswith("sv-"):
            sv = client.state_versions.get(target)
        else:
            # Resolve workspace from target arg, -w flag, or context
            resolve_ws = target or ws_name
            if not resolve_ws:
                console.print("[red]Error: Provide a workspace name or state version ID[/red]")
                raise typer.Exit(1)
            if resolve_ws.startswith("ws-"):
                ws = client.workspaces.get_by_id(resolve_ws)
            else:
                ws = client.workspaces.get(resolve_ws, org)
            sv = client.state_versions.get_current(ws.id)

    console.print(f"[bold]State Version:[/bold] {sv.id}")
    console.print(f"  Serial:     {sv.serial}")
    console.print(f"  Status:     {sv.status}")
    console.print(f"  Created:    {sv.created_at}")
    console.print(f"  Resources:  {sv.resource_count}")
    console.print(f"  Providers:  {sv.providers_count}")
    if sv.run_id:
        console.print(f"  Run:        {sv.run_id}")


@app.command("pull")
def state_pull(
    state_version_id: str | None = typer.Argument(None, help="State version ID (default: latest)"),
    workspace: str | None = typer.Option(None, "-w", "--workspace"),
    organization: str | None = typer.Option(None, "-o", "--organization"),
) -> None:
    """Download state JSON to stdout (like terraform state pull)."""
    org, ws_name = validate_context(organization, workspace)

    with TFCClient(organization=org) as client:
        if state_version_id:
            state = client.state_versions.download(state_version_id)
        else:
            if not ws_name:
                console.print("[red]Error: Workspace required when no state version ID given[/red]")
                raise typer.Exit(1)
            ws = client.workspaces.get(ws_name, org)
            sv = client.state_versions.get_current(ws.id)
            state = client.state_versions.download_from_url(_require_download_url(sv))

    # Raw JSON to stdout — not through rich, so it's pipeable
    print(json.dumps(state, indent=2))


@app.command("outputs")
def state_outputs(
    target: str | None = typer.Argument(
        None, help="Workspace name, workspace ID (ws-*), or state version ID (sv-*)"
    ),
    name: str | None = typer.Argument(None, help="Specific output name to show"),
    workspace: str | None = typer.Option(None, "-w", "--workspace"),
    organization: str | None = typer.Option(None, "-o", "--organization"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    raw: bool = typer.Option(
        False, "--raw", help="Return raw value for single output (unquoted string)"
    ),
) -> None:
    """List outputs from a state version or show a single output."""
    org, ws_name = validate_context(organization, workspace)

    # Validate that --raw is not combined with other formats
    if raw and output_format != "table":
        console.print("[red]Error: --raw is mutually exclusive with --format[/red]")
        raise typer.Exit(1)

    with TFCClient(organization=org) as client:
        state_version_id = None

        if target and target.startswith("sv-"):
            # Explicit state version ID
            state_version_id = target
        elif target:
            # Treat as workspace name or ID
            if target.startswith("ws-"):
                ws = client.workspaces.get_by_id(target)
            else:
                try:
                    ws = client.workspaces.get(target, org)
                except Exception:
                    # If target is not a workspace, maybe it's the output name and workspace is in context
                    if ws_name:
                        ws = client.workspaces.get(ws_name, org)
                        name = target  # Shift target to name
                    else:
                        raise
            sv = client.state_versions.get_current(ws.id)
            state_version_id = sv.id
        elif ws_name:
            ws = client.workspaces.get(ws_name, org)
            sv = client.state_versions.get_current(ws.id)
            state_version_id = sv.id
        else:
            console.print(
                "[red]Error: Provide a workspace name, workspace ID, or state version ID[/red]"
            )
            raise typer.Exit(1)

        outputs = client.state_versions.list_outputs(state_version_id)

    if name:
        output = next((o for o in outputs if o.name == name), None)
        if not output:
            console.print(f"[red]Error: Output '{name}' not found.[/red]")
            raise typer.Exit(1)

        if raw:
            # Print value directly without formatting
            if output.sensitive:
                console.print(
                    "[yellow]Warning: Output is sensitive, use --format=json to see the value[/yellow]"
                )
                raise typer.Exit(1)
            # Use print() instead of console.print() for raw shell friendliness
            print(output.value)
            return

        outputs = [output]

    if output_format == "json":
        data = {o.name: o.value for o in outputs}
        print(json.dumps(data, indent=2))
        return

    table = Table(title=f"Outputs for {state_version_id}")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Value")

    for o in outputs:
        val = "[sensitive]" if o.sensitive else str(o.value)
        table.add_row(o.name, o.type, val)

    console.print(table)
