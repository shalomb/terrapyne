"""Run CLI commands."""

import datetime
import time
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from terrapyne.api.client import TFCClient
from terrapyne.cli.utils import handle_cli_errors, validate_context
from terrapyne.models.run import Run, RunStatus
from terrapyne.terrapyne import Terraform
from terrapyne.utils.rich_tables import render_run_detail, render_runs

app = typer.Typer(help="Run management commands")
console = Console()


# Pure functions for log streaming
def _extract_new_lines(previous: str, current: str) -> list[str]:
    """Extract only the new lines from the current content.

    Compares current log content against previously fetched content and returns
    only the lines that have been added since the last fetch. Uses byte-offset
    tracking (string length) to avoid re-processing old content.

    Args:
        previous: Previously fetched log content (may be empty string on first call)
        current: Current log content from API

    Returns:
        List of new log lines that have been added since the last fetch.
        Returns empty list if current is not longer than previous (no new content).
    """
    if len(current) <= len(previous):
        return []
    return current[len(previous) :].splitlines()


def _fetch_run_logs_incrementally(
    run_id: str,
    client,
    sleep_fn=time.sleep,
    poll_interval: float = 1.0,
    max_wait: float = 1800.0,
) -> Iterator[str]:
    """Stream log lines from a run as they become available.

    Polls TFC run status and log endpoints on a regular interval, yielding only
    new log lines since the last fetch. Tracks both plan and apply logs with
    separate offset counters to handle runs that transition through planning
    to applying.

    Args:
        run_id: TFC run ID to stream logs for
        client: TFCClient instance for API calls
        sleep_fn: Function to sleep (injectable for testing)
        poll_interval: Seconds between API polls (default 1.0)
        max_wait: Maximum seconds to wait before giving up (default 1800, 30min)

    Yields:
        Individual log lines as they arrive from the API
    """
    seen_plan = ""
    seen_apply = ""
    interval = poll_interval
    start = time.monotonic()

    while True:
        run = client.runs.get(run_id)

        # Fetch and yield plan logs if run has a plan
        if run.plan_id:
            with suppress(Exception):
                current = client.runs.get_plan_logs(run.plan_id)
                for line in _extract_new_lines(seen_plan, current):
                    yield line
                seen_plan = current

        # Fetch and yield apply logs if run has an apply
        if run.apply_id:
            with suppress(Exception):
                current = client.runs.get_apply_logs(run.apply_id)
                for line in _extract_new_lines(seen_apply, current):
                    yield line
                seen_apply = current

        # Check if run has reached a terminal state
        if run.status.is_terminal:
            return

        # Check if max_wait has been exceeded
        if time.monotonic() - start >= max_wait:
            return

        sleep_fn(interval)


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def run_list(
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Target TFC workspace name. If omitted, attempts auto-detection from local Terraform context.",
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local Terraform context.",
    ),
    limit: int = typer.Option(
        20, "--limit", "-n", help="Maximum number of recent runs to retrieve and display."
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter results by specific run status (e.g., 'applied', 'planned', 'errored').",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Control the output style. 'table' is human-readable, 'json' is optimized for automation.",
    ),
):
    """List runs for a workspace.

    Auto-detects workspace and organization from .terraform/terraform.tfstate or terraform.tf if not specified.

    Examples:
        # List recent runs for current workspace
        terrapyne run list

        # List runs for specific workspace
        terrapyne run list --workspace my-app-dev

        # List only applied runs
        terrapyne run list --status applied

        # List last 50 runs
        terrapyne run list --limit 50
    """
    # Resolve workspace and organization
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        # Get workspace to retrieve workspace ID
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        # List runs
        runs, total_count = client.runs.list(workspace_id=ws.id, limit=limit, status=status)

        if not runs:
            status_msg = f" with status '{status}'" if status else ""
            console.print(
                f"[yellow]No runs found for workspace '{workspace_name}'{status_msg}.[/yellow]"
            )
            return

        if output_format == "json":
            from terrapyne.cli.utils import emit_json

            emit_json(
                [
                    {
                        "id": r.id,
                        "status": r.status.value,
                        "message": r.message,
                        "created_at": r.created_at,
                        "resource_additions": r.resource_additions,
                        "resource_changes": r.resource_changes,
                        "resource_destructions": r.resource_destructions,
                    }
                    for r in runs
                ]
            )
            return

        # Render runs table
        title = f"Runs for {workspace_name}"
        if status:
            title += f" (status: {status})"
        render_runs(runs, title=title, total_count=total_count)


