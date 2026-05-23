"""Workspace CLI commands."""

import sys
from typing import Annotated, cast

import typer

from terrapyne.cli import triggers_cmd
from terrapyne.cli.context_helpers import get_client, validate_context
from terrapyne.cli.error_handlers import handle_cli_errors
from terrapyne.cli.output_helpers import emit_json, set_quiet_mode
from terrapyne.core.browser import get_workspace_url, open_url_in_browser
from terrapyne.core.context import resolve_organization
from terrapyne.core.exceptions import TFCAPIError, WorkspaceNotFoundError
from terrapyne.models.run import RunStatus
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.rendering.logging import console
from terrapyne.rendering.rich_tables import (
    render_workspace_dashboard,
    render_workspace_variables,
    render_workspace_vcs,
    render_workspaces,
)

app = typer.Typer(help="Workspace management commands")
app.add_typer(triggers_cmd.app, name="triggers")

var_app = typer.Typer(help="Workspace variable management")
app.add_typer(var_app, name="var")


@var_app.callback(invoke_without_command=True)
def _var_show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.callback(invoke_without_command=True)
def _show_help(
    ctx: typer.Context,
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress UI output (data only)"),
):
    if quiet:
        set_quiet_mode(True)
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
    no_truncate: bool = typer.Option(
        False, "--no-truncate", help="Disable column width truncation (auto-enabled when piped)"
    ),
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

        # Auto-disable truncation when output is piped (non-TTY)
        effective_no_truncate = no_truncate or not sys.stdout.isatty()
        render_workspaces(
            workspaces,
            f"Workspaces in {org}",
            total_count=total_count,
            no_truncate=effective_no_truncate,
        )

        if not search and total_count and total_count > 10:
            console.print(
                "\n[dim]Tip: Use --search to narrow results (e.g. --search 'prod-*')[/dim]"
            )


