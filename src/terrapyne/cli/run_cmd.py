"""Run CLI commands."""

from __future__ import annotations

import datetime
import json
import sys
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any

import typer

from terrapyne.api.client import TFCClient
from terrapyne.cli.utils import console, emit_json, handle_cli_errors, validate_context
from terrapyne.models.run import Run
from terrapyne.utils.rich_tables import render_run_detail, render_runs

app = typer.Typer(help="Run management commands")


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def run_list(
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace name (auto-detected if omitted)",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option("--status", help="Filter by run status"),
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Maximum number of runs to show")
    ] = 20,
    output_format: Annotated[
        str, typer.Option("--format", "-f", help="Output format (table, json)")
    ] = "table",
):
    """List runs for a workspace."""
    # Resolve organization and workspace
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        # Get workspace to retrieve workspace ID
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        # Fetch runs
        runs, total = client.runs.list(workspace_id=ws.id, limit=limit, status=status)

        if not runs:
            status_msg = f" with status '{status}'" if status else ""
            console.print(
                f"[yellow]No runs found for workspace '{workspace_name}'{status_msg}[/yellow]"
            )
            return

        if output_format == "json":
            emit_json(runs)
            return

        render_runs(runs, title=f"Runs for {workspace_name}", total_count=total)


@app.command("show")
@handle_cli_errors
def run_show(
    run_id: Annotated[str, typer.Argument(help="Run ID (run-*)")],
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace name (optional, improves display)",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    output_format: Annotated[
        str, typer.Option("--format", "-f", help="Output format (table, json)")
    ] = "table",
):
    """Show detailed information for a specific run."""
    # Resolve organization
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # Fetch run details
        run = client.runs.get(run_id)

        # If workspace not provided, try to resolve from run's workspace_id
        if not workspace and run.workspace_id:
            with suppress(Exception):
                ws = client.workspaces.get_by_id(run.workspace_id)
                workspace = ws.name

        # Fetch plan details for accurate resource counts
        plan = None
        if run.plan_id:
            with suppress(Exception):
                plan = client.runs.get_plan(run.plan_id)

        if output_format == "json":
            emit_json(
                {
                    "id": run.id,
                    "status": run.status.value,
                    "message": run.message,
                    "created_at": run.created_at,
                    "workspace_id": run.workspace_id,
                    "plan_id": run.plan_id,
                    "resource_additions": run.resource_additions,
                    "resource_changes": run.resource_changes,
                    "resource_destructions": run.resource_destructions,
                    "is_destroy": run.is_destroy,
                }
            )
            return

        # Render run details with URL and plan
        render_run_detail(run, workspace_name=workspace, organization=org, plan=plan)


@app.command("plan")
@handle_cli_errors
def run_plan(
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace name (auto-detected if omitted)",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    message: Annotated[str | None, typer.Option("--message", "-m", help="Run description")] = None,
    wait: Annotated[
        bool, typer.Option("--wait/--no-wait", help="Block until plan completes")
    ] = True,
    wait_queue: Annotated[
        bool,
        typer.Option(
            "--wait-queue",
            help="Wait for any current run to finish before triggering (block until available)",
        ),
    ] = False,
    discard_older: Annotated[
        bool,
        typer.Option("--discard-older", help="Discard all pending/queued runs before triggering"),
    ] = False,
    debug_run: Annotated[
        bool, typer.Option("--debug-run", help="Enable TFC debugging-mode for this run")
    ] = False,
):
    """Create a new plan (run) for a workspace."""
    # Resolve context
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        # Queue management
        if discard_older:
            active_runs = client.runs.get_active_runs(ws.id)
            for r in active_runs:
                if not r.status.is_terminal and r.status.value not in ["applying", "applied"]:
                    with suppress(Exception):
                        client.runs.discard(r.id, comment="Discarded by terrapyne --discard-older")

        if wait_queue:
            active_runs = client.runs.get_active_runs(ws.id)
            if active_runs:
                current_run = active_runs[0]
                console.print(
                    f"[dim]Waiting for current run {current_run.id} "
                    f"({current_run.status.value}) to finish...[/dim]"
                )
                try:
                    client.runs.poll_until_complete(current_run.id)
                except TimeoutError:
                    console.print("[red]Timeout waiting for current run to finish.[/red]")
                    raise typer.Exit(1) from None

        console.print(f"[dim]Creating plan for workspace:[/dim] {workspace_name}")

        # Create run
        run = client.runs.create(
            workspace_id=ws.id,
            message=message,
            auto_apply=False,
            debug=debug_run,
        )

        console.print(f"[green]✓[/green] Created run: {run.id}")
        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not wait:
            console.print(
                f"\n[dim]View run at:[/dim] https://app.terraform.io/app/{org}/workspaces/{workspace_name}/runs/{run.id}"
            )
            return

        # Poll until complete
        console.print("\n[dim]Watching run progress...[/dim]")

        def print_status(r):
            console.print(f"  {r.status.emoji} {r.status.value}", end="\r", style="dim")

        try:
            final_run = client.runs.poll_until_complete(run.id, callback=print_status)
            console.print(" " * 80, end="\r")  # Clear line

            # Show final summary
            plan = None
            if final_run.plan_id:
                with suppress(Exception):
                    plan = client.runs.get_plan(final_run.plan_id)

            render_run_detail(final_run, workspace_name=workspace_name, organization=org, plan=plan)

            if not final_run.status.is_successful:
                if final_run.status.is_awaiting_approval:
                    console.print("\n[yellow]⏸ Plan paused for manual approval.[/yellow]")
                    raise typer.Exit(0)
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


