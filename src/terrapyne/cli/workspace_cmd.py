"""Workspace CLI commands."""

from typing import Annotated, cast

import typer

from terrapyne.cli.utils import (
    console,
    emit_json,
    get_client,
    handle_cli_errors,
    resolve_organization,
    validate_context,
)
from terrapyne.core.browser import get_workspace_url, open_url_in_browser
from terrapyne.core.exceptions import TFCAPIError
from terrapyne.models.run import RunStatus
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.rendering.rich_tables import (
    render_workspace_dashboard,
    render_workspace_variables,
    render_workspace_vcs,
    render_workspaces,
)

app = typer.Typer(help="Workspace management commands")


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def workspace_list(
    ctx: typer.Context,
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    search: str | None = typer.Option(
        None, "--search", "-s", help="Search pattern for workspace names"
    ),
    wildcard: bool = typer.Option(
        False, "--wildcard", help="Treat search pattern as a wildcard pattern"
    ),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
):
    """List workspaces in an organization."""
    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified and not found in context.[/red]")
        raise typer.Exit(1)

    with get_client(ctx, organization=org) as client:
        # Use wildcard search if requested
        search_pattern = f"*{search}*" if search and wildcard else search

        workspaces_iter, total_count = client.workspaces.list(org, search=search_pattern)
        workspaces = list(workspaces_iter)

        if output_format == "json":
            emit_json([ws.model_dump() for ws in workspaces])
            return

        render_workspaces(workspaces, f"Workspaces in {org}", total_count=total_count)

        if not search and total_count and total_count > 10:
            console.print(
                "\n[dim]Tip: Use --search to narrow results (e.g. --search 'prod-*')[/dim]"
            )