@app.command("show")
@handle_cli_errors
def run_show(
    run_id: str = typer.Argument(
        ..., help="The unique TFC Run ID to display (e.g., 'run-abc123')."
    ),
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Optional workspace name to provide context for display and deep links.",
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Control the output style. 'table' is human-readable, 'json' is optimized for automation.",
    ),
):
    """Show detailed information about a run.

    Examples:
        # Show run by ID
        terrapyne run show run-abc123

        # Show run with workspace context
        terrapyne run show run-abc123 --workspace my-app-dev
    """
    # Resolve organization (optional for this command)
    org, _ = validate_context(organization)

    # Try to resolve workspace if not provided
    if not workspace:
        try:
            _, workspace = validate_context(organization, workspace)
        except ValueError:
            # Workspace resolution failed, continue without it
            workspace = None

    with TFCClient(organization=org) as client:
        # Get run details
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
            from terrapyne.cli.utils import emit_json

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


def _stream_run_logs(
    client: TFCClient,
    run_id: str,
    allow_blocked: bool = False,
    discard_older: bool = False,
) -> Run:
    """Stream plan and apply logs for a run until completion."""
    import time

    last_plan_pos = 0
    last_apply_pos = 0
    last_status = None
    plan_started = False
    apply_started = False
    blocked_notified = False

    console.print(f"\n[bold blue]Streaming logs for run {run_id}...[/bold blue]")

    while True:
        try:
            run = client.runs.get(run_id)
        except Exception:
            # If status fetch fails, wait and retry
            time.sleep(5)
            continue

        # Print status transitions
        if run.status != last_status:
            if not plan_started and not apply_started:
                console.print(f"  {run.status.emoji} [dim]{run.status.value}...[/dim]")
            last_status = run.status

        # Queue block detection & handling
        if run.status == "pending" and not blocked_notified:
            try:
                # Find the root cause: the EARLIEST run that is not terminal
                if run.workspace_id:
                    # Fetch more to see deeper into the queue
                    runs, _ = client.runs.list(run.workspace_id, limit=100)
                    active_runs = [r for r in runs if not r.status.is_terminal]
                    if len(active_runs) > 1:
                        # Find runs created BEFORE this one
                        earlier_runs = [r for r in active_runs if r.id != run_id]
                        if earlier_runs:
                            # The root blocker is the oldest one (last in the list)
                            root_blocker = earlier_runs[-1]

                            if discard_older:
                                console.print(
                                    f"  [yellow]clearing...[/yellow] Automatically discarding {len(earlier_runs)} earlier run(s) blocking the queue"
                                )
                                for r_to_clear in earlier_runs:
                                    try:
                                        # Use discard for planned/cost_estimated, cancel for pending/queuing
                                        if r_to_clear.status in [
                                            RunStatus.PLANNED,
                                            RunStatus.COST_ESTIMATED,
                                            RunStatus.COST_ESTIMATING,
                                            RunStatus.POLICY_CHECKED,
                                            RunStatus.POLICY_SOFT_FAILED,
                                        ]:
                                            client.runs.discard(
                                                r_to_clear.id,
                                                comment="Discarded by terrapyne to unblock newer run",
                                            )
                                        else:
                                            client.runs.cancel(
                                                r_to_clear.id,
                                                comment="Canceled by terrapyne to unblock newer run",
                                            )
                                    except Exception as e:
                                        console.print(
                                            f"  [red]Warning:[/red] Failed to clear run {r_to_clear.id}: {e}"
                                        )

                                # Reset notification so we can check again after clearing
                                blocked_notified = False
                                time.sleep(2)
                                continue

                            console.print(
                                f"  [yellow]waiting...[/yellow] Workspace is blocked by earlier run [bold]{root_blocker.id}[/bold] ({root_blocker.status.value})"
                            )
                            console.print(
                                f"  [dim]Tip: Use 'tfc run discard {root_blocker.id}' or trigger with --discard-older[/dim]"
                            )

                            if not allow_blocked:
                                console.print(
                                    "\n[red]Error:[/red] Exiting because workspace is blocked. Use --wait to stay in queue or --discard-older to clear it."
                                )
                                raise typer.Exit(1)

                            blocked_notified = True
            except typer.Exit:
                raise
            except Exception:
                pass

        # Stream plan logs
        if run.plan_id and run.status not in [
            RunStatus.PENDING,
            RunStatus.QUEUING,
            RunStatus.FETCHING,
            RunStatus.PLAN_QUEUED,
        ]:
            try:
                logs = client.runs.get_plan_logs(run.plan_id)
                new_content = logs[last_plan_pos:]
                if new_content:
                    if not plan_started:
                        console.print(f"  {run.status.emoji} [bold]Planning started...[/bold]")
                        plan_started = True
                    print(new_content, end="", flush=True)
                    last_plan_pos = len(logs)
            except Exception:
                pass

        # Stream apply logs if applicable
        if run.apply_id and run.status == RunStatus.APPLYING:
            try:
                logs = client.runs.get_apply_logs(run.apply_id)
                new_content = logs[last_apply_pos:]
                if new_content:
                    if not apply_started:
                        console.print(f"\n  {run.status.emoji} [bold]Applying started...[/bold]")
                        apply_started = True
                    print(new_content, end="", flush=True)
                    last_apply_pos = len(logs)
            except Exception:
                pass

        # Check if run is waiting for approval
        if run.is_awaiting_approval and not run.auto_apply:
            # Final log fetch
            if run.plan_id:
                with suppress(Exception):
                    logs = client.runs.get_plan_logs(run.plan_id)
                    new_content = logs[last_plan_pos:]
                    if new_content:
                        print(new_content, end="", flush=True)

            console.print(f"\n  {run.status.emoji} [bold yellow]Awaiting Approval[/bold yellow]")
            console.print(
                f"  [dim]Run has paused at '{run.status.value}'. Approve in TFC or use 'tfc run apply {run.id}' to proceed.[/dim]"
            )
            return run

        if run.status.is_terminal:
            # Final log fetch to ensure we didn't miss the tail
            # We fetch one last time if we have IDs
            time.sleep(1)  # Give TFC a moment to finalize logs
            if run.plan_id:
                with suppress(Exception):
                    logs = client.runs.get_plan_logs(run.plan_id)
                    new_content = logs[last_plan_pos:]
                    if new_content:
                        print(new_content, end="", flush=True)

            if run.apply_id:
                with suppress(Exception):
                    logs = client.runs.get_apply_logs(run.apply_id)
                    new_content = logs[last_apply_pos:]
                    if new_content:
                        print(new_content, end="", flush=True)

            console.print(f"\n  {run.status.emoji} [bold]Run {run.status.value}[/bold]")
            return run

        time.sleep(2)