@app.command("logs")
@handle_cli_errors
def run_logs(
    run_id: Annotated[str, typer.Argument(help="Run ID (run-*)")],
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    apply: Annotated[
        bool, typer.Option("--apply", help="Show apply logs instead of plan logs")
    ] = False,
):
    """Fetch and print the logs for a specific run."""
    # Resolve organization
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # Fetch run details
        run = client.runs.get(run_id)

        if apply:
            if not run.apply_id:
                console.print(
                    "[red]Error: Run has no apply ID (apply may not have started yet).[/red]"
                )
                raise typer.Exit(1)
            try:
                logs = client.runs.get_apply_logs(run.apply_id)
            except Exception:
                console.print(
                    "[yellow]Apply logs unavailable — apply may have errored early.[/yellow]"
                )
                raise typer.Exit(1) from None
        else:
            if not run.plan_id:
                console.print("[red]Error: Run has no plan ID.[/red]")
                raise typer.Exit(1)
            try:
                logs = client.runs.get_plan_logs(run.plan_id)
            except Exception:
                console.print(
                    "[yellow]Plan logs unavailable — run may have errored before plan completed.[/yellow]"
                )
                raise typer.Exit(1) from None

        if not logs.strip():
            console.print("[yellow]Logs are empty (run may still be in progress).[/yellow]")
            return

        # Print raw logs to stdout so they're pipeable
        print(logs)