@app.command("id")
@handle_cli_errors
def workspace_id(
    ctx: typer.Context,
    workspace: str = typer.Argument(..., help="Workspace name"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
) -> None:
    """Print the raw workspace ID (ws-*) to stdout — no formatting."""
    org = resolve_organization(organization)
    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(workspace, organization=org)
    print(ws.id)


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
            active_statuses = ",".join(s.value for s in active_list)

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


@app.command("health")
@handle_cli_errors
def workspace_health(
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
    """Show workspace health snapshot (status, active runs, latest commit)."""
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(
            cast(str, ws_name), org, include="latest-run,latest-run.configuration-version"
        )

        latest_run = ws.latest_run
        active_runs_count = 0
        try:
            active_list = RunStatus.get_active_statuses()
            active_statuses = ",".join(active_list)
            _, total_active = client.runs.list(ws.id, status=active_statuses, limit=1)
            active_runs_count = total_active or 0
        except TFCAPIError as e:
            console.print(
                f"\n[yellow]Warning:[/yellow] Unable to fetch run activity "
                f"(API error {e.status_code})"
            )

        from terrapyne.rendering.rich_tables import render_workspace_snapshot

        render_workspace_snapshot(
            workspace=ws, latest_run=latest_run, active_runs_count=active_runs_count
        )


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
    """List variables for a workspace. (Legacy alias for 'workspace var list')"""
    var_list(ctx, workspace=workspace, organization=organization)


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
    """Set a workspace variable (create or update). (Legacy alias for 'workspace var set')"""
    var_set(
        ctx,
        workspace=workspace,
        key=key,
        value=value,
        category=category,
        hcl=hcl,
        sensitive=sensitive,
        description=description,
        organization=organization,
    )


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
    force: Annotated[
        bool, typer.Option("--force", "-f", "--yes", "-y", help="Skip confirmation")
    ] = False,
):
    """Remove a workspace variable. (Legacy alias for 'workspace var remove')"""
    var_remove(ctx, workspace=workspace, key=key, organization=organization, force=force)


@app.command("var-copy")
@handle_cli_errors
def workspace_var_copy(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Source workspace name"),
    target: str = typer.Argument(..., help="Target workspace name"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing variables"),
):
    """Copy all variables from one workspace to another. (Legacy alias for 'workspace var copy')"""
    var_copy(ctx, source=source, target=target, organization=organization, overwrite=overwrite)


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
    project_id: str | None = typer.Option(
        None,
        "--project-id",
        "-p",
        help="Project ID to assign the cloned workspace to (overrides source project)",
    ),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json"),
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

    if output_format != "json":
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
                project_id=project_id,
            )

            if result.get("status") == "error":
                console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")
                raise typer.Exit(1)

            new_ws = result.get("workspace")
            if output_format == "json" and new_ws is not None:
                emit_json(new_ws.model_dump())
                return

            console.print(f"\n[green]✓[/green] {result.get('message', 'Successfully cloned')}")

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


@app.command("create")
@handle_cli_errors
def workspace_create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Workspace name to create"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    project: str | None = typer.Option(None, "--project", "-p", help="Project ID to associate"),
    tf_version: str | None = typer.Option(
        None, "--tf-version", help="Terraform version (e.g. 1.9.0)"
    ),
    execution_mode: str | None = typer.Option(
        None, "--execution-mode", "-m", help="Execution mode: remote, local, agent"
    ),
    working_dir: str | None = typer.Option(
        None, "--working-dir", help="Working directory within VCS repo"
    ),
    vcs_repo: str | None = typer.Option(
        None, "--vcs-repo", help="VCS repo identifier (e.g. org/repo)"
    ),
    oauth_token_id: str | None = typer.Option(
        None, "--oauth-token-id", help="OAuth token ID for VCS connection"
    ),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    ignore_exists: bool = typer.Option(
        False, "--ignore-exists", help="Exit 0 if workspace already exists (idempotent)"
    ),
):
    """Create a new workspace.

    Examples:
        # Create a basic workspace
        tfc workspace create my-new-workspace --organization my-org

        # Capture the new workspace ID in a script
        WS_ID=$(tfc workspace create my-new-workspace --format json | jq -r .id)

        # Idempotent create — safe to retry
        tfc workspace create my-new-workspace --ignore-exists
    """
    from terrapyne.core.exceptions import TFCConflictError

    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified and not found in context.[/red]")
        raise typer.Exit(1)

    vcs_repo_config = None
    if vcs_repo:
        if not oauth_token_id:
            console.print("[red]Error: --oauth-token-id is required when --vcs-repo is set.[/red]")
            raise typer.Exit(1)
        vcs_repo_config = {"identifier": vcs_repo, "oauth-token-id": oauth_token_id}
        if working_dir:
            vcs_repo_config["working-directory"] = working_dir

    with get_client(ctx, organization=org) as client:
        try:
            ws = client.workspaces.create(
                name=name,
                organization=org,
                project_id=project,
                terraform_version=tf_version,
                execution_mode=execution_mode,
                working_directory=working_dir if not vcs_repo else None,
                vcs_repo=vcs_repo_config,
            )
        except TFCConflictError:
            if ignore_exists:
                ws = client.workspaces.get(name, organization=org)
            else:
                console.print(
                    f"[red]Error: Workspace '{name}' already exists. "
                    "Use --ignore-exists to return the existing workspace.[/red]"
                )
                raise typer.Exit(1) from None

    if output_format == "json":
        emit_json(ws.model_dump())
        return

    console.print(f"[green]✓[/green] Created workspace: {ws.name}")
    if ws.terraform_version:
        console.print(f"  Terraform version: {ws.terraform_version}")
    if ws.execution_mode:
        console.print(f"  Execution mode:    {ws.execution_mode}")
    if ws.project_id:
        console.print(f"  Project:           {ws.project_id}")

    url = get_workspace_url(org, ws.name)
    console.print(f"  View: {url}")


@app.command("update")
@handle_cli_errors
def workspace_update(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Workspace name to update"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    project_id: str | None = typer.Option(
        None, "--project-id", help="Project ID to move workspace to"
    ),
    project_name: str | None = typer.Option(
        None, "--project-name", help="Project name to move workspace to"
    ),
    tf_version: str | None = typer.Option(
        None, "--tf-version", help="Terraform version (e.g. 1.9.0)"
    ),
    execution_mode: str | None = typer.Option(
        None, "--execution-mode", "-m", help="Execution mode: remote, local, agent"
    ),
    working_dir: str | None = typer.Option(
        None, "--working-dir", help="Working directory within VCS repo"
    ),
    new_name: str | None = typer.Option(None, "--name", "-n", help="New name for the workspace"),
):
    """Update workspace configuration.

    Examples:
        # Update Terraform version
        tfc workspace update my-workspace --tf-version 1.9.0

        # Change execution mode
        tfc workspace update my-workspace --execution-mode local

        # Move to a different project
        tfc workspace update my-workspace --project-name my-project
    """
    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified and not found in context.[/red]")
        raise typer.Exit(1)

    if not any(
        [project_id, project_name, tf_version, execution_mode, working_dir is not None, new_name]
    ):
        console.print("[yellow]Warning: No update flags provided.[/yellow]")
        return

    with get_client(ctx, organization=org) as client:
        # Resolve project name to ID if provided
        final_project_id = project_id
        if project_name and not project_id:
            try:
                proj = client.projects.get_by_name(project_name, org)
                final_project_id = proj.id
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None

        try:
            ws = client.workspaces.update(
                workspace_name=name,
                organization=org,
                project_id=final_project_id,
                terraform_version=tf_version,
                execution_mode=execution_mode,
                working_directory=working_dir,
                name=new_name,
            )
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to update workspace: {e}")
            raise typer.Exit(1) from None

    console.print(f"[green]✓[/green] Successfully updated workspace '{name}'")
    if new_name:
        console.print(f"  New name:          {ws.name}")
    if tf_version:
        console.print(f"  Terraform version: {ws.terraform_version}")
    if execution_mode:
        console.print(f"  Execution mode:    {ws.execution_mode}")
    if final_project_id:
        console.print(f"  Project ID:        {ws.project_id}")

    url = get_workspace_url(org, ws.name)
    console.print(f"  View: {url}")