@app.command("plan")
@handle_cli_errors
def run_plan(
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Target TFC workspace name. If omitted, attempts auto-detection from local Terraform context.",
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    message: str | None = typer.Option(
        None,
        "--message",
        "-m",
        help="A descriptive title or comment for the run, visible in TFC history.",
    ),
    watch: bool = typer.Option(
        True,
        "--watch/--no-watch",
        help="Monitor the run's progress in real-time until it reaches a terminal state.",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream live plan and apply logs to the console while watching.",
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        help="If the workspace is locked by another run, stay in the queue until it becomes available instead of exiting immediately.",
    ),
    discard_older: bool = typer.Option(
        False,
        "--discard-older",
        help="Automatically discard or cancel any existing runs that are blocking the queue for this workspace.",
    ),
    debug_run: bool = typer.Option(
        False,
        "--debug-run",
        help="Enable TFC 'debugging-mode' for this specific run to capture verbose internal logs.",
    ),
):
    """Create a new plan (run) for a workspace.

    Auto-detects workspace and organization from .terraform/terraform.tfstate or terraform.tf if not specified.

    Examples:
        # Create plan for current workspace
        terrapyne run plan

        # Create plan with TFC debug mode enabled
        terrapyne run plan --debug-run

        # Create plan and clear any blocking runs
        terrapyne run plan --discard-older

        # Create plan without watching
        terrapyne run plan --no-watch
    """
    # Resolve workspace and organization
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        # Get workspace to retrieve workspace ID
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        console.print(f"[dim]Creating plan for workspace:[/dim] {workspace_name}")

        # Create run
        run = client.runs.create(
            workspace_id=ws.id, message=message, auto_apply=False, debug=debug_run
        )

        run_type = "plan-only"
        console.print(f"[green]✓[/green] Created [bold]{run_type}[/bold] run: {run.id}")
        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not watch:
            console.print(
                f"\n[dim]View run at:[/dim] https://app.terraform.io/app/{org}/workspaces/{workspace_name}/runs/{run.id}"
            )
            return

        # Watch
        if stream:
            final_run = _stream_run_logs(
                client, run.id, allow_blocked=wait, discard_older=discard_older
            )
        else:
            console.print("\n[dim]Polling run status...[/dim]")

            def print_status(r):
                console.print(f"  {r.status.emoji} {r.status.value}", end="\r", style="dim")

            final_run = client.runs.poll_until_complete(run.id, callback=print_status)
            console.print(" " * 80, end="\r")

        # Fetch plan details for accurate resource counts
        plan = None
        if final_run.plan_id:
            with suppress(Exception):
                plan = client.runs.get_plan(final_run.plan_id)

        # Show final status
        render_run_detail(final_run, workspace_name=workspace_name, organization=org, plan=plan)

        # Exit with appropriate code
        if final_run.status.is_successful:
            console.print("\n[green]✓ Plan completed successfully[/green]")
            raise typer.Exit(0)
        else:
            console.print(f"\n[red]✗ Plan failed: {final_run.status.value}[/red]")
            raise typer.Exit(1)


