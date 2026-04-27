"""Variable Set CLI commands."""

import typer

from terrapyne.cli.utils import (
    console,
    emit_json,
    get_client,
    handle_cli_errors,
    resolve_organization,
)

app = typer.Typer(help="Variable set management commands")


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def varset_list(
    ctx: typer.Context,
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List variable sets in an organization."""
    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified.[/red]")
        raise typer.Exit(1)

    with get_client(ctx, organization=org) as client:
        varsets, total = client.varsets.list(org)
        vs_list = list(varsets)

        if json_output:
            emit_json([vs.model_dump() for vs in vs_list])
            return

        from rich.table import Table

        table = Table(title=f"Variable Sets in {org}", show_lines=False)
        table.add_column("Name", style="bold")
        table.add_column("Description")
        table.add_column("Global", justify="center")
        table.add_column("Vars", justify="right")
        table.add_column("Workspaces", justify="right")

        for vs in vs_list:
            table.add_row(
                vs.name,
                vs.description or "",
                "yes" if vs.global_ else "no",
                str(vs.var_count),
                str(vs.workspace_count),
            )

        console.print(table)
        if total:
            console.print(f"\n[dim]Total: {total}[/dim]")


@app.command("show")
@handle_cli_errors
def varset_show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Variable set name"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show variables in a variable set."""
    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified.[/red]")
        raise typer.Exit(1)

    with get_client(ctx, organization=org) as client:
        vs = client.varsets.get_by_name(name, org)
        variables = list(client.varsets.get_variables(vs.id))

        if json_output:
            emit_json({"varset": vs.model_dump(), "variables": [v.model_dump() for v in variables]})
            return

        from rich.table import Table

        console.print(f"[bold]Variable Set:[/bold] {vs.name}")
        if vs.description:
            console.print(f"[dim]{vs.description}[/dim]")
        console.print(f"[dim]Global: {'yes' if vs.global_ else 'no'}[/dim]")
        console.print()

        table = Table(title="Variables", show_lines=False)
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_column("Category")
        table.add_column("Sensitive", justify="center")

        for var in variables:
            table.add_row(
                var.key,
                var.display_value,
                var.category,
                "yes" if var.sensitive else "no",
            )

        console.print(table)


@app.command("apply")
@handle_cli_errors
def varset_apply(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Variable set name"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
):
    """Apply a variable set to a workspace."""
    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified.[/red]")
        raise typer.Exit(1)

    with get_client(ctx, organization=org) as client:
        vs = client.varsets.get_by_name(name, org)
        ws = client.workspaces.get(workspace, org)
        client.varsets.apply(vs.id, ws.id)
        console.print(f"[green]Applied variable set '{name}' to workspace '{workspace}'.[/green]")


@app.command("remove")
@handle_cli_errors
def varset_remove(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Variable set name"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
):
    """Remove a variable set from a workspace."""
    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified.[/red]")
        raise typer.Exit(1)

    with get_client(ctx, organization=org) as client:
        vs = client.varsets.get_by_name(name, org)
        ws = client.workspaces.get(workspace, org)
        client.varsets.remove(vs.id, ws.id)
        console.print(f"[green]Removed variable set '{name}' from workspace '{workspace}'.[/green]")
