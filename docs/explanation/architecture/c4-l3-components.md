# C4 Level 3: Components

**Detailed view of two focused sub-systems: API Layer and Models/Core/Context**

## Overview

This level breaks down the SDK and shared utilities into fine-grained components:

1. **API & Transport Layer** — HTTP client, 7 API classes, retry/pagination logic
2. **Models, Core Utilities & Context** — Pydantic models, parsing, diff, context resolution

Two separate diagrams for clarity; together they show the complete internal structure.

---

## Sub-diagram A: API & Transport Layer

```mermaid
graph TB
    subgraph SDKUser["SDK Consumer<br/>(CLI or external app)"]
        App["TFCClient instance"]
    end
    
    subgraph Transport["HTTP & Auth Layer"]
        TFCClient["🔧 TFCClient<br/>- manage Bearer token<br/>- retry logic<br/>- pagination cursor"]
        Session["requests.Session<br/>(with headers)"]
        Cache["@cached_property<br/>API instances"]
    end
    
    subgraph APIClasses["7 API Classes<br/>(domain-specific)"]
        WS["WorkspaceAPI<br/>get(), list(),<br/>create(), update(),<br/>lock(), unlock(),<br/>get_variables()"]
        RS["RunsAPI<br/>get(), list(),<br/>create(),<br/>get_plan(),<br/>get_plan_json(),<br/>get_apply()"]
        PR["ProjectAPI<br/>get(), list(),<br/>create(),<br/>get_workspace_counts()"]
        TM["TeamsAPI<br/>list_teams(),<br/>add_members(),<br/>get_access()"]
        SV["StateVersionsAPI<br/>get(),<br/>get_state_outputs(),<br/>get_state_version_outputs()"]
        VC["VCSAPI<br/>get_workspace_vcs(),<br/>update_workspace_branch(),<br/>list_repositories()"]
        CW["CloneWorkspaceAPI<br/>clone()"]
    end
    
    subgraph HTTP["HTTP Transport"]
        Requests["requests library<br/>(HTTP client)"]
        TFC_API["Terraform Cloud<br/>JSON:API"]
    end
    
    App -->|"calls methods on"| TFCClient
    
    TFCClient -->|"lazy-initializes"| Cache
    Cache -->|"caches instance of"| WS
    Cache -->|"caches instance of"| RS
    Cache -->|"caches instance of"| PR
    Cache -->|"caches instance of"| TM
    Cache -->|"caches instance of"| SV
    Cache -->|"caches instance of"| VC
    Cache -->|"caches instance of"| CW
    
    WS -->|"inherits"| TFCClient
    RS -->|"inherits"| TFCClient
    PR -->|"inherits"| TFCClient
    TM -->|"inherits"| TFCClient
    SV -->|"inherits"| TFCClient
    VC -->|"inherits"| TFCClient
    CW -->|"inherits"| TFCClient
    
    TFCClient -->|"uses to send"| Session
    Session -->|"HTTP GET/POST/PATCH"| Requests
    Requests -->|"REST calls"| TFC_API
    
    style TFCClient fill:#fff3e0
    style APIClasses fill:#e8f5e9
    style Transport fill:#f3e5f5
```

### API Class Responsibilities

| Class | Primary Operations | Key Methods |
|---|---|---|
| **WorkspaceAPI** | Create, read, list, update, lock/unlock workspaces | `get()`, `list()`, `create()`, `update()`, `lock()`, `unlock()`, `get_variables()` |
| **RunsAPI** | Query runs, download plans and applies | `get()`, `list()`, `create()`, `get_plan()`, `get_plan_json()`, `get_apply()` |
| **ProjectAPI** | Manage projects, count workspaces per project | `get()`, `list()`, `create()`, `get_workspace_counts()` |
| **TeamsAPI** | Query teams, manage team membership and access | `list_teams()`, `add_members()`, `get_access()` |
| **StateVersionsAPI** | Retrieve and analyze state versions | `get()`, `get_state_outputs()`, `get_state_version_outputs()` |
| **VCSAPI** | Query and update VCS connections | `get_workspace_vcs()`, `update_workspace_branch()`, `list_repositories()` |
| **CloneWorkspaceAPI** | Clone workspace state and variables to new workspace | `clone()` |