@app.command("set-branch")
@handle_cli_errors
def workspace_set_branch(
    ctx: typer.Context,
    workspace: str = typer.Argument(..., help="Workspace name"),
    branch: str = typer.Argument(..., help="VCS branch name to set"),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
):
    """Set the VCS branch for a workspace.

    Examples:
        # Switch to a feature branch
        tfc workspace set-branch my-workspace feature/my-change --organization my-org

        # Switch back to main
        tfc workspace set-branch my-workspace main --organization my-org
    """
    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified and not found in context.[/red]")
        raise typer.Exit(1)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.set_vcs_branch(
            workspace_name=workspace,
            branch=branch,
            organization=org,
        )

    console.print(f"[green]✓[/green] Updated VCS branch for workspace '{workspace}'")
    console.print(f"  Branch: {ws.vcs_branch or branch}")
    url = get_workspace_url(org, ws.name)
    console.print(f"  View: {url}")


@app.command("delete")
@handle_cli_errors
def workspace_delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Workspace name to delete"),
    organization: str | None = typer.Option(None, "--organization", "-o", help="TFC organization"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Delete a workspace.

    Examples:
        # Delete with confirmation prompt
        tfc workspace delete my-old-workspace --organization my-org

        # Delete without confirmation (use in CI/CD)
        tfc workspace delete my-old-workspace --organization my-org --force
    """
    org = resolve_organization(organization)
    if not org:
        console.print("[red]Error: Organization not specified and not found in context.[/red]")
        raise typer.Exit(1)

    with get_client(ctx, organization=org) as client:
        try:
            ws = client.workspaces.get(name, org)
        except WorkspaceNotFoundError:
            console.print(f"[red]Error:[/red] Workspace '{name}' not found in '{org}'.")
            raise typer.Exit(1) from None

        if not force and not typer.confirm(
            f"Delete workspace '{name}' in '{org}'? This cannot be undone."
        ):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

        client.workspaces.delete(ws.id)

    console.print(f"[green]✓[/green] Deleted workspace: {name}")


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


# ---------------------------------------------------------------------------
# workspace var subgroup — delegates to existing workspace_variable* logic
# ---------------------------------------------------------------------------


@var_app.command("list")
@handle_cli_errors
def var_list(
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


@var_app.command("set")
@handle_cli_errors
def var_set(
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
        variables: list[WorkspaceVariable] = client.workspaces.get_variables(ws.id) or []
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


@var_app.command("remove")
@handle_cli_errors
def var_remove(
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
    force: Annotated[
        bool, typer.Option("--force", "-f", "--yes", "-y", help="Skip confirmation")
    ] = False,
):
    """Remove a workspace variable."""
    if key is None:
        console.print("[red]Error: Variable key is required.[/red]")
        raise typer.Exit(1)

    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with get_client(ctx, organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        variables: list[WorkspaceVariable] = client.workspaces.get_variables(ws.id) or []
        existing_var = next((v for v in variables if v.key == key), None)

        if not existing_var:
            console.print(f"[yellow]Variable '{key}' not found in workspace '{ws_name}'[/yellow]")
            raise typer.Exit(1)

        if not force and not typer.confirm(f"Remove variable '{key}' from workspace '{ws_name}'?"):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

        client.workspaces.delete_variable(workspace_id=ws.id, variable_id=existing_var.id)
        console.print(f"[green]✓[/green] Removed variable: {key}")


@var_app.command("copy")
@handle_cli_errors
def var_copy(
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

        source_variables: list[WorkspaceVariable] = (
            client.workspaces.get_variables(ws_source.id) or []
        )
        target_variables: list[WorkspaceVariable] = (
            client.workspaces.get_variables(ws_target.id) or []
        )

        target_keys = {v.key for v in target_variables}

        console.print(f"[dim]Copying {len(source_variables)} variables: {source} → {target}[/dim]")

        copied = 0
        skipped = 0
        updated = 0

        for var in source_variables:
            if var.key in target_keys:
                if overwrite:
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
