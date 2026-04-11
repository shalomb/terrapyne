"""Run CLI commands."""

import datetime
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from terrapyne.api.client import TFCClient
from terrapyne.cli.utils import handle_cli_errors, validate_context
from terrapyne.models.run import Run
from terrapyne.terrapyne import Terraform
from terrapyne.utils.rich_tables import render_run_detail, render_runs

app = typer.Typer(help="Run management commands")
console = Console()


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
        help="Workspace name (auto-detected from context if in terraform directory)",
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of runs to display"),
    status: str | None = typer.Option(
        None, "--status", "-s", help="Filter by run status (e.g., applied, errored)"
    ),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
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
    run_id: str = typer.Argument(..., help="Run ID to display"),
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace name (used for display context only)",
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
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


def _stream_run_logs(client: TFCClient, run_id: str) -> Run:
    """Stream plan and apply logs for a run until completion."""
    import time

    last_plan_pos = 0
    last_apply_pos = 0

    console.print(f"\n[bold blue]Streaming logs for run {run_id}...[/bold blue]")

    while True:
        run = client.runs.get(run_id)

        # Show status if no logs are available yet
        if not run.plan_id and not run.apply_id:
            console.print(f"  {run.status.emoji} {run.status.value}...", end="\r", style="dim")

        # Stream plan logs
        if run.plan_id:
            try:
                logs = client.runs.get_plan_logs(run.plan_id)
                new_content = logs[last_plan_pos:]
                if new_content:
                    print(new_content, end="", flush=True)
                    last_plan_pos = len(logs)
            except Exception:
                pass

        # Stream apply logs if applicable
        if run.apply_id:
            try:
                logs = client.runs.get_apply_logs(run.apply_id)
                new_content = logs[last_apply_pos:]
                if new_content:
                    print(new_content, end="", flush=True)
                    last_apply_pos = len(logs)
            except Exception:
                pass

        if run.status.is_terminal:
            # Final log fetch to ensure we didn't miss the tail
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

            return run

        time.sleep(2)


@app.command("plan")
@handle_cli_errors
def run_plan(
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace name (auto-detected from context if in terraform directory)",
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    message: str | None = typer.Option(None, "--message", "-m", help="Run description/message"),
    watch: bool = typer.Option(True, "--watch/--no-watch", help="Watch progress until complete"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream logs during watch"),
):
    """Create a new plan (run) for a workspace.

    Auto-detects workspace and organization from .terraform/terraform.tfstate or terraform.tf if not specified.

    Examples:
        # Create plan for current workspace
        terrapyne run plan

        # Create plan with message
        terrapyne run plan --message "Testing new config"

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
        run = client.runs.create(workspace_id=ws.id, message=message, auto_apply=False)

        console.print(f"[green]✓[/green] Created run: {run.id}")
        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not watch:
            console.print(
                f"\n[dim]View run at:[/dim] https://app.terraform.io/app/{org}/workspaces/{workspace_name}/runs/{run.id}"
            )
            return

        # Watch
        if stream:
            final_run = _stream_run_logs(client, run.id)
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
    run_id: str = typer.Argument(..., help="Run ID"),
    log_type: str = typer.Option("plan", "--type", "-t", help="Log type: plan or apply"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
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
    run_id: str | None = typer.Argument(None, help="Run ID to apply (creates new plan if omitted)"),
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace name (used when creating new plan)",
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    message: str | None = typer.Option(None, "--message", "-m", help="Apply comment/reason"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip confirmation prompt (for CI/CD)"
    ),
    watch: bool = typer.Option(True, "--watch/--no-watch", help="Watch progress until complete"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream logs during watch"),
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
            final_run = _stream_run_logs(client, run_id)
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
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="Filter by project name")
    ] = None,
    days: Annotated[int, typer.Option("--days", "-d", help="Look back period in days")] = 1,
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Maximum number of errors to show")
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
    watch: bool = typer.Option(True, "--watch/--no-watch", help="Watch progress until complete"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream logs during watch"),
):
    """Trigger a new run with optional targeting or replacement.

    Examples:
        # Trigger normal plan
        terrapyne run trigger my-app-dev

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

        console.print(f"[dim]Triggering run for workspace:[/dim] {workspace_name}")
        if target:
            console.print(f"[dim]Targets:[/dim] {', '.join(target)}")
        if replace:
            console.print(f"[dim]Replacements:[/dim] {', '.join(replace)}")

        # Create run
        run = client.runs.create(
            workspace_id=ws.id,
            message=message,
            auto_apply=auto_approve
            if destroy
            else False,  # Destroy usually needs auto-apply if confirmed
            is_destroy=destroy,
            target_addrs=target,
            replace_addrs=replace,
            refresh_only=refresh_only,
        )

        console.print(f"[green]✓[/green] Created run: {run.id}")
        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not watch:
            console.print(
                f"\n[dim]View run at:[/dim] https://app.terraform.io/app/{org}/workspaces/{workspace_name}/runs/{run.id}"
            )
            return

        # Watch
        if stream:
            final_run = _stream_run_logs(client, run.id)
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
    run_id: Annotated[str, typer.Argument(help="Run ID to watch")],
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace name (for deep links)",
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
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream logs"),
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
            final_run = _stream_run_logs(client, run_id)
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