@app.command("apply")
@handle_cli_errors
def run_apply(
    run_id: Annotated[
        str | None, typer.Argument(help="Run ID to apply (creates new plan if omitted)")
    ] = None,
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace name (used when creating new plan)",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    message: Annotated[
        str | None, typer.Option("--message", "-m", help="Apply comment/reason")
    ] = None,
    auto_approve: Annotated[
        bool, typer.Option("--auto-approve", help="Skip confirmation prompt (for CI/CD)")
    ] = False,
    wait: Annotated[
        bool, typer.Option("--wait/--no-wait", help="Block until apply completes")
    ] = True,
    wait_queue: Annotated[
        bool,
        typer.Option(
            "--wait-queue",
            help="Wait for any current run to finish before triggering",
        ),
    ] = False,
    discard_older: Annotated[
        bool,
        typer.Option("--discard-older", help="Discard all pending/queued runs before triggering"),
    ] = False,
    debug_run: Annotated[
        bool, typer.Option("--debug-run", help="Enable TFC debugging-mode for this run")
    ] = False,
):
    """Apply infrastructure changes."""
    org, ws_context_name = validate_context(organization, workspace)

    with TFCClient(organization=org) as client:
        # If no run_id provided, create a new run with auto-apply
        if not run_id:
            # Need workspace for creating new run
            if not ws_context_name:
                raise ValueError(
                    "No workspace specified and could not detect from context.\n"
                    "Either:\n"
                    "  1. Run this command from a directory with terraform configuration (terraform.tf or .terraform/terraform.tfstate), or\n"
                    "  2. Specify workspace name: --workspace WORKSPACE_NAME"
                )
            workspace_name = ws_context_name

            ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

            # Queue management
            if discard_older:
                active_runs = client.runs.get_active_runs(ws.id)
                for r in active_runs:
                    if not r.status.is_terminal and r.status.value not in ["applying", "applied"]:
                        with suppress(Exception):
                            client.runs.discard(
                                r.id, comment="Discarded by terrapyne --discard-older"
                            )

            if wait_queue:
                active_runs = client.runs.get_active_runs(ws.id)
                if active_runs:
                    current_run = active_runs[0]
                    console.print(
                        f"[dim]Waiting for current run {current_run.id} "
                        f"({current_run.status.value}) to finish...[/dim]"
                    )
                    try:
                        client.runs.poll_until_complete(current_run.id)
                    except TimeoutError:
                        console.print("[red]Timeout waiting for current run to finish.[/red]")
                        raise typer.Exit(1) from None

            console.print(
                f"[dim]Creating [bold cyan]APPLY[/bold cyan] run for workspace:[/dim] "
                f"{workspace_name}"
            )

            # Create run with auto-apply
            run = client.runs.create(
                workspace_id=ws.id,
                message=message,
                auto_apply=True,
                debug=debug_run,
            )
            run_id = run.id
            console.print(f"[green]✓[/green] Created apply run: {run_id}")
        else:
            # Applying existing run
            client.runs.apply(run_id, comment=message)
            console.print(f"[green]✓[/green] Applied run: {run_id}")

        if not wait:
            return

        # Poll until complete
        console.print("\n[dim]Watching apply progress...[/dim]")

        def print_status(r):
            console.print(f"  {r.status.emoji} {r.status.value}", end="\r", style="dim")

        try:
            final_run = client.runs.poll_until_complete(run_id, callback=print_status)
            console.print(" " * 80, end="\r")  # Clear line

            render_run_detail(final_run, organization=org)

            if final_run.status.is_successful:
                console.print("\n[green]✓ Run completed successfully[/green]")
                raise typer.Exit(0)
            else:
                console.print(f"\n[red]✗ Run failed: {final_run.status.value}[/red]")
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


@app.command("errors")
@handle_cli_errors
def run_errors(
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="Filter by project name")
    ] = None,
    days: Annotated[int, typer.Option("--days", "-d", help="Look back period in days")] = 1,
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Maximum number of runs to show")
    ] = 50,
):
    """Find errored runs across workspaces."""
    # Resolve organization
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        project_id = None
        if project:
            projects, _ = client.projects.list(organization=org)
            target_proj = next((p for p in projects if p.name == project), None)
            if not target_proj:
                console.print(f"[red]❌ Project not found:[/red] {project}")
                raise typer.Exit(1)
            project_id = target_proj.id

        workspaces, _ = client.workspaces.list(organization=org, project_id=project_id)

        errored_runs: list[tuple[Run, str]] = []
        cutoff_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)

        with console.status("[bold green]Mining for errors...") as status:
            for ws in workspaces:
                status.update(f"[bold green]Checking workspace:[/bold green] {ws.name}")
                runs, _ = client.runs.list(workspace_id=ws.id, limit=limit, status="errored")

                for run in runs:
                    if run.created_at and run.created_at >= cutoff_date:
                        errored_runs.append((run, ws.name))

        if not errored_runs:
            proj_msg = f" in project '{project}'" if project else ""
            console.print(
                f"[green]✅ No errored runs found{proj_msg} in the last {days} day(s).[/green]"
            )
            return

        errored_runs.sort(
            key=lambda x: x[0].created_at or datetime.datetime.min.replace(tzinfo=datetime.UTC),
            reverse=True,
        )

        from rich.table import Table

        from terrapyne.utils.rich_tables import _format_relative_time

        table = Table(
            title=f"🚨 Errored Runs (Last {days} days)",
            show_header=True,
            header_style="bold red",
        )
        table.add_column("Workspace", style="cyan")
        table.add_column("Run ID", style="dim")
        table.add_column("Time", justify="right")
        table.add_column("Message")

        for run, ws_name in errored_runs[:limit]:
            relative_time = _format_relative_time(run.created_at) if run.created_at else "N/A"
            table.add_row(
                ws_name,
                run.id,
                relative_time,
                run.message or "[dim](No message)[/dim]",
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(errored_runs[:limit])} errored runs.[/dim]")