@app.command("logs")
@handle_cli_errors
def run_logs(
    run_id: str = typer.Argument(..., help="The unique TFC Run ID to retrieve logs for."),
    log_type: str = typer.Option(
        "plan", "--type", "-t", help="The lifecycle phase to retrieve logs for: 'plan' or 'apply'."
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
):
    """View plan or apply logs for a run.

    Examples:
        # View plan logs
        terrapyne run logs run-abc123

        # View apply logs
        terrapyne run logs run-abc123 --type apply
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        run = client.runs.get(run_id)

        console.print(
            f"[dim]Run:[/dim] {run_id} [dim]({run.status.emoji} {run.status.value})[/dim]"
        )

        if log_type == "apply":
            if not run.apply_id:
                console.print("[yellow]No apply logs available for this run.[/yellow]")
                raise typer.Exit(1)
            try:
                logs = client.runs.get_apply_logs(run.apply_id)
            except Exception:
                console.print(
                    "[yellow]Apply logs unavailable — run may have errored before apply started.[/yellow]"
                )
                raise typer.Exit(1) from None
        else:
            if not run.plan_id:
                console.print("[yellow]No plan logs available for this run.[/yellow]")
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
    run_id: str | None = typer.Argument(
        None,
        help="The specific TFC Run ID to apply. If omitted, a new plan-and-apply run will be triggered.",
    ),
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Target TFC workspace name (required if run_id is omitted).",
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
    message: str | None = typer.Option(
        None, "--message", "-m", help="An optional comment or reason for the apply operation."
    ),
    auto_approve: bool = typer.Option(
        False,
        "--auto-approve",
        help="Skip the interactive confirmation prompt. Essential for non-interactive CI/CD environments.",
    ),
    watch: bool = typer.Option(
        True,
        "--watch/--no-watch",
        help="Monitor the run's progress in real-time until it reaches a terminal state.",
    ),
    stream: bool = typer.Option(
        True, "--stream/--no-stream", help="Stream live apply logs to the console while watching."
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        help="If the workspace is locked by another run, stay in the queue until it becomes available instead of exiting immediately.",
    ),
    discard_older: bool = typer.Option(
        False,
        "--discard-older",
        help="Automatically discard or cancel any existing runs that are blocking the queue for this workspace.",
    ),
):
    """Apply infrastructure changes.

    Can either apply an existing run or create a new plan+apply.

    Examples:
        # Apply existing run
        terrapyne run apply run-abc123

        # Create plan and auto-apply (CI/CD mode)
        terrapyne run apply --auto-approve --message "Deploy to production"

        # Apply without watching
        terrapyne run apply run-abc123 --no-watch
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # If no run_id provided, create a new run with auto-apply
        if not run_id:
            # Need workspace for creating new run
            org, workspace_name = validate_context(organization, workspace, require_workspace=True)

            ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

            console.print(f"[dim]Creating plan+apply run for workspace:[/dim] {workspace_name}")

            # Create run with auto-apply
            run = client.runs.create(workspace_id=ws.id, message=message, auto_apply=True)

            console.print(f"[green]✓[/green] Created run: {run.id}")
            run_id = run.id
        else:
            # Apply existing run
            run = client.runs.get(run_id)

            # Confirmation prompt (unless auto_approve)
            if not auto_approve and not typer.confirm(f"Apply run {run_id} ({run.status.value})?"):
                console.print("[yellow]Aborted.[/yellow]")
                raise typer.Exit(0)

            console.print(f"[dim]Applying run:[/dim] {run_id}")

            run = client.runs.apply(run_id, comment=message)
            console.print("[green]✓[/green] Apply triggered")

        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not watch:
            return

        # Watch
        if stream:
            final_run = _stream_run_logs(
                client, run_id, allow_blocked=wait, discard_older=discard_older
            )
        else:
            console.print("\n[dim]Polling apply status...[/dim]")

            def print_status(r):
                console.print(f"  {r.status.emoji} {r.status.value}", end="\r", style="dim")

            final_run = client.runs.poll_until_complete(run_id, callback=print_status)
            console.print(" " * 80, end="\r")

        # Fetch plan details for accurate resource counts
        plan = None
        if final_run.plan_id:
            with suppress(Exception):
                plan = client.runs.get_plan(final_run.plan_id)

        # Show final status
        render_run_detail(final_run, workspace_name=workspace, organization=org, plan=plan)

        # Exit with appropriate code
        if final_run.status.value == "applied":
            console.print("\n[green]✓ Apply completed successfully[/green]")
            raise typer.Exit(0)
        else:
            console.print(f"\n[red]✗ Apply failed: {final_run.status.value}[/red]")
            raise typer.Exit(1)


@app.command("errors")
@handle_cli_errors
def run_errors(
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
        ),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Filter error search to a specific TFC project name."),
    ] = None,
    days: Annotated[
        int, typer.Option("--days", "-d", help="Number of days to look back for errored runs.")
    ] = 1,
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Maximum number of errors to retrieve and display.")
    ] = 50,
):
    """Find errored runs across workspaces.

    Examples:
        # Show all errored runs in organization from last 24h
        terrapyne run errors

        # Show errors in a specific project from last 7 days
        terrapyne run errors --project platform --days 7
    """
    # Resolve organization
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # 1. Resolve project ID if provided
        project_id = None
        if project:
            projects, _ = client.projects.list(organization=org)
            target_proj = next((p for p in projects if p.name == project), None)
            if not target_proj:
                console.print(f"[red]❌ Project not found:[/red] {project}")
                raise typer.Exit(1)
            project_id = target_proj.id

        # 2. List workspaces
        workspaces, _ = client.workspaces.list(organization=org, project_id=project_id)

        # 3. Fetch errored runs for each workspace
        errored_runs: list[tuple[Run, str]] = []
        cutoff_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)

        with console.status("[bold green]Mining for errors...") as status:
            for ws in workspaces:
                status.update(f"[bold green]Checking workspace:[/bold green] {ws.name}")
                # Fetch recent runs with status=errored
                # Note: TFC API filter[status]=errored works!
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

        # 4. Sort by creation date (descending)
        errored_runs.sort(
            key=lambda x: (
                x[0].created_at
                or __import__("datetime").datetime.min.replace(tzinfo=__import__("datetime").UTC)
            ),
            reverse=True,
        )

        # 5. Render results
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
            help="Target TFC workspace name. If omitted, attempts auto-detection from local Terraform context.",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
        ),
    ] = None,
    message: Annotated[
        str | None,
        typer.Option(
            "--message",
            "-m",
            help="A descriptive title or comment for the run, visible in TFC history.",
        ),
    ] = None,
    target: Annotated[
        list[str] | None,
        typer.Option(
            "--target",
            "-t",
            help="Limit the plan to specific resource addresses (can be specified multiple times).",
        ),
    ] = None,
    replace: Annotated[
        list[str] | None,
        typer.Option(
            "--replace",
            "-r",
            help="Force the recreation of specific resource addresses (can be specified multiple times).",
        ),
    ] = None,
    destroy: Annotated[
        bool,
        typer.Option(
            "--destroy",
            help="Trigger a run that will destroy all resources managed by the workspace configuration.",
        ),
    ] = False,
    refresh_only: Annotated[
        bool,
        typer.Option(
            "--refresh-only",
            help="Trigger a run that only updates the TFC state to match reality without proposing configuration changes.",
        ),
    ] = False,
    auto_apply: Annotated[
        bool,
        typer.Option(
            "--auto-apply",
            "-y",
            help="Automatically proceed to the apply phase if the plan is successful, bypassing human approval.",
        ),
    ] = False,
    watch: bool = typer.Option(
        True,
        "--watch/--no-watch",
        help="Monitor the run's progress in real-time until it reaches a terminal state.",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream live plan and apply logs to the console while watching.",
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        help="If the workspace is locked by another run, stay in the queue until it becomes available instead of exiting immediately.",
    ),
    discard_older: bool = typer.Option(
        False,
        "--discard-older",
        help="Automatically discard or cancel any existing runs that are blocking the queue for this workspace.",
    ),
    debug_run: bool = typer.Option(
        False,
        "--debug-run",
        help="Enable TFC 'debugging-mode' for this specific run to capture verbose internal logs.",
    ),
):
    """Trigger a new run with optional targeting or replacement.

    Examples:
        # Trigger normal plan
        terrapyne run trigger my-app-dev

        # Trigger plan with TFC debug mode enabled
        terrapyne run trigger my-app-dev --debug-run

        # Trigger plan and automatically apply
        terrapyne run trigger my-app-dev --auto-apply

        # Targeted plan for specific resources
        terrapyne run trigger --target aws_instance.web --target aws_iam_role.admin

        # Force replacement of a resource
        terrapyne run trigger --replace aws_instance.web

        # Destroy run with confirmation
        terrapyne run trigger --destroy
    """
    # Resolve context
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    # Destroy confirmation
    if (
        destroy
        and not auto_apply
        and not typer.confirm(
            f"[bold red]⚠️  WARNING:[/bold red] This will destroy all resources in '{workspace_name}'. Continue?"
        )
    ):
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit(0)

    with TFCClient(organization=org) as client:
        # Get workspace ID
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        console.print(f"[dim]Triggering run for workspace:[/dim] {workspace_name}")
        if target:
            console.print(f"[dim]Targets:[/dim] {', '.join(target)}")
        if replace:
            console.print(f"[dim]Replacements:[/dim] {', '.join(replace)}")

        # Create run
        run = client.runs.create(
            workspace_id=ws.id,
            message=message,
            auto_apply=auto_apply,
            is_destroy=destroy,
            target_addrs=target,
            replace_addrs=replace,
            refresh_only=refresh_only,
            debug=debug_run,
        )

        # Determine run type for display
        if destroy:
            run_type = "destroy"
        elif refresh_only:
            run_type = "refresh-only"
        elif auto_apply:
            run_type = "plan-and-apply"
        else:
            run_type = "plan-only"

        console.print(f"[green]✓[/green] Created [bold]{run_type}[/bold] run: {run.id}")
        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not watch:
            console.print(
                f"\n[dim]View run at:[/dim] https://app.terraform.io/app/{org}/workspaces/{workspace_name}/runs/{run.id}"
            )
            return

        # Watch
        if stream:
            final_run = _stream_run_logs(
                client, run.id, allow_blocked=wait, discard_older=discard_older
            )
        else:
            console.print("\n[dim]Watching run progress...[/dim]")

            def print_status(r):
                console.print(f"  {r.status.emoji} {r.status.value}", end="\r", style="dim")

            final_run = client.runs.poll_until_complete(run.id, callback=print_status)
            console.print(" " * 80, end="\r")  # Clear line

        # Show final summary
        plan = None
        if final_run.plan_id:
            with suppress(Exception):
                plan = client.runs.get_plan(final_run.plan_id)

        render_run_detail(final_run, workspace_name=workspace_name, organization=org, plan=plan)

        if not final_run.status.is_successful:
            raise typer.Exit(1)