@app.command("show")
@handle_cli_errors
def workspace_show(
    ctx: typer.Context,
    workspace: str | None = typer.Argument(
        None, help="Workspace name (auto-detected from terraform.tf if in terraform directory)"
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    json_output: bool = typer.Option(
        False, "--json", help="Output in JSON format (alias for -f json)"
    ),
):
    """Show detailed workspace information.

    Auto-detects workspace and organization from .terraform/terraform.tfstate or terraform.tf if not specified.

    Examples:
        # Show current workspace (from terraform.tf)
        terrapyne workspace show

        # Show specific workspace
        terrapyne workspace show my-app-dev

        # Show workspace in specific organization
        terrapyne workspace show my-app-dev --organization my-org
    """
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    if json_output:
        output_format = "json"

    with get_client(ctx, organization=org) as client:
        # Optimized: Fetch workspace, project, and latest run (with commit info) in ONE call (Task 21)
        ws = client.workspaces.get(
            cast(str, ws_name), org, include="project,latest-run,latest-run.configuration-version"
        )

        # 1. Fetch active run count (optimized: use a single count-only call)
        latest_run = ws.latest_run
        active_runs_count = 0
        try:
            active_list = RunStatus.get_active_statuses()
            active_statuses = ",".join(active_list)

            # Efficiently get total count of active runs
            _, total_active = client.runs.list(ws.id, status=active_statuses, limit=1)
            active_runs_count = total_active or 0
        except TFCAPIError as e:
            console.print(
                f"\n[yellow]Warning:[/yellow] Unable to fetch run activity "
                f"(API error {e.status_code})"
            )

        # 2. Fetch VCS and variables (common for both formats)
        vcs = None
        variables = None

        try:
            vcs = client.vcs.get_workspace_vcs(ws.id)
        except TFCAPIError:
            pass

        try:
            variables = client.workspaces.get_variables(ws.id)
        except TFCAPIError:
            pass

        if output_format == "json":
            # Build variable summary
            variable_summary = None
            if variables:
                variable_summary = {
                    "total": len(variables),
                    "terraform": sum(1 for v in variables if v.category == "terraform"),
                    "env": sum(1 for v in variables if v.category == "env"),
                    "sensitive": sum(1 for v in variables if v.sensitive),
                }

            emit_json(
                {
                    "id": ws.id,
                    "name": ws.name,
                    "terraform_version": ws.terraform_version,
                    "execution_mode": ws.execution_mode,
                    "locked": ws.locked,
                    "auto_apply": ws.auto_apply,
                    "created_at": ws.created_at,
                    "updated_at": ws.updated_at,
                    "project_id": ws.project_id,
                    "project_name": ws.project_name,
                    "environment": ws.environment,
                    "working_directory": ws.working_directory,
                    "tag_names": ws.tag_names,
                    "vcs": {
                        "identifier": vcs.identifier,
                        "branch": vcs.branch,
                        "working_directory": vcs.working_directory,
                        "repository_url": vcs.repository_http_url,
                    }
                    if vcs
                    else None,
                    "variable_summary": variable_summary,
                    "snapshot": {
                        "latest_run": (
                            {
                                "id": latest_run.id,
                                "status": latest_run.status,
                                "commit_sha": latest_run.commit_sha,
                                "commit_author": latest_run.commit_author,
                                "commit_message": latest_run.commit_message,
                            }
                            if latest_run
                            else None
                        ),
                        "active_runs_count": active_runs_count,
                    },
                }
            )
            return

        # 3. Render dashboard
        render_workspace_dashboard(
            workspace=ws, latest_run=latest_run, active_runs_count=active_runs_count
        )

        # 4. Render variables
        if variables:
            render_workspace_variables(variables)

        # 5. Render VCS configuration
        render_workspace_vcs(ws)


@app.command("vcs")
@handle_cli_errors
def workspace_vcs(
    ctx: typer.Context,
    workspace: str | None = typer.Argument(
        None, help="Workspace name (auto-detected from terraform.tf if in terraform directory)"
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """Show VCS configuration for a workspace."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        render_workspace_vcs(ws)


@app.command("variables")
@handle_cli_errors
def workspace_variables(
    ctx: typer.Context,
    workspace: str | None = typer.Argument(
        None, help="Workspace name (auto-detected from terraform.tf if in terraform directory)"
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """List variables for a workspace."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)

        variables = client.workspaces.get_variables(ws.id)

        if not variables:
            console.print("[yellow]No variables configured in this workspace.[/yellow]")
            return

        render_workspace_variables(variables)


@app.command("var-set")
@handle_cli_errors
def workspace_var_set(
    ctx: typer.Context,
    workspace: Annotated[
        str | None,
        typer.Argument(
            help="Workspace name (auto-detected from terraform.tf if in terraform directory)"
        ),
    ] = None,
    key: Annotated[str | None, typer.Option("--key", "-k", help="Variable key")] = None,
    value: Annotated[str | None, typer.Option("--value", "-v", help="Variable value")] = None,
    category: Annotated[
        str, typer.Option("--category", "-c", help="Category: terraform, env")
    ] = "terraform",
    hcl: Annotated[bool, typer.Option("--hcl", help="Parse value as HCL")] = False,
    sensitive: Annotated[bool, typer.Option("--sensitive", "-s", help="Mark as sensitive")] = False,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Variable description")
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
):
    """Set a workspace variable (create or update)."""
    if key is None or value is None:
        console.print("[red]Error: Both --key and --value are required.[/red]")
        raise typer.Exit(1)

    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)

        # Check if variable already exists
        variables: list[WorkspaceVariable] = client.workspaces.get_variables(ws.id)
        if variables is None:
            variables = []

        existing_var = next((v for v in variables if v.key == key), None)

        if existing_var:
            console.print(f"[dim]Updating existing variable:[/dim] {key}")
            client.workspaces.update_variable(
                variable_id=existing_var.id,
                value=value,
                hcl=hcl,
                sensitive=sensitive,
                description=description,
            )
            console.print(f"[green]✓[/green] Updated variable: {key}")
        else:
            console.print(f"[dim]Creating new variable:[/dim] {key}")
            client.workspaces.create_variable(
                workspace_id=ws.id,
                key=key,
                value=value,
                category=category,
                hcl=hcl,
                sensitive=sensitive,
                description=description,
            )
            console.print(f"[green]✓[/green] Created variable: {key}")


@app.command("var-rm")
@handle_cli_errors
def workspace_var_rm(
    ctx: typer.Context,
    workspace: Annotated[
        str | None,
        typer.Argument(
            help="Workspace name (auto-detected from terraform.tf if in terraform directory)"
        ),
    ] = None,
    key: Annotated[str | None, typer.Argument(help="Variable key to remove")] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
):
    """Remove a workspace variable."""
    if key is None:
        console.print("[red]Error: Variable key is required.[/red]")
        raise typer.Exit(1)

    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)

        # Find variable by key
        variables: list[WorkspaceVariable] = client.workspaces.get_variables(ws.id)
        if variables is None:
            variables = []

        existing_var = next((v for v in variables if v.key == key), None)

        if not existing_var:
            console.print(f"[yellow]Variable '{key}' not found in workspace '{ws_name}'[/yellow]")
            raise typer.Exit(1)

        if not force and not typer.confirm(f"Remove variable '{key}' from workspace '{ws_name}'?"):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

        client.workspaces.delete_variable(workspace_id=ws.id, variable_id=existing_var.id)
        console.print(f"[green]✓[/green] Removed variable: {key}")


@app.command("var-copy")
@handle_cli_errors
def workspace_var_copy(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Source workspace name"),
    target: str = typer.Argument(..., help="Target workspace name"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing variables"),
):
    """Copy all variables from one workspace to another."""
    org, _ = validate_context(organization)

    with get_client(ctx, organization=org) as client:
        ws_source = client.workspaces.get(source, org)
        ws_target = client.workspaces.get(target, org)

        source_variables: list[WorkspaceVariable] = client.workspaces.get_variables(ws_source.id)
        target_variables: list[WorkspaceVariable] = client.workspaces.get_variables(ws_target.id)

        if source_variables is None:
            source_variables = []
        if target_variables is None:
            target_variables = []

        target_keys = {v.key for v in target_variables}

        console.print(f"[dim]Copying {len(source_variables)} variables: {source} → {target}[/dim]")

        copied = 0
        skipped = 0
        updated = 0

        for var in source_variables:
            if var.key in target_keys:
                if overwrite:
                    # Find target var ID
                    t_v = next(v for v in target_variables if v.key == var.key)
                    client.workspaces.update_variable(
                        variable_id=t_v.id,
                        value=var.value,
                        hcl=var.hcl,
                        sensitive=var.sensitive,
                        description=var.description,
                    )
                    updated += 1
                else:
                    skipped += 1
                    continue
            else:
                client.workspaces.create_variable(
                    workspace_id=ws_target.id,
                    key=var.key,
                    value=var.value or "",
                    category=var.category,
                    hcl=var.hcl,
                    sensitive=var.sensitive,
                    description=var.description,
                )
                copied += 1

        console.print(
            f"[green]✓[/green] Done! {copied} created, {updated} updated, {skipped} skipped."
        )


@app.command("open")
@handle_cli_errors
def workspace_open(
    ctx: typer.Context,
    workspace: str | None = typer.Argument(
        None, help="Workspace name (auto-detected from terraform.tf if in terraform directory)"
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """Open workspace in the default web browser."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    url = get_workspace_url(org, cast(str, ws_name))
    console.print(f"[dim]Opening:[/dim] {url}")
    open_url_in_browser(url)


@app.command("clone")
@handle_cli_errors
def workspace_clone(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Source workspace name"),
    target: str = typer.Argument(..., help="Target workspace name"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    with_variables: bool = typer.Option(True, help="Copy variables to the new workspace"),
    with_vcs: bool = typer.Option(True, help="Copy VCS configuration to the new workspace"),
    vcs_token: str | None = typer.Option(
        None, "--vcs-token", help="VCS OAuth token ID (required for cross-org clone)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force clone even if target workspace exists"
    ),
):
    """Clone a workspace (configuration and variables).

    Examples:
        # Clone workspace in same organization
        terrapyne workspace clone my-app-prod my-app-staging

        # Clone and overwrite existing target
        terrapyne workspace clone source target --force

        # Clone without variables
        terrapyne workspace clone source target --no-variables
    """
    org, _ = validate_context(organization)

    console.print(f"\n[dim]Cloning workspace:[/dim] {source} → {target}")

    with get_client(ctx, organization=org) as client:
        from terrapyne.api.workspace_clone import (
            CloneWorkspaceAPI,
            WorkspaceAlreadyExistsError,
            WorkspaceNotFoundError,
        )

        clone_api = CloneWorkspaceAPI(client)
        try:
            result = clone_api.clone(
                source_workspace_name=source,
                target_workspace_name=target,
                organization=org,
                with_variables=with_variables,
                with_vcs=with_vcs,
                vcs_oauth_token_id=vcs_token,
                force=force,
            )

            console.print(f"\n[green]✓[/green] {result.get('message', 'Successfully cloned')}")

            if result.get("status") == "error":
                console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")
                raise typer.Exit(1)

            # Show details of what was cloned
            res = result.get("results", {})
            if res.get("variables"):
                vars_info = res["variables"]
                count = vars_info.get("variables_cloned", 0)
                breakdown = []
                if vars_info.get("terraform_variables"):
                    breakdown.append(f"{vars_info['terraform_variables']} terraform")
                if vars_info.get("env_variables"):
                    breakdown.append(f"{vars_info['env_variables']} env")

                breakdown_str = f" ({', '.join(breakdown)})" if breakdown else ""
                console.print(f"[dim]Variables cloned:[/dim] {count}{breakdown_str}")

            if res.get("vcs"):
                vcs_info = res["vcs"]
                console.print(
                    f"[dim]VCS configuration:[/dim] {vcs_info.get('identifier')} (branch: {vcs_info.get('branch')})"
                )

            # Open in browser if successful
            url = get_workspace_url(org, target)
            console.print(f"[dim]View new workspace:[/dim] {url}")
        except WorkspaceAlreadyExistsError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
        except WorkspaceNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None


@app.command("costs")
@handle_cli_errors
def workspace_costs(
    ctx: typer.Context,
    workspace: str | None = typer.Argument(
        None, help="Workspace name (auto-detected from terraform.tf if in terraform directory)"
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """Show cost estimates for the latest plan."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        cost_estimate = client.runs.get_latest_cost_estimate(ws.id)
        if not cost_estimate:
            console.print(
                "[yellow]No finished cost estimates available for the latest run.[/yellow]"
            )
            return

        # Handle different key names from API vs what might be expected
        proposed = cost_estimate.get("proposed-monthly-cost") or cost_estimate.get("monthly", "0.0")
        delta = cost_estimate.get("delta-monthly-cost") or cost_estimate.get("delta", "0.0")

        try:
            monthly_val = float(proposed)
            delta_raw = float(delta)
        except ValueError:
            monthly_val = 0.0
            delta_raw = 0.0

        # Add + sign if positive
        if delta_raw > 0:
            delta_prefix = "+$"
            delta_val = delta_raw
        elif delta_raw < 0:
            delta_prefix = "-$"
            delta_val = abs(delta_raw)
        else:
            delta_prefix = "$"
            delta_val = 0.0

        console.print(f"Estimated monthly cost: ${monthly_val:,.2f}")
        console.print(f"Cost delta: {delta_prefix}{delta_val:,.2f}")