@app.command("trigger")
@handle_cli_errors
def run_trigger(
    workspace: Annotated[
        str | None,
        typer.Argument(
            help="Workspace name (auto-detected if omitted)",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization",
        ),
    ] = None,
    message: Annotated[str | None, typer.Option("--message", "-m", help="Run description")] = None,
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Resource address to target")
    ] = None,
    replace: Annotated[
        list[str] | None, typer.Option("--replace", "-r", help="Resource address to replace")
    ] = None,
    destroy: Annotated[bool, typer.Option("--destroy", help="Create a destroy run")] = False,
    refresh_only: Annotated[
        bool, typer.Option("--refresh-only", help="Create a refresh-only run")
    ] = False,
    auto_approve: Annotated[
        bool, typer.Option("--auto-approve", "-y", help="Skip confirmation")
    ] = False,
    wait: Annotated[
        bool, typer.Option("--wait/--no-wait", help="Block until run completes")
    ] = True,
    wait_queue: Annotated[
        bool,
        typer.Option(
            "--wait-queue",
            help="Wait for any current run to finish before triggering (block until available)",
        ),
    ] = False,
    discard_older: Annotated[
        bool,
        typer.Option("--discard-older", help="Discard all pending/queued runs before triggering"),
    ] = False,
    debug_run: Annotated[
        bool, typer.Option("--debug-run", help="Enable TFC debugging-mode for this run")
    ] = False,
):
    """Trigger a new run with optional targeting or replacement."""
    # Resolve context
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    # Destroy confirmation
    if (
        destroy
        and not auto_approve
        and not typer.confirm(
            f"[bold red]⚠️  WARNING:[/bold red] This will destroy all resources in '{workspace_name}'. Continue?"
        )
    ):
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit(0)

    with TFCClient(organization=org) as client:
        # Get workspace ID
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        # Queue management
        if discard_older:
            active_runs = client.runs.get_active_runs(ws.id)
            for r in active_runs:
                if not r.status.is_terminal and r.status.value not in ["applying", "applied"]:
                    with suppress(Exception):
                        client.runs.discard(r.id, comment="Discarded by terrapyne --discard-older")

        if wait_queue:
            active_runs = client.runs.get_active_runs(ws.id)
            if active_runs:
                current_run = active_runs[0]
                console.print(
                    f"[dim]Waiting for current run {current_run.id} "
                    f"({current_run.status.value}) to finish...[/dim]"
                )
                try:
                    client.runs.poll_until_complete(current_run.id)
                except TimeoutError:
                    console.print("[red]Timeout waiting for current run to finish.[/red]")
                    raise typer.Exit(1) from None

        # Identify run type
        run_type = "PLAN"
        if destroy:
            run_type = "DESTROY"
        elif refresh_only:
            run_type = "REFRESH"

        console.print(
            f"[dim]Triggering [bold cyan]{run_type}[/bold cyan] run for workspace:[/dim] "
            f"{workspace_name}"
        )

        # Create run
        run = client.runs.create(
            workspace_id=ws.id,
            message=message,
            auto_apply=auto_approve if destroy else False,
            is_destroy=destroy,
            target_addrs=target,
            replace_addrs=replace,
            refresh_only=refresh_only,
            debug=debug_run,
        )

        console.print(f"[green]✓[/green] Created {run_type} run: {run.id}")
        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not wait:
            console.print(
                f"\n[dim]View run at:[/dim] https://app.terraform.io/app/{org}/workspaces/{workspace_name}/runs/{run.id}"
            )
            return

        # Poll until complete
        console.print("\n[dim]Watching run progress...[/dim]")

        def print_status(r):
            console.print(f"  {r.status.emoji} {r.status.value}", end="\r", style="dim")

        try:
            final_run = client.runs.poll_until_complete(run.id, callback=print_status)
            console.print(" " * 80, end="\r")  # Clear line

            # Show final summary
            plan = None
            if final_run.plan_id:
                with suppress(Exception):
                    plan = client.runs.get_plan(final_run.plan_id)

            render_run_detail(final_run, workspace_name=workspace_name, organization=org, plan=plan)

            if not final_run.status.is_successful:
                if final_run.status.is_awaiting_approval:
                    console.print("\n[yellow]⏸ Run paused for manual approval.[/yellow]")
                    raise typer.Exit(0)
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