@app.command("watch")
@handle_cli_errors
def run_watch(
    run_id: Annotated[str, typer.Argument(help="The unique TFC Run ID to monitor.")],
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Target TFC workspace name. If omitted, attempts auto-detection from local context.",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
        ),
    ] = None,
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream live plan and apply logs to the console while watching.",
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        help="If the workspace is locked by another run, stay in the queue until it becomes available instead of exiting immediately.",
    ),
    discard_older: bool = typer.Option(
        False,
        "--discard-older",
        help="Automatically discard or cancel any existing runs that are blocking the queue for this workspace.",
    ),
):
    """Watch run progress until terminal state.

    Examples:
        # Watch a specific run with log streaming
        terrapyne run watch run-abc123

        # Watch without log streaming (status only)
        terrapyne run watch run-abc123 --no-stream
    """
    org, workspace_name = validate_context(organization, workspace)

    with TFCClient(organization=org) as client:
        console.print(f"[dim]Watching run:[/dim] {run_id}")

        if stream:
            final_run = _stream_run_logs(
                client, run_id, allow_blocked=wait, discard_older=discard_older
            )
        else:
            console.print("\n[dim]Watching run progress...[/dim]")

            def print_status(r):
                console.print(f"  {r.status.emoji} {r.status.value}", end="\r", style="dim")

            final_run = client.runs.poll_until_complete(run_id, callback=print_status)
            console.print(" " * 80, end="\r")  # Clear line

        # Show final summary
        plan = None
        if final_run.plan_id:
            with suppress(Exception):
                plan = client.runs.get_plan(final_run.plan_id)

        render_run_detail(final_run, workspace_name=workspace_name, organization=org, plan=plan)

        if not final_run.status.is_successful:
            raise typer.Exit(1)


