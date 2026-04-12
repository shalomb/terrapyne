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
    workspace: str | None = typer.Argument(
        None,
        help="Target TFC workspace name. If omitted, attempts auto-detection from local Terraform context.",
    ),
    organization: str | None = typer.Option(
        None,
        "-o",
        "--organization",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    limit: int = typer.Option(
        20, "-n", "--limit", help="Maximum number of state versions to retrieve and display."
    ),
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
        None,
        help="The specific state version ID (sv-*), workspace name, or workspace ID (ws-*) to inspect.",
    ),
    workspace: str | None = typer.Option(
        None,
        "-w",
        "--workspace",
        help="Target TFC workspace name. If omitted, attempts auto-detection from local context.",
    ),
    organization: str | None = typer.Option(
        None,
        "-o",
        "--organization",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
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
    state_version_id: str | None = typer.Argument(
        None, help="Specific TFC state version ID to download. Defaults to the latest version."
    ),
    workspace: str | None = typer.Option(
        None,
        "-w",
        "--workspace",
        help="Target TFC workspace name. Required if state_version_id is omitted.",
    ),
    organization: str | None = typer.Option(
        None,
        "-o",
        "--organization",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
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
        None,
        help="The specific workspace name, workspace ID (ws-*), or state version ID (sv-*) to retrieve outputs from.",
    ),
    name: str | None = typer.Argument(None, help="Optional name of a specific output to retrieve."),
    workspace: str | None = typer.Option(
        None,
        "-w",
        "--workspace",
        help="Target TFC workspace name. If omitted, attempts auto-detection from local context.",
    ),
    organization: str | None = typer.Option(
        None,
        "-o",
        "--organization",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Control the output style. 'table' is human-readable, 'json' is optimized for automation.",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="If enabled, prints the raw, unquoted value for a single output. Useful for shell pipelines.",
    ),
) -> None:
    """List outputs from a state version."""
    org, ws_name = validate_context(organization, workspace)

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
                ws = client.workspaces.get(target, org)
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

    # Filter by name if provided
    if name:
        outputs = [o for o in outputs if o.name == name]
        if not outputs:
            console.print(f"[red]Error: Output '{name}' not found.[/red]")
            raise typer.Exit(1)

    if raw:
        if len(outputs) == 1:
            print(outputs[0].value)
            return
        if len(outputs) > 1:
            console.print("[red]Error: Multiple outputs found. Specify a name to use --raw.[/red]")
            raise typer.Exit(1)
        # No outputs
        return

    if output_format == "json":
        print(
            json.dumps(
                [
                    {"name": o.name, "value": o.value, "type": o.type, "sensitive": o.sensitive}
                    for o in outputs
                ],
                indent=2,
            )
        )
        return

    table = Table(title="State Outputs")
    table.add_column("Name")
    table.add_column("Value")
    table.add_column("Type", style="dim")
    table.add_column("Sensitive")

    for o in outputs:
        val = "(sensitive)" if o.sensitive else str(o.value)
        table.add_row(o.name, val, o.type or "", "yes" if o.sensitive else "")

    console.print(table)


