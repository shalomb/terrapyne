# Terrapyne SDK

Python SDK for Terraform Cloud. Use terrapyne as a library in your own scripts.

## Installation

```bash
pip install terrapyne
# or
uv add terrapyne
```

## Quick Start

```python
from terrapyne import TFCClient

with TFCClient(organization="my-org") as client:
    # List workspaces
    workspaces, total = client.workspaces.list()
    for ws in workspaces:
        print(f"{ws.name} ({ws.terraform_version})")

    # Get a specific workspace
    ws = client.workspaces.get("my-app-dev")

    # List runs
    runs, _ = client.runs.list(ws.id, limit=5)
    for run in runs:
        print(f"{run.id}: {run.status.value} {run.changes_summary}")
```

## Authentication

Terrapyne reads credentials from `~/.terraform.d/credentials.tfrc.json` (the same file `terraform login` writes). No extra configuration needed.

## API Managers

All API operations are accessed through `TFCClient` properties:

| Property | Class | Operations |
|---|---|---|
| `client.workspaces` | `WorkspaceAPI` | list, get, get_by_id, get_variables, create_variable, update_variable |
| `client.runs` | `RunsAPI` | list, get, create, apply, get_plan, get_plan_logs, get_apply_logs, poll_until_complete |
| `client.projects` | `ProjectAPI` | list, get_by_name, get_by_id, list_team_access |
| `client.teams` | `TeamsAPI` | list_teams, get, create, update, delete, add/remove_member, get/set_project_access |
| `client.state_versions` | `StateVersionsAPI` | list, get, get_current, download, list_outputs, find_version_before |
| `client.vcs` | `VCSAPI` | get_workspace_vcs, update_workspace_branch, list_connections, list_repositories |

## Pydantic Models

All API responses are parsed into type-safe Pydantic models. You can import them directly from the package root:

```python
from terrapyne import (
    Apply,
    Plan,
    Project,
    Run,
    RunStatus,
    RunTrigger,
    StateVersion,
    StateVersionOutput,
    Team,
    TeamProjectAccess,
    VariableSet,
    VariableSetVariable,
    VCSConnection,
    Workspace,
    WorkspaceVCS,
    WorkspaceVariable,
)
```

Each model has a `from_api_response(data)` class method for parsing raw API responses.

### Models Reference

| Model | Description | Key Attributes |
|---|---|---|
| `Workspace` | Represents a Terraform Cloud workspace. | `id`, `name`, `terraform_version`, `working_directory`, `execution_mode` |
| `WorkspaceVCS` | VCS repository settings linked to a workspace. | `identifier`, `branch`, `oauth_token_id` |
| `WorkspaceVariable` | A variable defined in a workspace (Terraform or Environment). | `id`, `key`, `value`, `category`, `sensitive`, `hcl` |
| `VariableSet` | A reusable group of variables scoped to an organization or projects. | `id`, `name`, `description`, `global`, `project_count`, `var_count` |
| `VariableSetVariable` | A single variable defined inside a Variable Set. | `id`, `key`, `value`, `category`, `sensitive`, `hcl` |
| `Run` | Represents a Terraform execution run. | `id`, `status`, `message`, `is_speculative`, `created_at`, `plan_status` |
| `RunStatus` | Enum of possible run states (e.g., `PLANNING`, `APPLIED`, `ERRORED`). | Enum values representing the API state machine. |
| `RunTrigger` | Source workspace trigger that initiates runs on target workspaces. | `id`, `workspace_id`, `source_workspace_id` |
| `Plan` | Details of a run's planning phase. | `id`, `status`, `resource_additions`, `resource_destructions` |
| `Apply` | Details of a run's apply phase. | `id`, `status`, `resource_additions`, `resource_destructions` |
| `StateVersion` | Represents a specific state file version. | `id`, `serial`, `created_at`, `resource_count`, `run_id` |
| `StateVersionOutput` | Represents a single output from a state version. | `name`, `value`, `type`, `sensitive` |
| `Team` | Represents an organization team. | `id`, `name`, `member_count` |
| `TeamProjectAccess` | Represents a team's permissions on a project. | `team_id`, `project_id`, `access` |
| `Project` | Represents a project grouping workspaces. | `id`, `name`, `description` |
| `VCSConnection` | An OAuth connection link to a VCS provider (e.g., GitHub, GitLab). | `id`, `service_provider`, `name` |


## Examples

See the `examples/` directory for runnable scripts:

- `01_list_runs.py` — List recent runs for a workspace
- `02_create_plan.py` — Create a plan and poll until complete
- `03_batch_workspace_vars.py` — Manage workspace variables in bulk
- `04_clone_workspace.py` — Clone a workspace with variables and VCS
- `05_parse_plan.py` — Parse plain text plan output

## Plan Parser

Parse TFC plain text plan output (useful for remote backends where JSON plans aren't available):

```python
from terrapyne import PlanParser

parser = PlanParser()
result = parser.parse(plan_text)

print(f"Status: {result['status']}")
for resource in result.get("resources", []):
    print(f"  {resource['address']}: {resource['change']['actions']}")
```

## Local Terraform Wrapper

For local terraform operations (init, plan, apply):

```python
from terrapyne import Terraform

tf = Terraform(working_dir="/path/to/module")
tf.init()
tf.plan()
tf.apply()

# Inspect state
resources = tf.get_resources()
outputs = tf.get_outputs()
providers = tf.provider_selections
modules = tf.modules()
```
