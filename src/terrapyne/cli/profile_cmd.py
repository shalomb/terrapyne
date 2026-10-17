"""CLI commands for managing Terrapyne configuration profiles."""

from __future__ import annotations

import typer
from rich.table import Table

from terrapyne.cli.error_handlers import handle_cli_errors
from terrapyne.cli.output_helpers import effective_format, emit_json
from terrapyne.core.config import (
    Profile,
    get_xdg_config_path,
    load_config,
)
from terrapyne.rendering.logging import console, error_console

app = typer.Typer(
    name="profile",
    help="Manage named configuration profiles and active contexts",
)


@app.command(name="list")
@handle_cli_errors
def list_profiles(
    ctx: typer.Context,
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (table or json)",
    ),
) -> None:
    """List all available profiles."""
    fmt = effective_format(ctx, output_format)
    cfg = load_config()

    active_profile = cfg.get_profile()
    active_name = active_profile.name if active_profile else None

    if fmt == "json":
        items = []
        for name, profile in cfg.profiles.items():
            dump = profile.model_dump()
            dump["is_active"] = name == active_name
            items.append(dump)
        emit_json(
            {
                "source_path": str(cfg.source_path) if cfg.source_path else None,
                "current_profile": cfg.current_profile,
                "profiles": items,
            }
        )
        return

    if not cfg.profiles:
        console.print("[yellow]No profiles configured.[/yellow]")
        if cfg.source_path:
            console.print(f"[dim]Config file: {cfg.source_path}[/dim]")
        else:
            console.print(f"[dim]Config file: {get_xdg_config_path()} (not yet created)[/dim]")
        return

    table = Table(title="Configuration Profiles")
    table.add_column("Active", justify="center", style="bold green", width=8)
    table.add_column("Name", style="cyan")
    table.add_column("Organization", style="magenta")
    table.add_column("Hostname")
    table.add_column("Default Project")
    table.add_column("Default Workspace")

    for name, profile in cfg.profiles.items():
        is_active = "*" if name == active_name else ""
        table.add_row(
            is_active,
            name,
            profile.organization or "-",
            profile.hostname or "-",
            profile.default_project or "-",
            profile.default_workspace or "-",
        )

    console.print(table)
    if cfg.source_path:
        console.print(f"[dim]Source: {cfg.source_path}[/dim]")


@app.command(name="show")
@handle_cli_errors
def show_profile(
    ctx: typer.Context,
    name: str | None = typer.Argument(
        None,
        help="Profile name (defaults to active profile)",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (table or json)",
    ),
) -> None:
    """Show details of a specific profile or the active profile."""
    fmt = effective_format(ctx, output_format)
    cfg = load_config()

    target_profile = cfg.get_profile(name)
    if not target_profile:
        requested = f"'{name}'" if name else "active"
        error_console.print(
            f"[red]Error: Profile {requested} not found.[/red]\n"
            f"Run 'tfc profile list' to see available profiles."
        )
        raise typer.Exit(code=1)

    active_profile = cfg.get_profile()
    is_active = active_profile is not None and target_profile.name == active_profile.name

    if fmt == "json":
        data = target_profile.model_dump()
        data["is_active"] = is_active
        data["source_path"] = str(cfg.source_path) if cfg.source_path else None
        emit_json(data)
        return

    table = Table(title=f"Profile: {target_profile.name}{' (active)' if is_active else ''}")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Organization", target_profile.organization or "-")
    table.add_row("Hostname", target_profile.hostname)
    table.add_row("Default Project", target_profile.default_project or "-")
    table.add_row("Default Workspace", target_profile.default_workspace or "-")
    if target_profile.token_env:
        table.add_row("Token Env Var", target_profile.token_env)
    if target_profile.token:
        table.add_row("Token", "********" if target_profile.token else "-")
    if target_profile.poll_interval:
        table.add_row("Poll Interval", f"{target_profile.poll_interval}s")
    if target_profile.poll_timeout:
        table.add_row("Poll Timeout", f"{target_profile.poll_timeout}s")
    if target_profile.cache_ttl:
        table.add_row("Cache TTL", f"{target_profile.cache_ttl}s")
    if target_profile.format:
        table.add_row("Format", target_profile.format)
    if target_profile.runner_binary:
        table.add_row("Runner Binary", target_profile.runner_binary)

    for k, v in target_profile.extra.items():
        table.add_row(k, str(v))

    console.print(table)
    if cfg.source_path:
        console.print(f"[dim]Source: {cfg.source_path}[/dim]")


@app.command(name="use")
@handle_cli_errors
def use_profile(
    name: str = typer.Argument(..., help="Name of profile to switch to"),
) -> None:
    """Switch active profile."""
    cfg = load_config()

    if name not in cfg.profiles:
        # Create empty placeholder profile if it does not exist
        cfg.profiles[name] = Profile(name=name)

    cfg.current_profile = name
    saved_path = cfg.save()
    console.print(f"[green]Switched active profile to '{name}'[/green] (saved to {saved_path})")


@app.command(name="set")
@handle_cli_errors
def set_profile_value(
    key: str = typer.Argument(
        ..., help="Setting key (e.g. organization, hostname, default_project)"
    ),
    value: str = typer.Argument(..., help="Setting value"),
    profile_name: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile to modify (defaults to active profile or 'default')",
    ),
) -> None:
    """Set a configuration value for a profile."""
    cfg = load_config()

    target_name = profile_name or cfg.current_profile or "default"
    if target_name not in cfg.profiles:
        cfg.profiles[target_name] = Profile(name=target_name)

    profile = cfg.profiles[target_name]

    # Convert numeric fields
    if key in ("poll_interval", "poll_timeout"):
        try:
            setattr(profile, key, float(value))
        except ValueError:
            error_console.print(f"[red]Error: {key} must be a number[/red]")
            raise typer.Exit(code=1) from None
    elif key == "cache_ttl":
        try:
            setattr(profile, key, int(value))
        except ValueError:
            error_console.print(f"[red]Error: {key} must be an integer[/red]")
            raise typer.Exit(code=1) from None
    elif hasattr(profile, key) and key != "name":
        setattr(profile, key, value)
    else:
        profile.extra[key] = value

    saved_path = cfg.save()
    console.print(
        f"[green]Updated {key} = '{value}' in profile '{target_name}'[/green] (saved to {saved_path})"
    )


@app.command(name="path")
@handle_cli_errors
def show_config_path() -> None:
    """Print path to active configuration file."""
    cfg = load_config()
    if cfg.source_path:
        console.print(str(cfg.source_path))
    else:
        console.print(
            f"[dim]No active config found. Default location: {get_xdg_config_path()}[/dim]"
        )
