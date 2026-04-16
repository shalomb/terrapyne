# CLI Command Reference

Terrapyne provides the `tfc` command-line tool. Every command supports the `--format json` flag for structured output.

## Global Options

- `--version`: Show version and exit.
- `--quiet` / `-q`: Suppress all UI output (data only).
- `--debug`: Enable API call tracing and verbose logging.
- `--help`: Show help message and exit.

---

## `tfc workspace`
Workspace management and inspection.

- `list`: List workspaces in an organization.
- `show`: Show detailed workspace information.
- `vcs`: Show VCS configuration for a workspace.
- `variables`: List variables in a workspace.
- `var-set`: Create or update workspace variables (supports bulk setting).
- `var-copy`: Copy all variables from one workspace to another.
- `health`: Show workspace health: lock state, latest run, VCS, variables.
- `open`: Open workspace in browser.
- `clone`: Clone a workspace with optional variables and VCS configuration.
- `costs`: Show workspace TCO — total monthly cost from the latest cost estimate.

---

## `tfc run`
Run management and monitoring.

- `list`: List runs for a workspace.
- `show`: Show detailed information for a specific run.
- `plan`: Create a new plan (run) for a workspace.
- `logs`: Fetch and print the logs for a specific run.
- `apply`: Apply infrastructure changes.
- `errors`: Find errored runs across workspaces.
- `trigger`: Trigger a new run with optional targeting or replacement.
- `watch`: Watch run progress until complete.
- `follow`: Follow a run's logs in real-time.
- `discard`: Discard a run that is in a non-terminal state.
- `cancel`: Cancel a run that is currently planning or applying.
- `parse-plan`: Parse plain text terraform plan output.

---

## `tfc project`
Project discovery and cost aggregation.

- `list`: List all projects in organization.
- `find`: Find projects matching a pattern.
- `show`: Show project details and workspaces.
- `teams`: List team access for a project.
- `costs`: Aggregate cost estimates across all workspaces in a project.

---

## `tfc state`
State version and output management.

- `list`: List state versions for a workspace.
- `show`: Show state version metadata.
- `pull`: Download state JSON to stdout (like `terraform state pull`).
- `outputs`: List outputs from a state version or show a single output. Use `--raw` for unquoted values.

---

## `tfc team`
Team and membership management.

- `list`: List teams in an organization.
- `show`: Show detailed team information.
- `create`: Create a new team.
- `update`: Update team information.
- `delete`: Delete a team.
- `members`: List members of a team.
- `add-member`: Add a user to a team.
- `remove-member`: Remove a user from a team.

---

## `tfc vcs`
VCS connection and repository management.

- `show`: Show VCS configuration for workspace.
- `update-branch`: Update VCS branch for workspace.
- `repos`: List GitHub repositories connected to TFC workspaces.

---

## `tfc debug`
Troubleshooting and diagnostic tools.

- `run`: Diagnose run failures with log analysis.
- `workspace`: Check workspace health and configuration.
