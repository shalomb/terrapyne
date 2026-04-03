"""Workspace CLI commands."""

import builtins
from datetime import UTC
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console

from terrapyne.api.client import TFCClient
from terrapyne.cli.utils import handle_cli_errors, validate_context
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.utils.browser import get_workspace_url, open_url_in_browser
from terrapyne.utils.rich_tables import (
    render_workspace_detail,
    render_workspace_variables,
    render_workspace_vcs,
    render_workspaces,
)

app = typer.Typer(help="Workspace management commands")
console = Console()


@app.callback(invoke_without_command=True)
def _show_help(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("list")
@handle_cli_errors
def workspace_list(
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    search: str | None = typer.Option(
        None, "--search", "-s", help="Search pattern for workspace names"
    ),
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project name"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of workspaces to display"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
):
    """List workspaces in an organization.

    Auto-detects organization from .terraform/terraform.tfstate or terraform.tf if not specified.

    Examples:
        # List all workspaces (uses org from terraform.tf)
        terrapyne workspace list

        # List workspaces in specific organization
        terrapyne workspace list --organization Takeda

        # Search for workspaces
        terrapyne workspace list --search my-app

        # Filter by project
        terrapyne workspace list --project my-project
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        workspaces_iter, total_count = client.workspaces.list(search=search)
        workspaces = list(workspaces_iter)[:limit]

        if not workspaces:
            console.print("[yellow]No workspaces found.[/yellow]")
            return

        if output_format == "json":
            from terrapyne.cli.utils import emit_json

            emit_json(
                [
                    {
                        "id": ws.id,
                        "name": ws.name,
                        "terraform_version": ws.terraform_version,
                        "execution_mode": ws.execution_mode,
                        "locked": ws.locked,
                        "auto_apply": ws.auto_apply,
                    }
                    for ws in workspaces
                ]
            )
            return

        render_workspaces(workspaces, total_count=total_count)

        if not search:
            console.print("[dim]Tip: Use --search to narrow results (e.g. --search 'prod-*')[/dim]")


@app.command("show")
@handle_cli_errors
def workspace_show(
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
):
    """Show detailed workspace information.

    Auto-detects workspace and organization from .terraform/terraform.tfstate or terraform.tf if not specified.

    Examples:
        # Show current workspace (from terraform.tf)
        terrapyne workspace show

        # Show specific workspace
        terrapyne workspace show my-app-dev

        # Show workspace in specific organization
        terrapyne workspace show my-app-dev --organization Takeda
    """
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        if output_format == "json":
            from terrapyne.cli.utils import emit_json

            emit_json(
                {
                    "id": ws.id,
                    "name": ws.name,
                    "terraform_version": ws.terraform_version,
                    "execution_mode": ws.execution_mode,
                    "locked": ws.locked,
                    "auto_apply": ws.auto_apply,
                    "created_at": ws.created_at,
                    "project_id": ws.project_id,
                    "tag_names": ws.tag_names,
                }
            )
            return

        # Render workspace details
        render_workspace_detail(ws)

        # Fetch and render variables
        try:
            variables = client.workspaces.get_variables(ws.id)
            render_workspace_variables(variables)
        except Exception as e:
            console.print(f"\n[yellow]Warning:[/yellow] Unable to fetch variables: {e}")

        # Render VCS configuration
        render_workspace_vcs(ws)


@app.command("vcs")
@handle_cli_errors
def workspace_vcs(
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
    """Show VCS configuration for a workspace.

    Auto-detects workspace and organization from .terraform/terraform.tfstate or terraform.tf if not specified.

    Examples:
        # Show VCS config for current workspace
        terrapyne workspace vcs

        # Show VCS config for specific workspace
        terrapyne workspace vcs my-app-dev
    """
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        if not ws.vcs_repo:
            console.print(f"[yellow]Workspace '{ws_name}' has no VCS connection.[/yellow]")
            return

        # Display VCS info in a focused way
        from rich.table import Table

        table = Table(title=f"VCS Configuration: {workspace}", show_header=False, box=None)
        table.add_column("Property", style="bold cyan", width=25)
        table.add_column("Value")

        table.add_row("Repository", ws.vcs_identifier or "N/A")
        table.add_row("Branch", ws.vcs_branch or "N/A")

        if ws.vcs_repo.working_directory:
            table.add_row("Working Directory", ws.vcs_repo.working_directory)

        if ws.vcs_url:
            table.add_row("Repository URL", ws.vcs_url)

        table.add_row("Auto Apply", "✅ Enabled" if ws.auto_apply else "❌ Disabled")

        console.print(table)


@app.command("variables")
@handle_cli_errors
def workspace_variables(
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
    """List variables in a workspace.

    Examples:
        # List variables in current workspace
        terrapyne workspace variables

        # List variables in specific workspace
        terrapyne workspace variables my-app-dev

        # List variables in specific organization
        terrapyne workspace variables my-app-dev --organization Takeda
    """
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        variables = client.workspaces.get_variables(ws.id)

        if not variables:
            console.print("[yellow]No variables configured in this workspace.[/yellow]")
            return

        render_workspace_variables(variables)


@app.command("var-set")
@handle_cli_errors
def workspace_var_set(
    workspace: Annotated[
        str | None,
        typer.Argument(
            help="Workspace name (auto-detected from terraform.tf if in terraform directory)"
        ),
    ] = None,
    vars_list: Annotated[
        list[str] | None, typer.Argument(help="KEY=VAL pairs for bulk setting")
    ] = None,
    key: Annotated[str | None, typer.Option("--key", "-k", help="Variable name/key")] = None,
    value: Annotated[str | None, typer.Option("--value", "-v", help="Variable value")] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    category: Annotated[
        str,
        typer.Option(
            "--category",
            "-c",
            help="Variable category: 'terraform' or 'env'",
        ),
    ] = "terraform",
    sensitive: Annotated[
        bool, typer.Option("--sensitive", "-s", help="Mark variable as sensitive (masked in UI)")
    ] = False,
    hcl: Annotated[bool, typer.Option("--hcl", "-h", help="Variable value is HCL encoded")] = False,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Variable description")
    ] = None,
    from_env_file: Annotated[
        Path | None, typer.Option("--from-env-file", "-f", help="Import variables from .env file")
    ] = None,
):
    """Create or update workspace variables (supports bulk setting).

    Examples:
        # Create a single terraform variable
        terrapyne workspace var-set --key environment --value production

        # Bulk set multiple variables
        terrapyne workspace var-set my-ws KEY1=VAL1 KEY2=VAL2 --category env

        # Import from .env file
        terrapyne workspace var-set --from-env-file .env.prod --sensitive
    """
    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    # 1. Collect variables to set
    to_set: dict[str, str] = {}
    if key and value is not None:
        to_set[key] = value

    if vars_list:
        for pair in vars_list:
            if "=" not in pair:
                console.print(f"[yellow]Warning:[/yellow] Skipping invalid pair: {pair}")
                continue
            k, v = pair.split("=", 1)
            to_set[k.strip()] = v.strip()

    if from_env_file:
        if not from_env_file.exists():
            console.print(f"[red]❌ File not found:[/red] {from_env_file}")
            raise typer.Exit(1)

        with open(from_env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    # Strip quotes if present
                    v = v.strip().strip("'").strip('"')
                    to_set[k.strip()] = v

    if not to_set:
        console.print("[yellow]No variables provided to set.[/yellow]")
        return

    # Validate category
    if category not in ("terraform", "env"):
        console.print("[red]Error: category must be 'terraform' or 'env'[/red]")
        raise typer.Exit(1)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(cast(str, ws_name), org)
        existing_variables: list[WorkspaceVariable] = client.workspaces.get_variables(ws.id)

        results = []
        for k, v in to_set.items():
            existing_var = next((var for var in existing_variables if var.key == k), None)

            if existing_var:
                # Update
                console.print(f"[dim]Updating variable:[/dim] {k}")
                res = client.workspaces.update_variable(
                    variable_id=existing_var.id,
                    value=v,
                    hcl=hcl if hcl != existing_var.hcl else None,
                    sensitive=sensitive if sensitive != existing_var.sensitive else None,
                    description=description,
                )
                results.append(res)
            else:
                # Create
                console.print(f"[dim]Creating variable:[/dim] {k}")
                res = client.workspaces.create_variable(
                    workspace_id=ws.id,
                    key=k,
                    value=v,
                    category=category,
                    hcl=hcl,
                    sensitive=sensitive,
                    description=description,
                )
                results.append(res)

        console.print(f"[green]✓ Set {len(results)} variable(s).[/green]")
        render_workspace_variables(results)


@app.command("var-copy")
@handle_cli_errors
def workspace_var_copy(
    source: Annotated[str, typer.Argument(help="Source workspace name")],
    target: Annotated[str, typer.Argument(help="Target workspace name")],
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization (auto-detected from context if available)",
        ),
    ] = None,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite existing variables in target")
    ] = False,
    sensitive_only: Annotated[
        bool, typer.Option("--sensitive-only", help="Copy only sensitive variables")
    ] = False,
):
    """Copy all variables from one workspace to another.

    Examples:
        # Copy all variables from dev to staging
        terrapyne workspace var-copy my-app-dev my-app-staging

        # Copy only and overwrite existing
        terrapyne workspace var-copy dev staging --overwrite
    """
    org, _ = validate_context(organization)

    with TFCClient(organization=org) as client:
        # Get source and target workspaces
        src_ws = client.workspaces.get(source)
        tgt_ws = client.workspaces.get(target)

        # Get source variables
        src_vars: builtins.list[WorkspaceVariable] = client.workspaces.get_variables(src_ws.id)
        if sensitive_only:
            src_vars = [v for v in src_vars if v.sensitive]

        if not src_vars:
            console.print(f"[yellow]No variables found in source workspace '{source}'.[/yellow]")
            return

        # Get target variables to check for existence
        tgt_vars: builtins.list[WorkspaceVariable] = client.workspaces.get_variables(tgt_ws.id)
        tgt_var_keys = {v.key for v in tgt_vars}

        console.print(
            f"[dim]Copying {len(src_vars)} variables from '{source}' to '{target}'...[/dim]"
        )

        copied_count = 0
        updated_count = 0
        skipped_count = 0

        for v in src_vars:
            if v.key in tgt_var_keys:
                if overwrite:
                    # Update existing
                    existing_id = next(tv.id for tv in tgt_vars if tv.key == v.key)
                    client.workspaces.update_variable(
                        variable_id=existing_id,
                        value=v.value,
                        hcl=v.hcl,
                        sensitive=v.sensitive,
                        description=v.description,
                    )
                    updated_count += 1
                else:
                    skipped_count += 1
                    continue
            else:
                # Create new
                client.workspaces.create_variable(
                    workspace_id=tgt_ws.id,
                    key=v.key,
                    value=v.value or "",
                    category=v.category,
                    hcl=v.hcl,
                    sensitive=v.sensitive,
                    description=v.description,
                )
                copied_count += 1

        console.print(
            f"[green]✓ Done![/green] Copied: {copied_count}, Updated: {updated_count}, Skipped: {skipped_count}"
        )


@app.command("health")
@handle_cli_errors
def workspace_health(
    workspace: Annotated[
        str | None,
        typer.Argument(help="Workspace name (auto-detected from context)"),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option("--organization", "-o", help="TFC organization"),
    ] = None,
):
    """Show workspace health: lock state, latest run, VCS, variables.

    Examples:
        terrapyne workspace health my-app-dev
        terrapyne workspace health  # auto-detect from context
    """

    from terrapyne.api.vcs import VCSAPI

    org, ws_name = validate_context(organization, workspace, require_workspace=True)

    with TFCClient(organization=org) as client:
        ws = client.workspaces.get(ws_name or "", org)
        variables: builtins.list[WorkspaceVariable] = client.workspaces.get_variables(ws.id)
        runs, _ = client.runs.list(ws.id, limit=1)
        latest_run = runs[0] if runs else None

        # VCS
        vcs_api = VCSAPI(client)
        vcs = vcs_api.get_workspace_vcs(ws.id)

    # Render health dashboard
    console.print(f"\n[bold]{ws.name}[/bold]  [dim]({ws.id})[/dim]\n")

    # Lock state
    lock_icon = "[red]🔒 Locked[/red]" if ws.locked else "[green]🔓 Unlocked[/green]"
    console.print(f"  Lock:       {lock_icon}")

    # Terraform version
    console.print(f"  TF Version: {ws.terraform_version or 'not set'}")
    console.print(f"  Exec Mode:  {ws.execution_mode or 'remote'}")
    console.print(f"  Auto-Apply: {'yes' if ws.auto_apply else 'no'}")

    # Latest run
    if latest_run:
        age = ""
        if latest_run.created_at:
            from datetime import datetime

            delta = (
                datetime.now(UTC) - latest_run.created_at.replace(tzinfo=UTC)
                if latest_run.created_at.tzinfo is None
                else datetime.now(UTC) - latest_run.created_at
            )
            if delta.days > 0:
                age = f" ({delta.days}d ago)"
            else:
                hours = delta.seconds // 3600
                age = f" ({hours}h ago)" if hours > 0 else " (recent)"
        console.print(
            f"  Last Run:   {latest_run.status.emoji} {latest_run.status.value}{age}  [{latest_run.id}]"
        )
        console.print(f"  Changes:    {latest_run.changes_summary}")
    else:
        console.print("  Last Run:   [dim]no runs[/dim]")

    # VCS
    if vcs:
        console.print(f"  VCS Repo:   {vcs.identifier}")
        console.print(f"  Branch:     {vcs.branch or 'default'}")
        if vcs.working_directory:
            console.print(f"  Work Dir:   {vcs.working_directory}")
    else:
        console.print("  VCS:        [dim]not connected[/dim]")

    # Variables
    tf_vars = [v for v in variables if v.is_terraform_var]
    env_vars = [v for v in variables if v.is_env_var]
    sensitive_count = sum(1 for v in variables if v.sensitive)
    console.print(
        f"  Variables:  {len(tf_vars)} terraform, {len(env_vars)} env"
        + (f" ({sensitive_count} sensitive)" if sensitive_count else "")
    )

    # Tags
    if ws.tag_names:
        console.print(f"  Tags:       {', '.join(ws.tag_names)}")

    console.print()


@app.command("open")
@handle_cli_errors
def workspace_open(
    workspace: str | None = typer.Argument(
        None, help="Workspace name (auto-detected from context if in terraform directory)"
    ),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    host: str = typer.Option(
        "app.terraform.io",
        "--host",
        help="TFC hostname (default: app.terraform.io)",
    ),
    page: str | None = typer.Option(
        None,
        "--page",
        help="Specific page to open (runs, states, variables, settings)",
    ),
):
    """Open workspace in browser.

    Auto-detects workspace and organization from .terraform/terraform.tfstate or terraform.tf.

    Examples:
        # Open current workspace (auto-detected from context)
        terrapyne workspace open

        # Open specific workspace
        terrapyne workspace open my-app-dev --organization Takeda

        # Open workspace runs page
        terrapyne workspace open --page runs

        # Open workspace on custom TFC host
        terrapyne workspace open my-ws -o MyOrg --host terraform.example.com
    """
    org, ws = validate_context(organization, workspace, require_workspace=True)

    # Construct URL
    url = get_workspace_url(
        organization=org,
        workspace=ws or workspace or "",
        host=host,
        page=page,  # type: ignore
    )

    console.print(f"[dim]Opening:[/dim] {url}")

    # Attempt to open in browser
    if not open_url_in_browser(url):
        console.print("[yellow]Could not open browser. Please visit:[/yellow]")
        console.print(f"  {url}")
        raise typer.Exit(1) from None


@app.command("clone")
@handle_cli_errors
def workspace_clone(
    source: str = typer.Argument(..., help="Source workspace name to clone from"),
    target: str = typer.Argument(..., help="Target workspace name to create"),
    organization: str | None = typer.Option(
        None,
        "--organization",
        "-o",
        help="TFC organization (auto-detected from context if available)",
    ),
    with_variables: bool = typer.Option(
        False,
        "--with-variables",
        help="Clone terraform and environment variables",
    ),
    with_vcs: bool = typer.Option(
        False,
        "--with-vcs",
        help="Clone VCS repository connection and configuration",
    ),
    vcs_oauth_token_id: str | None = typer.Option(
        None,
        "--vcs-oauth-token-id",
        help="OAuth token ID for VCS (required for cross-organization cloning)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing target workspace if it exists",
    ),
):
    """Clone a workspace with optional variables and VCS configuration.

    Creates a new workspace based on an existing workspace's configuration.
    Optionally includes variables, VCS settings, and other components.

    Always clones workspace settings (terraform version, execution mode, auto_apply, tags).

    Examples:
        # Basic clone (settings and tags only)
        terrapyne workspace clone prod-app staging-app

        # Clone with variables
        terrapyne workspace clone prod-app staging-app --with-variables

        # Clone with VCS configuration
        terrapyne workspace clone prod-app staging-app --with-vcs

        # Full clone with all options
        terrapyne workspace clone prod-app staging-app --with-variables --with-vcs

        # Clone to specific organization
        terrapyne workspace clone prod-app test-app -o test-org --with-variables

        # Force overwrite existing workspace
        terrapyne workspace clone prod-app staging-app --force
    """
    org, _ = validate_context(organization)

    console.print(f"\n[dim]Cloning workspace:[/dim] {source} → {target}")

    with TFCClient(organization=org) as client:
        from terrapyne.api.workspace_clone import CloneWorkspaceAPI

        clone_api = CloneWorkspaceAPI(client)

        result = clone_api.clone(
            source_workspace_name=source,
            target_workspace_name=target,
            organization=org,
            with_variables=with_variables,
            with_vcs=with_vcs,
            vcs_oauth_token_id=vcs_oauth_token_id,
            force=force,
        )

        # Display results
        if result["status"] == "success":
            console.print(f"\n[green]✓[/green] {result['message']}\n")

            # Show target workspace ID
            console.print(f"[dim]Target workspace ID:[/dim] {result['target_workspace_id']}")

            # Show variable results if included
            if with_variables and result["results"]["variables"]:
                var_result = result["results"]["variables"]
                if var_result["status"] == "success":
                    console.print(
                        f"[dim]Variables cloned:[/dim] {var_result['variables_cloned']} "
                        f"({var_result['terraform_variables']} terraform, "
                        f"{var_result['env_variables']} env)"
                    )

            # Show VCS results if included
            if with_vcs and result["results"]["vcs"]:
                vcs_result = result["results"]["vcs"]
                if vcs_result.get("vcs_cloned"):
                    console.print(
                        f"[dim]VCS configured:[/dim] {vcs_result['identifier']} "
                        f"(branch: {vcs_result.get('branch', 'default')})"
                    )
                elif vcs_result.get("status") == "success":
                    console.print(
                        f"[yellow]Note:[/yellow] {vcs_result.get('reason', 'No VCS to clone')}"
                    )

            console.print()  # Blank line at end
        else:
            console.print(f"\n[red]Error:[/red] {result.get('error', 'Unknown error')}\n")
            raise typer.Exit(1)