@app.command("watch")
@handle_cli_errors
def run_watch(
    run_id: Annotated[str, typer.Argument(help="Run ID to watch")],
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace name (optional)",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization",
        ),
    ] = None,
):
    """Watch run progress until complete."""
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # Watch progress
        console.print(f"\n[dim]Watching run progress for {run_id}...[/dim]")

        def print_status(r):
            console.print(f"  {r.status.emoji} {r.status.value}", end="\r", style="dim")

        try:
            final_run = client.runs.poll_until_complete(run_id, callback=print_status)
            console.print(" " * 80, end="\r")  # Clear line

            # Show final summary
            plan = None
            if final_run.plan_id:
                with suppress(Exception):
                    plan = client.runs.get_plan(final_run.plan_id)

            render_run_detail(final_run, organization=org, plan=plan)

            if not final_run.status.is_successful:
                if final_run.status.is_awaiting_approval:
                    console.print("\n[yellow]⏸ Run paused for manual approval.[/yellow]")
                    raise typer.Exit(0)
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


def _print_log_delta(full_log: str, last_pos: int) -> int:
    """Print new log content since last position.

    Args:
        full_log: Complete log content
        last_pos: Last position read

    Returns:
        New position (length of full_log)
    """
    new_content = full_log[last_pos:]
    if new_content:
        print(new_content, end="", flush=True)
    return len(full_log)


