"""Team CLI commands."""

import typer
from rich.console import Console
from rich.table import Table

from terrapyne.api.client import TFCClient
from terrapyne.cli.utils import handle_cli_errors, validate_context

app = typer.Typer(help="Team management commands")
console = Console()


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def team_list(
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    limit: int = typer.Option(
        100, "--limit", "-n", help="Maximum number of teams to retrieve and display."
    ),
    search: str | None = typer.Option(
        None,
        "--search",
        "-s",
        help="Optional search pattern to filter teams by name (substring match).",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Control the output style. 'table' is human-readable, 'json' is optimized for automation.",
    ),
):
    """List teams in an organization.

    Auto-detects organization from terraform.tf if not specified.

    Examples:
        # List all teams in organization
        terrapyne team list

        # Search for teams by name
        terrapyne team list --search platform

        # List teams in specific organization
        terrapyne team list --organization my-org
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        teams_iter, total_count = client.teams.list_teams(organization=org, search=search)
        teams = [t for i, t in enumerate(teams_iter) if i < limit]

        if not teams:
            console.print("[yellow]No teams found.[/yellow]")
            return

        if output_format == "json":
            from terrapyne.cli.utils import emit_json

            emit_json([{"id": t.id, "name": t.name, "created_at": t.created_at} for t in teams])
            return

        # Render teams table
        table = Table(title=f"Teams in {org}", show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Members", justify="right")
        table.add_column("Description", max_width=50)

        for team in teams:
            members_count = str(team.members_count or 0)
            description = team.description or "-"
            table.add_row(team.name, members_count, description)

        console.print(table)

        # Display count
        if total_count is not None:
            console.print(f"\n[dim]Showing: {len(teams)} of {total_count} team(s)[/dim]")
        else:
            console.print(f"\n[dim]Showing: {len(teams)} team(s)[/dim]")


@app.command("show")
@handle_cli_errors
def team_show(
    team_id: str = typer.Argument(
        ..., help="The unique TFC Team ID to display (e.g., 'team-abc123')."
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
):
    """Show detailed team information.

    Examples:
        # Show team by ID
        terrapyne team show team-abc123

        # Show team in specific organization
        terrapyne team show team-abc123 -o my-org
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        team = client.teams.get(team_id)

        # Display team details
        table = Table(title=f"Team: {team.name}", show_header=False, box=None)
        table.add_column("Property", style="bold cyan", width=20)
        table.add_column("Value")

        table.add_row("ID", team.id)
        table.add_row("Name", team.name)

        if team.description:
            table.add_row("Description", team.description)

        if team.members_count is not None:
            table.add_row("Members", str(team.members_count))

        if team.created_at:
            table.add_row("Created", team.created_at.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(table)

        # List team members
        members, total_members = client.teams.list_members(team_id)

        if members:
            console.print()  # Blank line
            members_table = Table(
                title=f"Members ({len(members)})", show_header=True, header_style="bold magenta"
            )
            members_table.add_column("User ID", style="cyan")
            members_table.add_column("Type")

            for member in members:
                user_id = member.get("id", "N/A")
                user_type = member.get("type", "user")
                members_table.add_row(user_id, user_type)

            console.print(members_table)


@app.command("create")
@handle_cli_errors
def team_create(
    name: str = typer.Option(..., "--name", "-n", help="The name of the new TFC team."),
    description: str | None = typer.Option(
        None, "--description", "-d", help="An optional description for the new team."
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
):
    """Create a new team.

    Examples:
        # Create team with name
        terrapyne team create --name "Platform Team"

        # Create with description
        terrapyne team create --name "DevOps" --description "Infrastructure and DevOps"

        # In specific organization
        terrapyne team create --name "Team" -o my-org
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        console.print(f"[dim]Creating team:[/dim] {name}")

        team = client.teams.create(
            organization=org,
            name=name,
            description=description,
        )

        console.print(f"[green]✓[/green] Team created: {team.id}")
        console.print(f"[dim]Name:[/dim] {team.name}")
        if team.description:
            console.print(f"[dim]Description:[/dim] {team.description}")


@app.command("update")
@handle_cli_errors
def team_update(
    team_id: str = typer.Argument(
        ..., help="The unique TFC Team ID to update (e.g., 'team-abc123')."
    ),
    name: str | None = typer.Option(None, "--name", "-n", help="The new name for the TFC team."),
    description: str | None = typer.Option(
        None, "--description", "-d", help="The new description for the TFC team."
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
):
    """Update team information.

    Examples:
        # Update team name
        terrapyne team update team-abc123 --name "New Name"

        # Update description
        terrapyne team update team-abc123 --description "Updated description"

        # Update multiple fields
        terrapyne team update team-abc123 --name "Platform" --description "Platform engineers"
    """
    org, _ = validate_context(organization)

    if not name and description is None:
        console.print("[red]Error: Specify at least --name or --description[/red]")
        raise typer.Exit(1)

    with TFCClient(organization=org) as client:
        console.print(f"[dim]Updating team:[/dim] {team_id}")

        team = client.teams.update(
            team_id=team_id,
            name=name,
            description=description,
        )

        console.print("[green]✓[/green] Team updated")
        console.print(f"[dim]Name:[/dim] {team.name}")
        if team.description:
            console.print(f"[dim]Description:[/dim] {team.description}")


@app.command("delete")
@handle_cli_errors
def team_delete(
    team_id: str = typer.Argument(
        ..., help="The unique TFC Team ID to delete (e.g., 'team-abc123')."
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip interactive deletion confirmation. Required for automation.",
    ),
):
    """Delete a team.

    Examples:
        # Delete team (with confirmation)
        terrapyne team delete team-abc123

        # Delete without confirmation
        terrapyne team delete team-abc123 --force
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # Get team info for confirmation
        team = client.teams.get(team_id)

        # Confirmation prompt
        if not force and not typer.confirm(f"Delete team '{team.name}' ({team_id})?"):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

        console.print(f"[dim]Deleting team:[/dim] {team_id}")

        client.teams.delete(team_id)

        console.print(f"[green]✓[/green] Team deleted: {team.name}")


@app.command("members")
@handle_cli_errors
def team_members(
    team_id: str = typer.Argument(..., help="The unique TFC Team ID to list members for."),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
):
    """List members of a team.

    Examples:
        # List team members
        terrapyne team members team-abc123

        # In specific organization
        terrapyne team members team-abc123 -o my-org
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        team = client.teams.get(team_id)

        members, total_count = client.teams.list_members(team_id)

        if not members:
            console.print(f"[yellow]No members in team '{team.name}'[/yellow]")
            return

        # Display members table
        table = Table(
            title=f"Team Members: {team.name}",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("User ID", style="cyan")
        table.add_column("Type")

        for member in members:
            user_id = member.get("id", "N/A")
            user_type = member.get("type", "user")
            table.add_row(user_id, user_type)

        console.print(table)

        if total_count is not None:
            console.print(f"\n[dim]Showing: {len(members)} of {total_count} member(s)[/dim]")
        else:
            console.print(f"\n[dim]Showing: {len(members)} member(s)[/dim]")


@app.command("add-member")
@handle_cli_errors
def add_team_member(
    team_id: str = typer.Argument(..., help="The unique TFC Team ID to add a user to."),
    user_id: str = typer.Option(
        ..., "--user", "-u", help="The unique TFC User ID to add to the team."
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
):
    """Add a user to a team.

    Examples:
        # Add user to team
        terrapyne team add-member team-abc123 --user user-xyz789

        # In specific organization
        terrapyne team add-member team-abc123 --user user-xyz789 -o my-org
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        team = client.teams.get(team_id)

        console.print(f"[dim]Adding user to team:[/dim] {team.name}")

        client.teams.add_member(team_id=team_id, user_id=user_id)

        console.print("[green]✓[/green] User added to team")
        console.print(f"[dim]Team:[/dim] {team.name}")
        console.print(f"[dim]User:[/dim] {user_id}")


@app.command("remove-member")
@handle_cli_errors
def remove_team_member(
    team_id: str = typer.Argument(..., help="The unique TFC Team ID to remove a user from."),
    user_id: str = typer.Option(
        ..., "--user", "-u", help="The unique TFC User ID to remove from the team."
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip interactive removal confirmation. Required for automation.",
    ),
):
    """Remove a user from a team.

    Examples:
        # Remove user from team (with confirmation)
        terrapyne team remove-member team-abc123 --user user-xyz789

        # Remove without confirmation
        terrapyne team remove-member team-abc123 --user user-xyz789 --force
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        team = client.teams.get(team_id)

        # Confirmation prompt
        if not force and not typer.confirm(f"Remove user {user_id} from team '{team.name}'?"):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

        console.print(f"[dim]Removing user from team:[/dim] {team.name}")

        client.teams.remove_member(team_id=team_id, user_id=user_id)

        console.print("[green]✓[/green] User removed from team")
        console.print(f"[dim]Team:[/dim] {team.name}")
        console.print(f"[dim]User:[/dim] {user_id}")
