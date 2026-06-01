"""Run CLI commands."""

from __future__ import annotations

import datetime
import sys
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any

import typer

from terrapyne.api.org_errors import get_errored_workspaces
from terrapyne.cli.context_helpers import get_client, resolve_project_context, validate_context
from terrapyne.cli.error_handlers import handle_cli_errors
from terrapyne.cli.output_helpers import effective_format, emit_json
from terrapyne.core.exceptions import TFCConflictError
from terrapyne.models.run import Run
from terrapyne.rendering.logging import console, error_console
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
    workspace_arg: Annotated[
        str | None,
        typer.Argument(help="Workspace name (positional shorthand)"),
    ] = None,
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
    # Resolve organization and workspace (positional arg takes precedence over --workspace option)
    org, workspace_name = validate_context(
        organization, workspace_arg or workspace, require_workspace=True
    )

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

        if effective_format(ctx, output_format) == "json":
            emit_json([run.model_dump() for run in runs])
            return

        render_runs(runs, f"Runs in {workspace_name}", total_count=total)


@app.command("show")
@handle_cli_errors
def run_show(
    ctx: typer.Context,
    run_id: Annotated[str | None, typer.Argument(help="Run ID (e.g., run-xxx)")] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    workspace: Annotated[
        str | None,
        typer.Option("--workspace", "-w", help="Workspace name (required with --latest)"),
    ] = None,
    latest: Annotated[
        bool,
        typer.Option("--latest", help="Show the most recent run for --workspace"),
    ] = False,
    output_format: Annotated[
        str, typer.Option("--format", "-f", help="Output format (table, json)")
    ] = "table",
):
    """Show details for a specific run."""
    org, ws_name = validate_context(organization, workspace)

    with get_client(ctx, organization=org) as client:
        if latest:
            if not ws_name:
                console.print("[red]Error: --latest requires --workspace[/red]")
                raise typer.Exit(1)
            ws = client.workspaces.get(ws_name, org)
            runs, _ = client.runs.list(workspace_id=ws.id, limit=1)
            run = next(iter(runs), None)
            if not run:
                console.print("[yellow]No runs found for workspace.[/yellow]")
                raise typer.Exit(0)
            run_id = run.id
        elif not run_id:
            console.print("[red]Error: Provide a run ID or use --workspace with --latest[/red]")
            raise typer.Exit(1)

        # Fetch run details
        run = client.runs.get(run_id)

        # Try to fetch plan details if available
        plan = None
        if run.plan_id:
            with suppress(Exception):
                plan = client.runs.get_plan(run.plan_id)

        if effective_format(ctx, output_format) == "json":
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
    """Trigger a new queued plan (confirmable; use 'run trigger --speculative' for a true read-only speculative plan)."""
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
    run_id: Annotated[str | None, typer.Argument(help="Run ID")] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    workspace: Annotated[
        str | None,
        typer.Option("--workspace", "-w", help="Workspace name (required with --latest)"),
    ] = None,
    latest: Annotated[
        bool,
        typer.Option("--latest", help="Show logs for the most recent run of --workspace"),
    ] = False,
    stage: Annotated[
        str,
        typer.Option("--stage", help="Logs to show: plan, apply"),
    ] = "plan",
):
    """Show logs for a specific run stage."""
    org, ws_name = validate_context(organization, workspace)

    with get_client(ctx, organization=org) as client:
        if latest:
            if not ws_name:
                console.print("[red]Error: --latest requires --workspace[/red]")
                raise typer.Exit(1)
            ws = client.workspaces.get(ws_name, org)
            runs, _ = client.runs.list(workspace_id=ws.id, limit=1)
            run = next(iter(runs), None)
            if not run:
                console.print("[yellow]No runs found for workspace.[/yellow]")
                raise typer.Exit(0)
            run_id = run.id
        elif not run_id:
            console.print("[red]Error: Provide a run ID or use --workspace with --latest[/red]")
            raise typer.Exit(1)

        run = client.runs.get(run_id)

        if stage == "plan":
            if not run.plan_id:
                console.print("[yellow]No plan logs available for this run.[/yellow]")
                return
            plan = None
            with suppress(Exception):
                plan = client.runs.get_plan(run.plan_id)
            logs = client.runs.get_plan_logs(
                run.plan_id, log_read_url=plan.log_read_url if plan else None
            )
        elif stage == "apply":
            if not run.apply_id:
                console.print("[yellow]No apply logs available for this run.[/yellow]")
                return
            apply_obj = None
            with suppress(Exception):
                apply_obj = client.runs.get_apply(run.apply_id)
            logs = client.runs.get_apply_logs(
                run.apply_id, log_read_url=apply_obj.log_read_url if apply_obj else None
            )
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
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON array (one entry per workspace with errors)"),
    ] = False,
):
    """Identify recent execution errors across a project or the entire organisation.

    When PROJECT_NAME is omitted, scans the entire organisation using a single
    API call (filter[current-run][status]=errored) — much faster than iterating
    every project and workspace individually.
    """
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        project_id: str | None = None
        scope_label: str

        if project_name:
            # Scoped to a single project (existing behaviour).
            _, project = resolve_project_context(client, org, project_name)
            project_id = project.id
            scope_label = f"project '{project.name}'"
        else:
            # Try to infer project from workspace context; fall back to org-wide.
            try:
                _, project = resolve_project_context(client, org, None)
                project_id = project.id
                scope_label = f"project '{project.name}' (from workspace context)"
            except ValueError:
                scope_label = f"organisation '{org}' (all projects)"

        if not json_output:
            console.print(f"[dim]Scanning for errored workspaces in {scope_label}[/dim]")

        errored = get_errored_workspaces(client, days=days, project_id=project_id, organization=org)

        if json_output:
            results: list[dict[str, Any]] = []
            for ws in errored:
                run = ws.latest_run
                results.append(
                    {
                        "workspace": ws.name,
                        "run_id": run.id if run else None,
                        "created_at": run.created_at.isoformat()
                        if run and run.created_at
                        else None,
                        "error": client.runs.get_error_summary(run) if run else None,
                    }
                )
            emit_json(results)
            return

        if not errored:
            console.print(
                f"[green]✓ No errored workspaces found in {scope_label} over the last {days} days.[/green]"
            )
            return

        for ws in errored:
            console.print(f"\n[bold red]✗ {ws.name}[/bold red]", end="")
            if ws.project_name:
                console.print(f" [dim]({ws.project_name})[/dim]", end="")
            console.print()
            if ws.latest_run:
                run = ws.latest_run
                date_str = (
                    run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else "Unknown"
                )
                error_text = client.runs.get_error_summary(run)
                console.print(f"  • [cyan]{run.id}[/cyan] ({date_str}): {error_text}")


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
        typer.Option("--wait/--no-wait", help="Wait for completion (default: no-wait)"),
    ] = False,
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
    speculative: Annotated[
        bool,
        typer.Option(
            "--speculative",
            help=(
                "Create a true speculative plan (read-only, cannot be applied). "
                "Uses the configuration-version API with speculative=true. "
                "Omit this flag for a confirmable queued plan."
            ),
        ),
    ] = False,
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table, json"),
    ] = "table",
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
        if speculative:
            run_type = "SPECULATIVE"
        elif destroy:
            run_type = "DESTROY"
        elif refresh_only:
            run_type = "REFRESH"

        if not speculative and target:
            run_type = f"TARGETED {run_type}"
        if not speculative and replace:
            run_type = f"REPLACE {run_type}"

        if output_format != "json":
            console.print(
                f"[dim]Triggering [bold cyan]{run_type}[/bold cyan] run for workspace:[/dim] "
                f"{workspace_name}"
            )

        # 2. Create run
        if speculative:
            run = client.runs.create_speculative(
                workspace_id=ws.id,
                message=message or f"{run_type} triggered via terrapyne",
            )
        else:
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

        if output_format == "json":
            from terrapyne.cli.output_helpers import emit_json as _emit_json

            _emit_json(run.model_dump())
            if not wait:
                return

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
                error_summary = client.runs.get_error_summary(final_run)
                if error_summary:
                    console.print(f"\n[red]Error details:[/red]\n{error_summary}")
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
    auto_apply: Annotated[
        bool,
        typer.Option(
            "--auto-apply",
            help="Automatically apply when planning/cost-estimation completes",
        ),
    ] = False,
    comment: Annotated[
        str | None,
        typer.Option("--comment", "-m", help="Comment to attach to the apply action"),
    ] = None,
    max_wait: Annotated[
        int,
        typer.Option("--max-wait", help="Max seconds to wait"),
    ] = 1800,
):
    """Watch progress of an existing run (e.g. triggered by a VCS push).

    With --auto-apply, automatically confirms the run once planning or cost
    estimation completes, then waits for the apply to finish.
    """
    import time

    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        console.print(f"[dim]Watching run:[/dim] {run_id}")

        intervals = [2, 2, 3, 5, 5, 10, 10, 15, 30]
        interval_index = 0
        start_time = time.time()
        max_wait_f = float(max_wait)

        try:
            # Phase 1: poll until awaiting approval or terminal
            while True:
                run = client.runs.get(run_id)

                if run.status.is_terminal:
                    break

                if run.status.is_awaiting_approval:
                    if auto_apply:
                        console.print(f"\n[dim]Run reached[/dim] {run.status.value} — applying...")
                        client.runs.apply(run_id, comment=comment)
                    break

                elapsed = time.time() - start_time
                if elapsed >= max_wait_f:
                    raise TimeoutError(
                        f"Run {run_id} did not reach a confirmable state within {max_wait}s "
                        f"(current status: {run.status.value})"
                    )

                wait_time = intervals[interval_index]
                if interval_index < len(intervals) - 1:
                    interval_index += 1
                time.sleep(wait_time)

            # Phase 2: if we applied, wait for the apply to complete
            if auto_apply and run.status.is_awaiting_approval:
                console.print("[dim]Waiting for apply to complete...[/dim]")
                run = client.runs.poll_until_complete(run_id, max_wait=max_wait_f)

            print()

            plan = None
            if run.plan_id:
                with suppress(Exception):
                    plan = client.runs.get_plan(run.plan_id)

            render_run_detail(run, plan=plan)

            if run.status.is_awaiting_approval:
                console.print("\n[yellow]⏸ Run paused — requires manual approval.[/yellow]")
                raise typer.Exit(0)

            if not run.status.is_successful:
                error_summary = client.runs.get_error_summary(run)
                if error_summary:
                    console.print(f"\n[red]Error details:[/red]\n{error_summary}")
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
        plan_url_fetched = False
        plan_log_read_url: str | None = None
        apply_url_fetched = False
        apply_log_read_url: str | None = None

        def stream_logs(run: Run) -> None:
            nonlocal last_plan_pos, last_apply_pos, current_stage
            nonlocal plan_url_fetched, plan_log_read_url
            nonlocal apply_url_fetched, apply_log_read_url

            # 1. Plan Stage
            if run.plan_id:
                if current_stage is None:
                    current_stage = "plan"
                    console.print("[dim]📋 Plan:[/dim]")
                try:
                    if not plan_url_fetched:
                        plan_log_read_url = client.runs.get_plan(run.plan_id).log_read_url
                        plan_url_fetched = True
                    plan_log = client.runs.get_plan_logs(
                        run.plan_id, log_read_url=plan_log_read_url
                    )
                    last_plan_pos = _print_log_delta(plan_log, last_plan_pos)
                except Exception:
                    pass

            # 2. Apply Stage
            if run.apply_id and run.status.value in ["applying", "applied"]:
                if current_stage != "apply":
                    current_stage = "apply"
                    console.print("\n[dim]⚙️  Apply:[/dim]")
                try:
                    if not apply_url_fetched:
                        apply_log_read_url = client.runs.get_apply(run.apply_id).log_read_url
                        apply_url_fetched = True
                    apply_log = client.runs.get_apply_logs(
                        run.apply_id, log_read_url=apply_log_read_url
                    )
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
        try:
            run = client.runs.discard(run_id, comment=comment)
        except TFCConflictError:
            current = client.runs.get(run_id)
            error_console.print(
                f"[red]Error:[/red] Run is in '{current.status.value}' state"
                f" — use `tfc run cancel {run_id}` instead."
            )
            raise typer.Exit(1) from None
        console.print(f"[green]✓[/green] Run {run_id} discarded (Status: {run.status.value})")


@app.command("cancel")
@handle_cli_errors
def run_cancel(
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
        typer.Option("--comment", "-m", help="Reason for cancelling"),
    ] = None,
):
    """Cancel a pending, planning, or applying run."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        console.print(f"[dim]Cancelling run:[/dim] {run_id}")
        run = client.runs.cancel(run_id, comment=comment)
        console.print(f"[green]✓[/green] Run {run_id} cancelled (Status: {run.status.value})")


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
    from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

    result = TerraformPlainTextPlanParser(plan_text).parse()

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
