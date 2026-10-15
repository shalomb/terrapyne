"""Raw TFC API gateway command."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Annotated, Any

import typer

from terrapyne.cli.context_helpers import get_client, validate_context
from terrapyne.cli.error_handlers import handle_cli_errors
from terrapyne.cli.safety import check_deletion_allowed
from terrapyne.rendering.logging import error_console

HINT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        r"GET",
        r"^/organizations/[^/]+/workspaces$",
        "Consider using 'tfc workspace list' for typed validation, filtering, and table/JSON formatting.",
    ),
    (
        r"POST",
        r"^/organizations/[^/]+/workspaces$",
        "Consider using 'tfc workspace create' with schema validation and project assignment.",
    ),
    (
        r"POST",
        r"^/workspaces/[^/]+/actions/lock$",
        "Consider using 'tfc workspace lock' with reason and safety checks.",
    ),
    (
        r"POST",
        r"^/workspaces/[^/]+/actions/unlock$",
        "Consider using 'tfc workspace unlock' with safety confirmation.",
    ),
    (
        r"GET",
        r"^/workspaces/[^/]+/runs$",
        "Consider using 'tfc run list' for run history and status filtering.",
    ),
    (
        r"GET",
        r"^/workspaces/[^/]+/current-state-version$",
        "Consider using 'tfc state current' to inspect active state.",
    ),
    (
        r"GET",
        r"^/workspaces/[^/]+/state-versions",
        "Consider using 'tfc state list' or 'tfc state show' for structured state inspection.",
    ),
    (
        r"DELETE",
        r"^/workspaces/[^/]+$",
        "Consider using 'tfc workspace delete' which includes confirmation prompts and session safeguards.",
    ),
    (
        r"PATCH",
        r"^/workspaces/[^/]+$",
        "Consider using 'tfc workspace update' for atomic attribute updates with schema validation.",
    ),
    (
        r"GET",
        r"^(/organizations/[^/]+/workspaces/[^/]+|/workspaces/[^/]+)$",
        "Consider using 'tfc workspace show' for workspace status, tags, and settings.",
    ),
    (
        r"POST",
        r"^/runs$",
        "Consider using 'tfc run create' for automatic workspace detection and plan monitoring.",
    ),
    (
        r"POST",
        r"^/runs/[^/]+/actions/apply$",
        "Consider using 'tfc run apply' for run monitoring and confirmation safety.",
    ),
    (
        r"POST",
        r"^/runs/[^/]+/actions/discard$",
        "Consider using 'tfc run cancel' to safely discard runs.",
    ),
    (
        r"GET",
        r"^/runs/[^/]+$",
        "Consider using 'tfc run show' for run progress and structured plan metrics.",
    ),
    (
        r"GET",
        r"^/organizations/[^/]+/projects$",
        "Consider using 'tfc project list' to list organization projects.",
    ),
    (
        r"POST",
        r"^/organizations/[^/]+/projects$",
        "Consider using 'tfc project create' to create projects.",
    ),
    (
        r"GET",
        r"^(/organizations/[^/]+/projects/[^/]+|/projects/[^/]+)$",
        "Consider using 'tfc project show' to inspect project details.",
    ),
    (
        r"DELETE",
        r"^(/organizations/[^/]+/projects/[^/]+|/projects/[^/]+)$",
        "Consider using 'tfc project delete' for safe project deletion.",
    ),
    (
        r"GET",
        r"^/organizations/[^/]+/teams$",
        "Consider using 'tfc team list' to list organization teams.",
    ),
    (
        r"POST",
        r"^/organizations/[^/]+/teams$",
        "Consider using 'tfc team create' to create teams.",
    ),
    (
        r"GET",
        r"^/teams/[^/]+$",
        "Consider using 'tfc team show' to inspect team details.",
    ),
    (
        r"GET",
        r"^/organizations/[^/]+/varsets$",
        "Consider using 'tfc varset list' to list variable sets.",
    ),
    (
        r"POST",
        r"^/organizations/[^/]+/varsets$",
        "Consider using 'tfc varset create' to create variable sets.",
    ),
    (
        r"GET",
        r"^/varsets/[^/]+$",
        "Consider using 'tfc varset show' to inspect variable set details.",
    ),
    (
        r"DELETE",
        r"^/varsets/[^/]+$",
        "Consider using 'tfc varset delete' for safe variable set deletion.",
    ),
    (
        r"GET",
        r"^/organizations/[^/]+/oauth-clients",
        "Consider using 'tfc vcs list' to inspect VCS providers.",
    ),
)


def get_subcommand_hint(method: str, path: str) -> str | None:
    """Return an advisory hint if a native, validated CLI subcommand exists for the endpoint.

    Args:
        method: HTTP method (e.g. GET, POST, DELETE).
        path: Interpolated API path (e.g. /organizations/my-org/workspaces).

    Returns:
        Recommendation string pointing to the high-level subcommand, or None.
    """
    normalized_path = path.rstrip("/")
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"

    for m_re, p_re, hint in HINT_PATTERNS:
        if re.match(m_re, method, re.IGNORECASE) and re.match(p_re, normalized_path):
            return hint
    return None


def interpolate_endpoint(
    endpoint: str, organization: str | None = None, workspace: str | None = None
) -> str:
    """Interpolate organization and workspace placeholders in an endpoint path.

    Supports:
        {organization}, :organization, {org}, :org
        {workspace}, :workspace, {ws}, :ws
    """
    interpolated = endpoint

    # Check for organization placeholders
    org_placeholders = ["{organization}", ":organization", "{org}", ":org"]
    has_org_placeholder = any(p in interpolated for p in org_placeholders)

    if has_org_placeholder:
        if not organization:
            raise ValueError(
                "Organization could not be resolved for '{organization}' placeholder. "
                "Specify --organization / -o or run from a directory with TFC context."
            )
        for p in org_placeholders:
            interpolated = interpolated.replace(p, organization)

    # Check for workspace placeholders
    ws_placeholders = ["{workspace}", ":workspace", "{ws}", ":ws"]
    has_ws_placeholder = any(p in interpolated for p in ws_placeholders)

    if has_ws_placeholder:
        if not workspace:
            raise ValueError(
                "Workspace could not be resolved for '{workspace}' placeholder. "
                "Specify --workspace / -w or run from a directory with TFC context."
            )
        for p in ws_placeholders:
            interpolated = interpolated.replace(p, workspace)

    return interpolated


def _parse_scalar(val: str) -> Any:
    """Parse a string value into a typed primitive (int, float, bool, null, or string)."""
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() in ("null", "none"):
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def parse_field_options(fields: list[str] | None) -> dict[str, Any]:
    """Parse a list of 'key=value' strings into a dictionary with typed scalars."""
    result: dict[str, Any] = {}
    if not fields:
        return result

    for f in fields:
        if "=" not in f:
            raise ValueError(f"Invalid field format '{f}'. Expected 'key=value'.")
        key, val = f.split("=", 1)
        key = key.strip()
        val = val.strip()

        # Check if value is valid JSON (object, array, etc.)
        if (val.startswith("{") and val.endswith("}")) or (
            val.startswith("[") and val.endswith("]")
        ):
            try:
                result[key] = json.loads(val)
                continue
            except Exception:
                pass

        result[key] = _parse_scalar(val)

    return result


def load_request_payload(input_val: str) -> dict[str, Any]:
    """Load JSON payload from a raw string, file path, or stdin ('-')."""
    raw_text: str
    if input_val == "-":
        raw_text = sys.stdin.read()
    elif Path(input_val).is_file():
        raw_text = Path(input_val).read_text(encoding="utf-8")
    else:
        raw_text = input_val

    try:
        parsed = json.loads(raw_text)
        if not isinstance(parsed, dict):
            raise ValueError(f"Payload must be a JSON object, got {type(parsed).__name__}")
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON payload: {e}") from e


@handle_cli_errors
def api_command(
    ctx: typer.Context,
    endpoint: Annotated[
        str,
        typer.Argument(
            help="TFC API endpoint path (e.g. /organizations/{organization}/workspaces)",
        ),
    ],
    method: Annotated[
        str,
        typer.Option(
            "--method",
            "-X",
            help="HTTP method (GET, POST, PATCH, DELETE, PUT)",
        ),
    ] = "GET",
    field: Annotated[
        list[str] | None,
        typer.Option(
            "--field",
            "-F",
            help="Request parameter or field formatted as key=value (repeatable)",
        ),
    ] = None,
    input_file: Annotated[
        str | None,
        typer.Option(
            "--input",
            "-i",
            help="Path to JSON payload file, inline JSON string, or '-' for stdin",
        ),
    ] = None,
    organization: Annotated[
        str | None,
        typer.Option(
            "--organization",
            "-o",
            help="TFC organization name (auto-detected from context if available)",
        ),
    ] = None,
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace name or ID (auto-detected from context if available)",
        ),
    ] = None,
    host: Annotated[
        str | None,
        typer.Option(
            "--host",
            "-H",
            help="TFC/TFE host (default: app.terraform.io)",
        ),
    ] = None,
    paginate: Annotated[
        bool,
        typer.Option(
            "--paginate",
            help="Automatically follow pagination links and aggregate items",
        ),
    ] = False,
    raw: Annotated[
        bool,
        typer.Option(
            "--raw",
            help="Output raw response text without JSON formatting",
        ),
    ] = False,
    hints: Annotated[
        bool,
        typer.Option(
            "--hints/--no-hints",
            help="Show advisory hints to stderr when a native subcommand exists",
        ),
    ] = True,
) -> None:
    """Execute an authenticated HTTP request against a raw Terraform Cloud or Enterprise REST API endpoint.

    IMPORTANT: This command is a low-level escape hatch intended for endpoints not
    yet covered by validated native subcommands. Whenever possible, prefer high-level
    subcommands ('tfc workspace', 'tfc run', 'tfc project', 'tfc team', 'tfc state')
    which provide schema validation, safety confirmations, session-gated protections,
    and structured output.
    """
    # Resolve organization / workspace if needed
    org, ws = validate_context(organization, workspace)
    interpolated_path = interpolate_endpoint(endpoint, organization=org, workspace=ws)

    # Ensure path begins with /
    if not interpolated_path.startswith("/") and not interpolated_path.startswith("http"):
        interpolated_path = f"/{interpolated_path}"

    upper_method = method.upper()

    # Emit advisory hint to stderr if a higher-level validated subcommand exists
    if hints and not os.environ.get("TERRAPYNE_NO_HINTS"):
        subcommand_hint = get_subcommand_hint(upper_method, interpolated_path)
        if subcommand_hint:
            error_console.print(f"[dim yellow]hint: {subcommand_hint}[/dim yellow]")

    if upper_method == "DELETE":
        check_deletion_allowed("api", ctx=ctx, output_format="raw" if raw else "json")

    # Parse fields
    field_dict = parse_field_options(field)

    params: dict[str, Any] | None = None
    json_data: dict[str, Any] | None = None

    if input_file:
        json_data = load_request_payload(input_file)
        if field_dict:
            json_data.update(field_dict)
    elif field_dict:
        if upper_method in ("GET", "HEAD"):
            params = field_dict
        else:
            json_data = field_dict

    with get_client(ctx, organization=org, host=host or "app.terraform.io") as client:
        if paginate and upper_method == "GET":
            # Paginate through results
            items: list[Any] = []
            for item in client.paginate(interpolated_path, params=params):
                items.append(item)
            output_obj = {"data": items}
            if raw:
                sys.stdout.write(json.dumps(output_obj) + "\n")
            else:
                sys.stdout.write(json.dumps(output_obj, indent=2) + "\n")
            return

        # Single request
        resp = client._request(
            method=upper_method,
            path=interpolated_path,
            params=params,
            json_data=json_data,
        )

        try:
            body_json = resp.json()
            if raw:
                sys.stdout.write(resp.text + "\n")
            else:
                sys.stdout.write(json.dumps(body_json, indent=2) + "\n")
        except Exception:
            # Non-JSON or empty response
            if resp.text:
                sys.stdout.write(resp.text + "\n")