---

## Sub-diagram B: Models, Core & Context

```mermaid
graph TB
    subgraph PydanticModels["Pydantic Models<br/>(JSON:API Response Deserialization)"]
        Workspace["Workspace<br/>id, name, terraform_version,<br/>auto_apply, execution_mode,<br/>locked, tag_names, project_id"]
        Run["Run<br/>id, status, message, created_at,<br/>additions, changes, destructions,<br/>workspace_id, plan_id"]
        Plan["Plan<br/>id, status, resource_changes,<br/>output_changes"]
        Apply["Apply<br/>id, status, log"]
        Project["Project<br/>id, name, created_at,<br/>resource_count"]
        Team["Team<br/>id, name, created_at"]
        StateVersion["StateVersion<br/>id, serial, created_at,<br/>outputs"]
        VCSConnection["VCSConnection<br/>id, identifier, branch,<br/>oauth_token_id,<br/>repository_url,<br/>working_directory"]
    end
    
    subgraph CoreUtils["Core Utilities"]
        TFCreds["TerraformCredentials<br/>from_env() / from_file()<br/>api_token, organization"]
        RemoteBackend["RemoteBackend<br/>workspace_name,<br/>hostname, organization"]
        PlanParser["TerraformPlainTextPlanParser<br/>parse_plan_output()<br/>extract: additions,<br/>changes, destructions"]
        StateDiff["StateDiff<br/>compare_states()<br/>detect added/<br/>removed/changed<br/>resources"]
    end
    
    subgraph ContextResolution["Context Resolution"]
        ResOrg["resolve_organization()<br/>TFC_ORG env var<br/>or .terraform/"]
        ResWs["resolve_workspace()<br/>TFC_WORKSPACE env var<br/>or .terraform/"]
    end
    
    subgraph Presentation["Presentation & Rendering"]
        TableRenderer["rich_tables.py<br/>render_workspace_detail()<br/>render_run_list()<br/>render_project_list()<br/>render_team_list()<br/>render_vcs_repos()"]
    end
    
    subgraph Legacy["Legacy/Distinct"]
        TerraformBinary["Terraform class<br/>(subprocess wrapper)<br/>login(), validate(),<br/>show()"]
    end
    
    subgraph DataFlows["Key Data Flows"]
        Flow1["<b>workspace show</b><br/>CLI resolves org/ws<br/>→ calls WorkspaceAPI.get()<br/>→ deserializes to Workspace<br/>→ enriches with VCS + vars<br/>→ renders with TableRenderer"]
        
        Flow2["<b>run list</b><br/>CLI resolves workspace<br/>→ calls RunsAPI.list()<br/>→ deserializes to Run[] with<br/>configuration-version includes<br/>→ enriches with commit info<br/>→ renders with TableRenderer"]
    end
    
    PydanticModels -->|"deserialized from TFC API"| Workspace
    PydanticModels -->|"deserialized from TFC API"| Run
    PydanticModels -->|"included in Run"| Plan
    PydanticModels -->|"included in Run"| Apply
    PydanticModels -->|"deserialized from TFC API"| Project
    PydanticModels -->|"deserialized from TFC API"| Team
    PydanticModels -->|"deserialized from TFC API"| StateVersion
    PydanticModels -->|"deserialized from TFC API"| VCSConnection
    
    CoreUtils -->|"uses"| TFCreds
    CoreUtils -->|"uses"| RemoteBackend
    CoreUtils -->|"uses"| PlanParser
    CoreUtils -->|"uses"| StateDiff
    
    ContextResolution -->|"resolves with"| ResOrg
    ContextResolution -->|"resolves with"| ResWs
    
    TableRenderer -->|"renders"| PydanticModels
    
    Presentation -->|"calls"| TableRenderer
    
    Legacy -->|"distinct from API<br/>layer"| TerraformBinary
    
    Flow1 -->|"composed of"| ContextResolution
    Flow1 -->|"composed of"| CoreUtils
    Flow1 -->|"composed of"| Presentation
    
    Flow2 -->|"composed of"| ContextResolution
    Flow2 -->|"composed of"| CoreUtils
    Flow2 -->|"composed of"| Presentation
    
    style PydanticModels fill:#e8f5e9
    style CoreUtils fill:#f3e5f5
    style ContextResolution fill:#fff3e0
    style Presentation fill:#fce4ec
    style Legacy fill:#ffebee
```

