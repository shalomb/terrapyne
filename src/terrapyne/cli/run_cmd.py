"""Run CLI commands."""

from __future__ import annotations

import datetime
import sys
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any

import typer

from terrapyne.cli.utils import (
    console,
    emit_json,
    get_client,
    handle_cli_errors,
    resolve_project_context,
    validate_context,
)
from terrapyne.models.run import Run
from terrapyne.rendering.rich_tables import render_run_detail, render_runs

app = typer.Typer(help="Run management commands")


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def run_list(
    ctx: typer.Context,
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

    with get_client(ctx, organization=org) as client:
        # Get workspace to retrieve workspace ID
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        # Fetch runs
        runs, total = client.runs.list(workspace_id=ws.id, limit=limit, status=status)

        if not runs:
            status_msg = f" with status '{status}'" if status else ""
            console.print(
                f"[yellow]No runs found for workspace '{workspace_name}'{status_msg}.[/yellow]"
            )
            return

        if output_format == "json":
            emit_json([run.model_dump() for run in runs])
            return

        render_runs(runs, f"Runs in {workspace_name}", total_count=total)


@app.command("show")
@handle_cli_errors
def run_show(
    ctx: typer.Context,
    run_id: Annotated[str, typer.Argument(help="Run ID (e.g., run-xxx)")],
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
    """Show details for a specific run."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        # Fetch run details
        run = client.runs.get(run_id)

        # Try to fetch plan details if available
        plan = None
        if run.plan_id:
            with suppress(Exception):
                plan = client.runs.get_plan(run.plan_id)

        if output_format == "json":
            data = run.model_dump()
            if plan:
                data["plan"] = plan.model_dump()
            emit_json(data)
            return

        render_run_detail(run, plan=plan)


@app.command("plan")
@handle_cli_errors
def run_plan(
    ctx: typer.Context,
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
    message: Annotated[
        str | None,
        typer.Option("--message", "-m", help="Reason for the plan"),
    ] = None,
    wait: Annotated[
        bool,
        typer.Option(
            "--wait/--no-wait",
            help="Wait for the plan to complete",
        ),
    ] = True,
    refresh_only: Annotated[
        bool,
        typer.Option("--refresh-only", help="Trigger a refresh-only plan"),
    ] = False,
):
    """Trigger a new plan (speculative run)."""
    # Resolve organization and workspace
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        # Get workspace ID
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        console.print(f"[dim]Triggering plan for workspace:[/dim] {workspace_name}")

        # Create run
        run = client.runs.create(
            workspace_id=ws.id,
            message=message or f"Plan triggered via terrapyne at {datetime.datetime.now()}",
            is_destroy=False,
            auto_apply=False,
            refresh_only=refresh_only,
        )

        console.print(f"[green]✓[/green] Created run: {run.id}")
        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not wait:
            console.print(
                f"\n[dim]View run at:[/dim] https://app.terraform.io/app/{org}/workspaces/{workspace_name}/runs/{run.id}"
            )
            return

        # Wait for completion
        console.print("\nWatching run progress...")
        try:
            final_run = client.runs.poll_until_complete(run.id)
            print()  # New line after progress

            # Fetch final plan details
            plan = None
            if final_run.plan_id:
                with suppress(Exception):
                    plan = client.runs.get_plan(final_run.plan_id)

            render_run_detail(final_run, plan=plan)

            if not final_run.status.is_successful:
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


@app.command("logs")
@handle_cli_errors
def run_logs(
    ctx: typer.Context,
    run_id: Annotated[str, typer.Argument(help="Run ID")],
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    stage: Annotated[
        str,
        typer.Option("--stage", help="Logs to show: plan, apply"),
    ] = "plan",
):
    """Show logs for a specific run stage."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        run = client.runs.get(run_id)

        if stage == "plan":
            if not run.plan_id:
                console.print("[yellow]No plan logs available for this run.[/yellow]")
                return
            logs = client.runs.get_plan_logs(run.plan_id)
        elif stage == "apply":
            if not run.apply_id:
                console.print("[yellow]No apply logs available for this run.[/yellow]")
                return
            logs = client.runs.get_apply_logs(run.apply_id)
        else:
            console.print(f"[red]Error: Invalid stage '{stage}'. Use 'plan' or 'apply'.[/red]")
            raise typer.Exit(1)

        if not logs:
            console.print(f"[yellow]Logs for {stage} stage are empty or not yet ready.[/yellow]")
            return

        console.print(logs)


@app.command("apply")
@handle_cli_errors
def run_apply(
    ctx: typer.Context,
    run_id: Annotated[
        str | None,
        typer.Argument(help="Run ID (or omit to trigger new auto-apply run)"),
    ] = None,
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace name (if triggering new run)",
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
    comment: Annotated[
        str | None,
        typer.Option("--comment", "-m", help="Apply comment"),
    ] = None,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Wait for completion"),
    ] = True,
):
    """Apply a plan or trigger a new auto-apply run."""
    org, ws_context_name = validate_context(organization, workspace)

    with get_client(ctx, organization=org) as client:
        # If no run_id provided, create a new run with auto-apply
        if not run_id:
            if not ws_context_name:
                console.print("[red]Error: Provide a run ID or specify a workspace.[/red]")
                raise typer.Exit(1)

            ws = client.workspaces.get(ws_context_name, organization=org)
            console.print(f"[dim]Triggering auto-apply run for:[/dim] {ws_context_name}")
            run = client.runs.create(
                workspace_id=ws.id,
                message=comment or "Apply triggered via terrapyne",
                auto_apply=True,
            )
            run_id = run.id
        else:
            # Apply existing run
            console.print(f"[dim]Applying run:[/dim] {run_id}")
            run = client.runs.apply(run_id, comment=comment)

        console.print(f"[green]✓[/green] Applied run: {run.id}")

        if not wait:
            return

        console.print("\nWatching apply progress...")
        try:
            final_run = client.runs.poll_until_complete(run_id)
            print()

            if final_run.status.is_successful:
                console.print("[green]✓[/green] Run completed successfully")
            else:
                console.print(f"[red]✗[/red] Run failed with status: {final_run.status.value}")
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


@app.command("errors")
@handle_cli_errors
def run_errors(
    ctx: typer.Context,
    project_name: Annotated[
        str | None,
        typer.Argument(help="Project name (auto-detected from context if available)"),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Look back N days"),
    ] = 7,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Max errors to show per workspace"),
    ] = 3,
):
    """Identify recent execution errors across a project."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        # Resolve project
        org, project = resolve_project_context(client, org, project_name)

        console.print(f"[dim]Searching for recent errors in project:[/dim] {project.name}")

        # Get workspaces
        workspaces_iter, _ = client.workspaces.list(org, project_id=project.id)
        workspaces = list(workspaces_iter)

        since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)
        error_found = False

        for ws in workspaces:
            # Fetch errored runs
            runs, _ = client.runs.list(ws.id, status="errored", limit=limit)

            # Filter by date
            recent_errors = [r for r in runs if r.created_at and r.created_at > since]

            if recent_errors:
                error_found = True
                console.print(f"\n[bold red]✗ Workspace: {ws.name}[/bold red]")
                for run in recent_errors:
                    date_str = (
                        run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else "Unknown"
                    )
                    console.print(
                        f"  • [cyan]{run.id}[/cyan] ({date_str}): {run.message or 'No message'}"
                    )

        if not error_found:
            console.print(
                f"[green]✓ No recent errors found in project '{project.name}' over the last {days} days.[/green]"
            )


@app.command("trigger")
@handle_cli_errors
def run_trigger(
    ctx: typer.Context,
    workspace: Annotated[
        str | None,
        typer.Argument(help="Workspace name (auto-detected if omitted)"),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization",
        ),
    ] = None,
    message: Annotated[
        str | None,
        typer.Option("--message", "-m", help="Reason for the run"),
    ] = None,
    auto_apply: Annotated[
        bool,
        typer.Option("--auto-apply", help="Automatically apply if plan succeeds"),
    ] = False,
    destroy: Annotated[
        bool,
        typer.Option("--destroy", help="Trigger a destruction run"),
    ] = False,
    refresh_only: Annotated[
        bool,
        typer.Option("--refresh-only", help="Trigger a refresh-only run"),
    ] = False,
    target: Annotated[
        list[str] | None,
        typer.Option("--target", help="Resource address to target"),
    ] = None,
    replace: Annotated[
        list[str] | None,
        typer.Option("--replace", help="Resource address to replace"),
    ] = None,
    wait: Annotated[
        bool,
        typer.Option("--wait/--no-wait", help="Wait for completion"),
    ] = True,
    wait_queue: Annotated[
        bool,
        typer.Option("--wait-queue", help="If another run is active, wait for it to finish"),
    ] = False,
    discard_older: Annotated[
        bool,
        typer.Option("--discard-older", help="Discard any active runs before triggering"),
    ] = False,
    auto_approve: Annotated[
        bool,
        typer.Option("--auto-approve", help="Skip confirmation for destructive runs"),
    ] = False,
    max_wait: Annotated[
        int,
        typer.Option("--max-wait", help="Max seconds to wait for queue/completion"),
    ] = 1800,
    debug_run: Annotated[
        bool,
        typer.Option("--debug-run", help="Enable TFC debugging mode for this run"),
    ] = False,
):
    """Trigger a new run with advanced queue management."""
    # Resolve organization and workspace
    org, workspace_name = validate_context(organization, workspace, require_workspace=True)

    if destroy and not auto_approve:
        if not typer.confirm(
            f"[bold red]WARNING:[/bold red] You are triggering a DESTROY run for '{workspace_name}'. Proceed?",
            default=False,
        ):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    with get_client(ctx, organization=org) as client:
        # Get workspace ID
        ws = client.workspaces.get(workspace_name or "", organization=org)  # type: ignore[arg-type]

        # 1. Handle existing runs
        active_runs = client.runs.get_active_runs(ws.id)
        if active_runs:
            if discard_older:
                console.print(f"[dim]Discarding {len(active_runs)} active run(s)...[/dim]")
                for r in active_runs:
                    with suppress(Exception):
                        client.runs.discard(r.id, comment="Discarded by terrapyne --discard-older")
            elif wait_queue:
                current_run = active_runs[0]
                console.print(
                    f"[dim]Waiting for current run {current_run.id} "
                    f"({current_run.status.value}) to finish...[/dim]"
                )
                try:
                    client.runs.poll_until_complete(current_run.id, max_wait=float(max_wait))
                except TimeoutError as e:
                    console.print(f"\n[red]Error:[/red] Timed out waiting for queue: {e}")
                    raise typer.Exit(1) from None

        # Identify run type
        run_type = "PLAN"
        if destroy:
            run_type = "DESTROY"
        elif refresh_only:
            run_type = "REFRESH"

        if target:
            run_type = f"TARGETED {run_type}"
        if replace:
            run_type = f"REPLACE {run_type}"

        console.print(
            f"[dim]Triggering [bold cyan]{run_type}[/bold cyan] run for workspace:[/dim] "
            f"{workspace_name}"
        )

        # 2. Create run
        run = client.runs.create(
            workspace_id=ws.id,
            message=message or f"{run_type} triggered via terrapyne",
            is_destroy=destroy,
            auto_apply=auto_apply,
            target_addrs=target,
            replace_addrs=replace,
            refresh_only=refresh_only,
            debug=debug_run,
        )

        console.print(f"[green]✓[/green] Created {run_type} run: {run.id}")
        if message:
            console.print(f"[dim]Message:[/dim] {message}")
        console.print(f"[dim]Status:[/dim] {run.status.emoji} {run.status.value}")

        if not wait:
            console.print(
                f"\n[dim]View run at:[/dim] https://app.terraform.io/app/{org}/workspaces/{workspace_name}/runs/{run.id}"
            )
            return

        # 3. Wait for completion
        console.print("\nWatching run progress...")
        try:
            final_run = client.runs.poll_until_complete(run.id, max_wait=float(max_wait))
            print()

            plan = None
            if final_run.plan_id:
                with suppress(Exception):
                    plan = client.runs.get_plan(final_run.plan_id)

            render_run_detail(final_run, workspace_name=workspace_name, organization=org, plan=plan)

            if final_run.status.is_awaiting_approval:
                console.print("\n[yellow]⏸ Run paused for manual approval.[/yellow]")
                raise typer.Exit(0)

            if not final_run.status.is_successful:
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


@app.command("watch")
@handle_cli_errors
def run_watch(
    ctx: typer.Context,
    run_id: Annotated[str, typer.Argument(help="Run ID")],
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    max_wait: Annotated[
        int,
        typer.Option("--max-wait", help="Max seconds to wait"),
    ] = 1800,
):
    """Watch progress of an existing run."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        console.print(f"[dim]Watching run:[/dim] {run_id}")
        try:
            final_run = client.runs.poll_until_complete(run_id, max_wait=float(max_wait))
            print()

            plan = None
            if final_run.plan_id:
                with suppress(Exception):
                    plan = client.runs.get_plan(final_run.plan_id)

            render_run_detail(final_run, plan=plan)

            if not final_run.status.is_successful:
                raise typer.Exit(1)

        except TimeoutError as e:
            console.print(f"\n[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1) from None


@app.command("follow")
@handle_cli_errors
def run_follow(
    ctx: typer.Context,
    run_id: Annotated[str, typer.Argument(help="Run ID")],
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    max_wait: Annotated[
        int,
        typer.Option("--max-wait", help="Max seconds to wait"),
    ] = 1800,
):
    """Stream logs of an existing run in real-time."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        console.print(f"\n[dim]Following run {run_id}...[/dim]\n")

        last_plan_pos = 0
        last_apply_pos = 0
        current_stage = None

        def stream_logs(run: Run) -> None:
            nonlocal last_plan_pos, last_apply_pos, current_stage

            # 1. Plan Stage
            if run.plan_id:
                if current_stage is None:
                    current_stage = "plan"
                    console.print("[dim]📋 Plan:[/dim]")
                try:
                    plan_log = client.runs.get_plan_logs(run.plan_id)
                    last_plan_pos = _print_log_delta(plan_log, last_plan_pos)
                except Exception:
                    pass

            # 2. Apply Stage
            if run.apply_id and run.status.value in ["applying", "applied"]:
                if current_stage != "apply":
                    current_stage = "apply"
                    console.print("\n[dim]⚙️  Apply:[/dim]")
                try:
                    apply_log = client.runs.get_apply_logs(run.apply_id)
                    last_apply_pos = _print_log_delta(apply_log, last_apply_pos)
                except Exception:
                    pass

            # Feedback if run fails before generating logs
            if run.status.is_error and last_plan_pos == 0 and last_apply_pos == 0:
                if current_stage != "error":
                    current_stage = "error"
                    console.print(
                        f"\n[red]Run failed before generating logs: {run.status.value}[/red]"
                    )

        try:
            final_run = client.runs.poll_until_complete(
                run_id, callback=stream_logs, max_wait=float(max_wait)
            )

            # Print final newline and status
            print()
            if final_run.status.is_successful:
                console.print(f"[green]✓[/green] Run {run_id} completed successfully")
            else:
                console.print(
                    f"[red]✗[/red] Run {run_id} failed with status: {final_run.status.value}"
                )
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
    if len(full_log) < last_pos:
        # Logs were truncated or rotated; reset position
        last_pos = 0

    new_content = full_log[last_pos:]
    if new_content:
        # Use rich console to automatically handle or strip ANSI escape codes
        # depending on terminal capabilities
        console.print(new_content, end="", markup=False)
    return len(full_log)


@app.command("discard")
@handle_cli_errors
def run_discard(
    ctx: typer.Context,
    run_id: Annotated[str, typer.Argument(help="Run ID")],
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    comment: Annotated[
        str | None,
        typer.Option("--comment", "-m", help="Reason for discarding"),
    ] = None,
):
    """Discard a run that is not yet applied."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        console.print(f"[dim]Discarding run:[/dim] {run_id}")
        run = client.runs.discard(run_id, comment=comment)
        console.print(f"[green]✓[/green] Run {run_id} discarded (Status: {run.status.value})")


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
    from terrapyne.core.local_binary import Terraform

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