@app.command("inventory")
def state_inventory(
    workspace: str | None = typer.Argument(
        None,
        help="Target TFC workspace name. If omitted, attempts auto-detection from local Terraform context.",
    ),
    organization: str | None = typer.Option(
        None,
        "-o",
        "--organization",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    fields: str | None = typer.Option(
        None,
        "--fields",
        help="Comma-separated list of resource fields to include in the output (e.g. 'type,id,name').",
    ),
    type_filter: str | None = typer.Option(
        None,
        "--type",
        help="Filter results to specific resource types (comma-separated, e.g. 'aws_instance,aws_s3_bucket').",
    ),
    mode: str = typer.Option(
        "managed", "--mode", help="Filter by resource mode: 'managed' (default) or 'data'."
    ),
    module: str | None = typer.Option(
        None, "--module", help="Filter results by module path substring."
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Control the output style. 'table' is human-readable, 'markdown' for docs, 'json' for automation.",
    ),
) -> None:
    """Show current resource inventory from latest state."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)
    field_list = _parse_fields(fields)
    type_set = _parse_types(type_filter)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(ws_name or "", org)
        sv = client.state_versions.get_current(ws.id)
        state = client.state_versions.download_from_url(_require_download_url(sv))

    instances = parse_state_resources(state, types=type_set, mode=mode, module_pattern=module)
    rows = extract_rows(instances, field_list)

    _render_rows(rows, field_list, output_format, title=f"Resources in {ws_name}")


@app.command("diff")
def state_diff(
    workspace: str | None = typer.Argument(
        None,
        help="Target TFC workspace name. If omitted, attempts auto-detection from local Terraform context.",
    ),
    organization: str | None = typer.Option(
        None,
        "-o",
        "--organization",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    since: str = typer.Option(
        ...,
        "--since",
        help="The start date/time for the diff (ISO 8601 format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).",
    ),
    fields: str | None = typer.Option(
        None,
        "--fields",
        help="Comma-separated list of resource fields to include in the diff output.",
    ),
    type_filter: str | None = typer.Option(
        None, "--type", help="Filter the diff to specific resource types (comma-separated)."
    ),
    mode: str = typer.Option(
        "managed", "--mode", help="Filter the diff by resource mode: 'managed' (default) or 'data'."
    ),
    module: str | None = typer.Option(
        None, "--module", help="Filter the diff by module path substring."
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Control the output style. 'table', 'markdown', 'json', or 'diff' (unified patch format).",
    ),
    diff_cmd: str | None = typer.Option(
        None,
        "--diff-cmd",
        help="External diff program to use when format is 'diff' (e.g. 'delta', 'git diff --no-index').",
    ),
) -> None:
    """Show resources added/removed since a date."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)
    since_dt = _parse_since(since)
    field_list = _parse_fields(fields)
    type_set = _parse_types(type_filter)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(ws_name or "", org)

        # Current state
        sv_new = client.state_versions.get_current(ws.id)
        state_new = client.state_versions.download_from_url(_require_download_url(sv_new))

        # State before the given date
        sv_old = client.state_versions.find_version_before(ws.id, since_dt)
        state_old = (
            client.state_versions.download_from_url(_require_download_url(sv_old)) if sv_old else {}
        )

    new_instances = parse_state_resources(
        state_new, types=type_set, mode=mode, module_pattern=module
    )
    old_instances = (
        parse_state_resources(state_old, types=type_set, mode=mode, module_pattern=module)
        if state_old
        else []
    )

    if output_format == "diff":
        output = format_diff_unified(old_instances, new_instances, field_list, diff_cmd=diff_cmd)
        print(output, end="")
        return

    result = diff_state_resources(old_instances, new_instances)

    since_label = since_dt.strftime("%Y-%m-%d")
    old_serial = f" (serial {sv_old.serial})" if sv_old else " (no prior state)"
    console.print(
        f"[dim]Comparing current (serial {sv_new.serial}) vs state before {since_label}{old_serial}[/dim]\n"
    )

    if not result.added and not result.removed:
        console.print(f"[green]No resource changes since {since_label}[/green]")
        return

    if result.added:
        rows = extract_rows(result.added, field_list)
        _render_rows(
            rows, field_list, output_format, title=f"Added ({len(result.added)})", action="+"
        )

    if result.removed:
        rows = extract_rows(result.removed, field_list)
        _render_rows(
            rows, field_list, output_format, title=f"Removed ({len(result.removed)})", action="-"
        )


def _render_rows(
    rows: list[dict[str, str]],
    fields: list[str],
    output_format: str,
    title: str = "",
    action: str | None = None,
) -> None:
    """Render rows in the requested format."""
    if output_format == "json":
        if action:
            for row in rows:
                row["_action"] = action
        print(json.dumps(rows, indent=2))

    elif output_format == "markdown":
        cols = ["#"]
        if action:
            cols.append("")
        cols.extend(fields)
        header = "| " + " | ".join(cols) + " |"
        separator = "| " + " | ".join("---" for _ in cols) + " |"

        if title:
            console.print(f"\n**{title}**\n")
        print(header)
        print(separator)
        for i, row in enumerate(rows, 1):
            prefix = f" {action} |" if action else ""
            vals = " | ".join(row.get(f, "") for f in fields)
            print(f"| {i} |{prefix} {vals} |")

    else:  # table (default)
        table = Table(title=title)
        table.add_column("#", style="dim", justify="right")
        if action:
            table.add_column("", width=1)
        for f in fields:
            table.add_column(f)

        for i, row in enumerate(rows, 1):
            action_cell = (
                "[green]+[/green]" if action == "+" else "[red]-[/red]" if action == "-" else ""
            )
            cells = [str(i)]
            if action:
                cells.append(action_cell)
            cells.extend(row.get(f, "") for f in fields)
            table.add_row(*cells)

        console.print(table)