### Model Serialization

All Pydantic models follow the same deserialization pattern:

```python
@classmethod
def from_api_response(cls, data: dict, included: dict | None = None):
    """Deserialize JSON:API response into model instance."""
    # Extract attributes
    attrs = data.get("attributes", {})
    # Extract relationships and optional includes
    return cls(
        id=data["id"],
        **attrs,
        **enriched_from_includes,
    )
```

This allows models to:
- Extract nested data from `included` array (e.g., commit info from `configuration-version`)
- Gracefully handle missing includes (fields remain None)
- Support dynamic enrichment without schema changes

### Core Utilities

| Utility | Purpose | Key Methods |
|---|---|---|
| **TerraformCredentials** | Read/write local TFC credentials file | `from_env()`, `from_file()`, `save()` |
| **RemoteBackend** | Parse `terraform { cloud { ... } }` block | Constructor from block dict |
| **TerraformPlainTextPlanParser** | Extract stats from `terraform show -json` | `parse_plan_output()` |
| **StateDiff** | Compare state versions, identify changes | `compare_states()` |

### Context Resolution

Two functions in `utils/context.py`:

| Function | Purpose | Sources (in order) |
|---|---|---|
| **resolve_organization()** | Find organization name | 1. CLI flag (`-o`) 2. `TFC_ORG` env var 3. `.terraform/terraform.tfstate` |
| **resolve_workspace()** | Find workspace name | 1. CLI flag (`-w`) 2. `TFC_WORKSPACE` env var 3. `.terraform/terraform.tfstate` |

### Presentation Layer

`rich_tables.py` provides rendering functions for each entity:

| Function | Input | Output |
|---|---|---|
| `render_workspace_detail()` | Workspace + variables + VCS | Rich table with fields and values |
| `render_run_list()` | Run[] | Rich table with id, status, message, stats |
| `render_project_list()` | Project[] | Rich table with id, name, resource count |
| `render_team_list()` | Team[] | Rich table with id, name, created_at |
| `render_vcs_repos()` | dict[] | Rich table with identifier, workspace count |

---

## Design Patterns

### Lazy Initialization

API classes are cached as properties on `TFCClient`:

```python
class TFCClient:
    @cached_property
    def workspaces(self) -> WorkspaceAPI:
        return WorkspaceAPI(self)
```

Benefits:
- Single instance per client
- Shared session and retry logic
- Reduced memory footprint

### Model Enrichment at Construction

Run model accepts optional `included` parameter:

```python
run = Run.from_api_response(
    data={"id": "run-abc", "attributes": {...}},
    included=[
        {"type": "configuration-version", "id": "cv-123", "attributes": {"commit": {...}}}
    ]
)
```

This allows:
- Hydration of related data without separate API calls
- Graceful degradation if includes are missing
- Centralized enrichment logic

### Pagination Transparency

Each API method handles pagination internally:

```python
# CLI calls once
for run in client.runs.list(workspace_id="ws-abc"):
    print(run.id)

# Internally: fetch pages, decode cursors, iterate all results
```

---

## Legacy: Terraform Class

The `Terraform` class (subprocess wrapper) exists but is **distinct** from the API layer:

- **Use case:** Local `terraform` commands that don't route through TFC API
- **Examples:** `terraform login`, `terraform validate`, `terraform show`
- **Not recommended for:** Workspace queries or state management (use SDK instead)

This is kept separate to emphasize that the primary data path is the TFC API, not subprocess invocation.