@app.command("discard")
@handle_cli_errors
def run_discard(
    run_id: str = typer.Argument(..., help="The unique TFC Run ID to discard."),
    comment: str | None = typer.Option(
        None,
        "--comment",
        "-m",
        help="An optional comment explaining the reason for discarding the run.",
    ),
    organization: str | None = typer.Option(
        None,
        "-o",
        "--organization",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
):
    """Discard a run that is awaiting confirmation.

    Examples:
        # Discard a run
        terrapyne run discard run-abc123

        # Discard with reason
        terrapyne run discard run-abc123 --comment "Testing queue clearing"
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        if not typer.confirm(f"Discard run {run_id}?"):
            raise typer.Exit(0)

        run = client.runs.discard(run_id, comment=comment)
        console.print(f"[green]✓[/green] Run {run_id} discarded (status: {run.status.value})")


@app.command("cancel")
@handle_cli_errors
def run_cancel(
    run_id: str = typer.Argument(..., help="The unique TFC Run ID to cancel."),
    comment: str | None = typer.Option(
        None,
        "--comment",
        "-m",
        help="An optional comment explaining the reason for canceling the run.",
    ),
    organization: str | None = typer.Option(
        None,
        "-o",
        "--organization",
        help="Target TFC organization name. If omitted, attempts auto-detection from local context.",
    ),
):
    """Cancel a run that is currently queued or in progress.

    Examples:
        # Cancel a run
        terrapyne run cancel run-abc123
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        if not typer.confirm(f"Cancel run {run_id}?"):
            raise typer.Exit(0)

        run = client.runs.cancel(run_id, comment=comment)
        console.print(f"[green]✓[/green] Run {run_id} canceled (status: {run.status.value})")


@app.command("parse-plan")
@handle_cli_errors
def run_parse_plan(
    plan_file: Annotated[
        Path | None,
        typer.Argument(
            help="Path to the plain text terraform plan output file. Use '-' to read from standard input."
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Control the output style. 'human' is readable, 'json' is for machine processing.",
        ),
    ] = "human",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional path to save the parsed results to a file."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed diagnostic information and full resource addresses.",
        ),
    ] = False,
):
    """Parse plain text terraform plan output.

    Useful for parsing plans from Terraform Cloud remote backend
    where terraform plan -json is not available.

    Examples:
        # Parse plan and show summary
        terrapyne run parse-plan plan.txt

        # Read from stdin (pipe-friendly)
        terraform plan 2>&1 | terrapyne run parse-plan -

        # Output as JSON
        terrapyne run parse-plan plan.txt --format json

        # Save to file
        terrapyne run parse-plan plan.txt --output parsed.json
    """
    import sys

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
    tf = Terraform(".")
    result = tf.parse_plain_text_plan(plan_text)

    # Format output
    if output_format == "json":
        import json

        output_text = json.dumps(result, indent=2)
    else:  # human
        output_text = _format_plan_output_human(result, verbose=verbose)

    # Display or save
    if output:
        with open(output, "w") as f:
            f.write(output_text)
        console.print(f"[green]✅ Parsed plan saved to[/green] {output}")
    else:
        # Use print() for JSON to avoid Rich mangling embedded newlines/control chars
        if output_format == "json":
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