@app.command("follow")
@handle_cli_errors
def run_follow(
    run_id: Annotated[str, typer.Argument(help="Run ID to follow")],
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization",
        ),
    ] = None,
    max_wait: Annotated[
        int,
        typer.Option(
            "--max-wait",
            help="Maximum time to wait in seconds (default: 30 minutes)",
        ),
    ] = 1800,
):
    """Follow a run's logs in real-time.

    Streams plan and apply logs as they happen, polling at exponential intervals.
    Exits when the run reaches a terminal state.

    Examples:
        # Follow a specific run
        terrapyne run follow run-abc123

        # Follow with custom timeout (5 minutes)
        terrapyne run follow run-abc123 --max-wait 300
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        console.print(f"\n[dim]Following run {run_id}...[/dim]\n")

        last_plan_pos = 0
        last_apply_pos = 0
        current_stage = None  # Track which stage we're in

        def stream_logs(run: Run) -> None:
            nonlocal last_plan_pos, last_apply_pos, current_stage

            # Determine which logs to fetch based on run status
            if run.plan_id and run.status.value in [
                "planning",
                "planned",
                "queued",
                "applying",
                "applied",
            ]:
                if current_stage != "plan":
                    current_stage = "plan"
                    console.print("[dim]📋 Plan:[/dim]")
                try:
                    plan_log = client.runs.get_plan_logs(run.plan_id)
                    last_plan_pos = _print_log_delta(plan_log, last_plan_pos)
                except Exception:
                    pass  # Silently skip if logs not available yet

            # Once in apply stage, show apply logs
            if run.apply_id and run.status.value in ["applying", "applied"]:
                if current_stage != "apply":
                    current_stage = "apply"
                    console.print("\n[dim]⚙️  Apply:[/dim]")
                try:
                    apply_log = client.runs.get_apply_logs(run.apply_id)
                    last_apply_pos = _print_log_delta(apply_log, last_apply_pos)
                except Exception:
                    pass  # Silently skip if logs not available yet

        try:
            final_run = client.runs.poll_until_complete(
                run_id, callback=stream_logs, max_wait=float(max_wait)
            )

            # Print final newline and status
            print()
            if final_run.status.is_successful:
                console.print(f"\n[green]✓ Run {run_id} completed successfully[/green]")
            elif final_run.status.is_awaiting_approval:
                console.print(f"\n[yellow]⏸ Run {run_id} is awaiting approval[/yellow]")
            else:
                console.print(f"\n[red]✗ Run {run_id} failed: {final_run.status.value}[/red]")
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


@app.command("discard")
@handle_cli_errors
def run_discard(
    run_id: Annotated[str, typer.Argument(help="Run ID to discard (run-*)")],
    comment: Annotated[
        str | None, typer.Option("--comment", "-m", help="Reason for discarding")
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization",
        ),
    ] = None,
):
    """Discard a run that is in a non-terminal state."""
    org, _ = validate_context(organization)
    with TFCClient(organization=org) as client:
        client.runs.discard(run_id, comment=comment)
        console.print(f"[green]✓[/green] Run {run_id} discarded.")


@app.command("cancel")
@handle_cli_errors
def run_cancel(
    run_id: Annotated[str, typer.Argument(help="Run ID to cancel (run-*)")],
    comment: Annotated[
        str | None, typer.Option("--comment", "-m", help="Reason for canceling")
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization",
        ),
    ] = None,
):
    """Cancel a run that is currently planning or applying."""
    org, _ = validate_context(organization)
    with TFCClient(organization=org) as client:
        client.runs.cancel(run_id, comment=comment)
        console.print(f"[green]✓[/green] Run {run_id} canceled.")


@app.command("parse-plan")
@handle_cli_errors
def run_parse_plan(
    plan_file: Annotated[
        Path | None,
        typer.Argument(help="Path to terraform plan output file, or - to read from stdin"),
    ] = None,
    output_format: Annotated[
        str, typer.Option("--format", "-f", help="Output format: human, json")
    ] = "human",
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Save parsed plan to file")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed output")] = False,
):
    """Parse plain text terraform plan output."""

    # Read plan from stdin or file
    if plan_file is None or str(plan_file) == "-":
        plan_text = sys.stdin.read()
    elif not plan_file.exists():
        console.print(f"[red]❌ Plan file not found:[/red] {plan_file}")
        raise typer.Exit(1)
    else:
        with open(plan_file) as f:
            plan_text = f.read()

    # Parse it
    from terrapyne.terrapyne import Terraform

    tf = Terraform(".")
    result = tf.parse_plain_text_plan(plan_text)

    # Format output
    if output_format == "json":
        output_text = json.dumps(result, indent=2)
    else:
        output_text = _format_plan_output_human(result, verbose=verbose)

    # Display or save
    if output:
        with open(output, "w") as f:
            f.write(output_text)
        console.print(f"[green]✅ Parsed plan saved to[/green] {output}")
    # Use print() for JSON to avoid Rich mangling embedded newlines/control chars
    elif output_format == "json":
        print(output_text)
    else:
        console.print(output_text)


def _format_plan_output_human(result: dict[str, Any], verbose: bool = False) -> str:
    """Format parsed plan for human-readable output."""
    lines = []

    # Summary
    if result.get("resource_changes"):
        lines.append(f"📊 Resources: {len(result['resource_changes'])} changes")
        for rc in result["resource_changes"]:
            actions = ", ".join(rc["change"]["actions"])
            lines.append(f"  • {rc['address']} ({actions})")
    else:
        lines.append("📊 Resources: No changes")

    # Plan summary
    if result.get("plan_summary"):
        summary = result["plan_summary"]
        parts = []
        if summary.get("add", 0) > 0:
            parts.append(f"+{summary['add']}")
        if summary.get("change", 0) > 0:
            parts.append(f"~{summary['change']}")
        if summary.get("destroy", 0) > 0:
            parts.append(f"-{summary['destroy']}")
        if summary.get("import", 0) > 0:
            parts.append(f"📥{summary['import']}")
        if parts:
            lines.append(f"Summary: {', '.join(parts)}")

    # Plan status
    if result.get("plan_status"):
        status_icon = {"planned": "✅", "failed": "❌", "incomplete": "⚠️"}.get(
            result["plan_status"], "❓"
        )
        lines.append(f"{status_icon} Status: {result['plan_status']}")

    # Errors
    if result.get("diagnostics"):
        lines.append(f"\n⚠️  Errors found: {len(result['diagnostics'])}")
        for diag in result["diagnostics"]:
            lines.append(f"  • {diag.get('summary', 'Unknown error')}")
            if verbose and diag.get("detail"):
                lines.append(f"    {diag['detail']}")

    return "\n".join(lines)
