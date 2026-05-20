# TODO — Terrapyne Product Backlog

Bugs, gaps, and improvements. Sources:
- Exploratory testing against live TFC
- Product fitness appraisal against TFC API model (April 2026)

## Development Requirements

All new features and fixes must strictly follow:
1. **Red/Green TDD**: Write a failing test first, make it pass with minimal code, then refactor.
2. **Adzic BDD**: Use Gojko Adzic's Specification by Example principles to write `.feature` files.
3. **ACP (Atomic Commit Protocol)**: Every commit must be atomic, verified, and uses Conventional Commits.

## Test Environment

For evaluating live TFC behaviour, use:
- `/home/unop/oneTakeda/terraform-dce-developer-ShalomBhooshi/iac/dev`

---

## Priority Matrix (WSJF)

**Impact**: 🔴 High (4), 🟡 Medium (2), 🟢 Low (1)
**Effort**: S=1, M=2, L=3
**WSJF** = Impact / Effort

| # | Finding | Impact | Effort | WSJF | Status |
|---|---|---|---|---|---|
| **NEW FEATURES** |
| F4 | Workspace notifications (webhook/Slack config) | 🟡 | M | 1.0 | TODO |
| F5 | Policy sets / Sentinel outcome reporting | 🟡 | M | 1.0 | TODO |
| F6 | Private registry query (modules + providers) | 🟡 | M | 1.0 | TODO |
| F7 | Agent pools — list and show self-hosted agents | 🟡 | M | 1.0 | TODO |
| F8 | SSH keys / VCS OAuth token management | 🟢 | L | 0.33 | TODO |
| F9 | `workspace update` command and API update method | 🔴 | M | 2.0 | TODO |
| **COMPLETED** |
| B3 | `paginate_with_meta` `included` leaks only last page | 🟡 | S | 2.0 | ✅ |
| B4 | `project.list()` wildcard search strips `*` but doesn't post-filter | 🟢 | S | 1.0 | ✅ |
| B5 | `runs.get()` never passes `include=plans` — `plan_status` always `None` | 🔴 | S | 4.0 | ✅ |
| B6 | `get_error_summary` falls back to `run.message` when `plan_status` is `None` instead of trying apply log | 🔴 | S | 4.0 | ✅ |
| B1 | `_handle_response_error` catches wrong exception type | 🔴 | S | 4.0 | ✅ |
| B2 | Retry-on-mutation: POST/PATCH/DELETE retry `TFCAPIError` (unsafe) | 🔴 | S | 4.0 | ✅ |
| 17 | Restore test coverage to 65% | 🔴 | S | 4.0 | ✅ |
| 18 | Fix cost estimate regression | 🔴 | S | 4.0 | ✅ |
| 19 | Remove broad exception silencing in `workspace_cmd.py` | 🔴 | S | 4.0 | ✅ |
| 20 | Use `RunStatus` enum instead of hardcoded strings | 🟡 | S | 2.0 | ✅ |
| 9  | `--raw` flag for `state outputs` | 🟡 | S | 2.0 | ✅ |
| 13.1 | `--json` output for `workspace show` | 🟡 | S | 2.0 | ✅ |
| 13.2 | `--json` output for `project show` | 🟡 | S | 2.0 | ✅ |
| 13.3 | Workspace health enrichment (active runs, VCS metadata) | 🟡 | M | 1.33 | ✅ |
| 13.4 | Log streaming for `run follow` | 🟡 | M | 1.33 | ✅ |
| 21 | Consolidate `workspace show` API calls | 🟡 | M | 1.0 | ✅ |
| 22 | Strict validation for `Run.from_api_response` | 🟡 | M | 1.0 | ✅ |
| 6  | `--debug` flag for API call tracing | 🟡 | M | 1.0 | ✅ |
| 1c | `tfc project show` project snapshot | 🟡 | M | 1.0 | ✅ |
| 8  | Local file-based response cache with TTL | 🟢 | L | 0.3 | ✅ |
| 10 | Enhanced run lifecycle (trigger types, queue wait, approvals) | 🔴 | M | 2.0 | ✅ |
| 14 | Restore test coverage minimum to 80% (long-term goal) | 🔴 | M | 2.0 | ✅ |
| C1 | `cloud` block backend detection (Terraform ≥ 1.1) | 🔴 | M | 2.0 | ✅ |
| C2 | `run plan` semantics mismatch — not a true speculative plan | 🟡 | M | 1.0 | ✅ |
| C3 | `StateVersionsAPI.list()` needless workspace round-trip | 🟢 | S | 1.0 | ✅ |
| F1 | Variable Sets (`/varsets`) — org/project-scoped variables | 🔴 | L | 1.33 | ✅ |
| F2 | Run Triggers — workspace-to-workspace automation | 🔴 | L | 1.33 | ✅ |
| F3 | `workspace create` / `workspace delete` commands | 🔴 | M | 2.0 | ✅ |

---

## Task Details

### B5 — `runs.get()` never requests `include=plans`

**Intent**: Populate `run.plan_status` so callers can determine whether the error is in the plan or apply stage.

**Context**: `runs.get(run_id)` fetches `/runs/{id}` with no `include` param. The `Run.from_api_response` model correctly handles a `plans` sideload to extract `plan_status`, but since it’s never requested the field is always `None`. This silently breaks `get_error_summary` (see B6) and any downstream logic that branches on plan_status.

**Root cause**:
```python
# api/runs.py:get()
path = f"/runs/{run_id}"
response = self.client.get(path, params=params)  # no include=plans
```

**Fix**: Always include `plans` in the sideload, or pass it when the caller needs plan_status:
```python
params["include"] = "plan"  # sideloads the plan object
```

**Success Criteria**:
- `client.runs.get(run_id).plan_status` returns `"finished"` for a run whose plan succeeded but apply errored
- Existing tests updated; new test covers plan_status population

---

### B6 — `get_error_summary` silent fallback when `plan_status` is `None`

**Intent**: Surface the actual Terraform error from errored runs, not the run message.

**Context**: `get_error_summary` branches on `plan_status == "finished"` to decide whether to read the apply log or the plan log. When `plan_status` is `None` (always, due to B5), it reads the plan log — which is empty for apply-stage failures — then silently falls back to `run.message`. The caller sees the commit message instead of the Terraform error.

Discovered during ASG BB integration testing:
```
# Expected:
Error: creating Lambda Function: InvalidParameterValueException: 
  The provided execution role does not have permissions to call CreateNetworkInterface

# Actual (run.message fallback):
"fix: VPC Lambda IAM permissions"
```

**Fix**: When `plan_status` is `None`, try both logs (apply first for plan-and-apply runs, then plan log as fallback):
```python
if run.plan_status == "finished" or (run.plan_status is None and run.apply_id):
    raw = self.get_apply_logs(run.apply_id) if run.apply_id else ""
    if not raw:  # fallback to plan log
        raw = self.get_plan_logs(run.plan_id)
else:
    raw = self.get_plan_logs(run.plan_id)
```

**Success Criteria**:
- `get_error_summary` returns the Terraform `Error:` text for apply-stage failures even when `plan_status` is `None`
- `tfc run errors` and `tfc run show` surface the actual error, not the commit message
- Fixes B5 first (so plan_status is populated), then B6 is the defensive fallback
- Test covers: plan-errored run, apply-errored run, apply-errored run with plan_status=None

---

### B1 — `_handle_response_error` catches wrong exception type

**Intent**: Fix silent failure in HTTP error handling — errors currently propagate as raw `httpx.HTTPStatusError` instead of domain exceptions.

**Context**: `_handle_response_error` calls `response.raise_for_status()` and catches `TFCAPIError`. But `httpx` raises `httpx.HTTPStatusError`, not `TFCAPIError`. The catch block is unreachable; all HTTP errors bypass domain exception mapping entirely.

**Success Criteria**:
- `except httpx.HTTPStatusError` used instead of `except TFCAPIError`
- `TFCAuthenticationError`, `TFCNotFoundError`, `TFCConflictError`, `TFCRateLimitError`, `TFCServerError` are raised correctly on 401/403/404/409/429/5xx
- Existing tests updated/extended to verify the mapping

---

### B2 — Retry-on-mutation is unsafe

**Intent**: Prevent duplicate resource creation or double-apply from over-eager retry on non-idempotent calls.

**Context**: `post`, `patch`, and `delete` all retry on `TFCAPIError`. A run creation or variable update that times out server-side but returns a 500 could be retried, creating duplicates. Retry should only apply to idempotent operations or be narrowed to `TFCServerError` on mutations.

**Success Criteria**:
- `post` / `patch` / `delete` retry only on `TFCServerError` (5xx), not on generic `TFCAPIError`
- Or: mutation methods have no retry decorator and callers handle retries explicitly where safe
- Test covers retry-not-triggered scenario for 409 on POST

---

### B3 — `paginate_with_meta` `included` leaks only last page

**Intent**: Ensure relationship data (project names, run details) is correctly resolved for all pages, not just the last one fetched.

**Context**: `ResponseIterator.included` is overwritten on each page fetch. Workspace listings spanning multiple pages lose project name resolution for workspaces on page 2+.

**Success Criteria**:
- `included` accumulates across all pages (or is merged per item)
- `workspace list` with >100 workspaces correctly resolves project names throughout

---

### B4 — Project wildcard search false positives

**Intent**: `project find 10234-*` should return only projects whose names start with `10234-`, not every project containing `10234`.

**Context**: The wildcard is stripped to a bare substring for the `q=` param. No post-filtering is applied, so `my-10234-project` is included in results for `10234-*`.

**Success Criteria**:
- After fetching API results, apply Python `fnmatch` filtering on the pattern
- Works for prefix (`10234-*`), suffix (`*-MAN`), and contains (`*235*`) patterns

---

### C1 — `cloud` block backend detection

**Intent**: Auto-detect org/workspace from modern Terraform configurations that use the `cloud` block.

**Context**: `backend "remote"` was soft-deprecated in Terraform 1.1 in favour of the `cloud` block. Most contemporary codebases use `cloud`. The current `backend.py` regex and HCL parser only handle `backend "remote"`, so context auto-detection silently fails for modern configs.

```hcl
terraform {
  cloud {
    organization = "my-org"
    workspaces {
      name = "my-workspace"
    }
  }
}
```

**Success Criteria**:
- `detect_backend()` parses `cloud` blocks (both HCL and regex fallback)
- Returns a `RemoteBackend` with the same fields as today
- Existing `backend "remote"` tests still pass
- New fixture `.tf` files cover `cloud` block variants (name, tags, prefix)

---

### C2 — `run plan` semantics mismatch

**Intent**: Align the `run plan` command with TFC's concept of a speculative plan.

**Context**: `run plan` creates a confirmable plan run (`auto_apply=False`). TFC's true speculative plan is a read-only, non-confirmable plan attached to a `configuration-version` with `speculative: true`. These are different: a speculative plan cannot be applied; the current command's output *can* be applied via `run apply`.

**Options**:
1. Rename `run plan` to `run queue` (plan queued for potential apply)
2. Add a separate `run speculative` command via the configuration-version API
3. Add a `--speculative` flag to `run plan` / `run trigger`

**Success Criteria** (option 3 recommended):
- `run trigger --speculative` creates a true speculative plan via configuration-version API
- Existing `run plan` behaviour preserved but documented as "queued plan"
- Help text distinguishes the two modes

---

### C3 — `StateVersionsAPI.list()` unnecessary round-trip

**Intent**: Remove redundant workspace lookup when listing state versions by workspace ID.

**Context**: TFC's `/state-versions` endpoint accepts `filter[workspace][id]` directly. The current implementation fetches the workspace by ID first to get its name, then uses `filter[workspace][name]`. This adds a round-trip.

**Success Criteria**:
- `filter[workspace][id]` used when a `workspace_id` is provided
- Workspace name resolution only happens when `workspace_name` is explicitly needed
- Existing `state list` behaviour unchanged

---

### F1 — Variable Sets

**Intent**: Allow listing, inspecting, and applying variable sets — the primary mechanism for shared variables at org/project scope in TFC.

**Context**: Variable Sets (`/varsets`) are one of the most heavily used TFC primitives in multi-workspace organisations. Without them, the tool cannot support common patterns like shared AWS credentials or shared environment configs.

**Success Criteria**:
- `tfc varset list` — list org-level variable sets
- `tfc varset show <name>` — show variables in a set
- `tfc varset apply <name> --workspace <ws>` — apply set to a workspace
- `tfc varset remove <name> --workspace <ws>` — detach set from workspace
- Models: `VariableSet`, `VariableSetVariable`
- JSON output supported

---

### F2 — Run Triggers

**Intent**: Enable inspection and management of workspace-to-workspace run trigger relationships.

**Context**: Run triggers are central to TFC pipeline patterns — workspace B re-plans when workspace A applies successfully. Without visibility, debugging pipeline failures is blind.

**Success Criteria**:
- `tfc workspace triggers list <ws>` — list upstream trigger sources for a workspace
- `tfc workspace triggers add <ws> --source <upstream-ws>` — add a trigger
- `tfc workspace triggers remove <ws> --source <upstream-ws>` — remove a trigger
- Model: `RunTrigger`

---

### F3 — `workspace create` / `workspace delete`

**Intent**: Complete the workspace lifecycle — bootstrapping and teardown are as common as inspection.

**Context**: `workspace clone` exists but there's no bare create or delete. CI pipelines that provision ephemeral workspaces (e.g., per-PR environments) have no way to use the tool end-to-end.

**Success Criteria**:
- `tfc workspace create <name> --project <p> --tf-version <v> --execution-mode <m>`
- `tfc workspace delete <name> [--force]` with confirmation guard
- `workspace create` supports `--vcs-repo`, `--oauth-token-id`, `--working-dir` for VCS-connected workspaces
- Integration with existing `workspace clone` internals where possible

---

### F4 — Workspace Notifications

**Intent**: Inspect and configure notification triggers (Slack, webhook, email, PagerDuty) on workspaces.

**Success Criteria**:
- `tfc workspace notifications list <ws>`
- `tfc workspace notifications add <ws> --type slack --url <url> --triggers apply,errored`
- `tfc workspace notifications remove <ws> <notification-id>`

---

### F5 — Policy Set Outcomes

**Intent**: Surface Sentinel/OPA policy check results in run output without requiring the TFC UI.

**Success Criteria**:
- `run show` includes policy check outcomes when present (pass/fail/override per policy)
- `tfc policy list` — list policy sets scoped to a workspace or project
- JSON output supported

---

### F6 — Private Registry Query

**Intent**: Allow platform teams to discover modules and providers in the private registry without the UI.

**Success Criteria**:
- `tfc registry modules list` — list private modules with version info
- `tfc registry providers list` — list private providers
- `tfc registry modules show <namespace>/<name>/<provider>` — show versions and readme

---

### F7 — Agent Pools

**Intent**: Provide visibility into self-hosted agent pools and agent status.

**Success Criteria**:
- `tfc agent list` — list agent pools and agents with status (idle/busy/errored)
- `tfc agent show <pool-id>` — show pool details and connected agents
- JSON output supported

---

### F8 — SSH Keys / VCS OAuth Tokens

**Intent**: Support workspace provisioning workflows that require attaching SSH keys or VCS tokens.

**Success Criteria**:
- `tfc vcs tokens list` — list OAuth tokens in the org
- `tfc ssh list` / `tfc ssh show <id>` — list/inspect SSH keys
- Used internally by `workspace create --vcs-repo` (F3 dependency)

---

*(Task 14 — restore coverage to 80% — remains a long-term goal, tracked separately)*

---

## Documentation & Architecture Audit (April 2026)

### Priority Matrix Additions

| # | Finding | Impact | Effort | WSJF | Status |
|---|---|---|---|---|---|
| **DOCS** |
| D4 | SDK models table incomplete | 🟡 | S | 2.0 | TODO |
| D5 | `plan-parser.md` is a planning artifact, not explanation | 🟡 | S | 2.0 | TODO |
| D6 | ADR-004 Gherkin examples diverged from feature file | 🟡 | S | 2.0 | TODO |
| D9 | Update reference docs for missing models | 🟢 | S | 1.0 | TODO |
| **ARCH** |
| A16 | `sensitive=True` variables may leak values in `--debug` log output | 🟡 | S | 2.0 | TODO |
| A8 | Three uncoordinated `Console()` instances | 🟡 | M | 1.33 | TODO |
| A12 | `run_cmd.py` decomposition (852 lines) | 🟢 | L | 0.3 | TODO |
| A13 | `paginate()` and `paginate_with_meta()` divergent | 🟢 | M | 0.5 | TODO |
| A14 | Domain errors defined in API layer | 🟢 | S | 1.0 | TODO |
| A15 | `utils/` is an unconstrained catch-all | 🟢 | L | 0.3 | TODO |
| A17 | Export all SDK models in package root | 🟡 | S | 2.0 | TODO |
| **COMPLETED** |
| D1 | Fix broken docs links in AGENTS.md & deprecate GEMINI.md | 🔴 | S | 4.0 | ✅ |
| D2 | CLI reference lists non-existent `workspace health` | 🟡 | S | 2.0 | ✅ |
| D3 | SDK reference missing managers (state_versions, vcs) | 🟡 | S | 2.0 | ✅ |
| D8 | How-to SDK example: clarify Iterator and nullable total | 🟢 | S | 1.0 | ✅ |
| A6 | `model_construct()` skips validation across all models | 🟡 | M | 1.33 | ✅ |
| A3 | `emit_json` imports `unittest.mock.Mock` in prod | 🟡 | S | 2.0 | ✅ |
| A4 | `parse-plan` CLI spawns local Terraform binary | 🟡 | S | 2.0 | ✅ |
| A7 | `Workspace.latest_run` Any type (circular ref) | 🟡 | S | 2.0 | ✅ |
| A9 | `Terraform` and `TFCClient` conflated in top-level | 🟡 | M | 1.0 | ✅ |
| A10| `RunStatus.get_active_statuses()` returns `list[str]` | 🟢 | S | 1.0 | ✅ |
| A11| Inline `RunStatus` import in `workspace_show` | 🟢 | S | 1.0 | ✅ |
| D7 | Promote `workspace health` to real CLI command | 🟡 | M | 1.33 | ✅ |

### Task Details (Audit)

#### D1 — Fix AGENTS.md links & GEMINI.md deprecation
- **Context**: Guide paths moved in Diataxis restructure but AGENTS.md was not updated. GEMINI.md has duplicate/divergent agent instructions.
- **Action**: Update links to `docs/how-to/` and `docs/explanation/`. Merge unique Ralph/Bart/ACP rules from GEMINI.md into AGENTS.md. Delete GEMINI.md.

#### A4 — parse-plan binary dependency
- **Context**: `tfc run parse-plan` currently creates a `Terraform` object which fails if the binary is missing, even though the parser is pure Python.
- **Action**: Call `PlanParser` directly from `terrapyne.sdk.plan_parser`.

#### A6 — model_validate instead of model_construct
- **Context**: Performance "optimization" that bypasses Pydantic validation on API ingestion.
- **Action**: Re-enable validation to catch malformed TFC responses early.

#### A7 — Workspace.latest_run type hint
- **Context**: Uses `Any` to avoid circular import.
- **Action**: Use `from __future__ import annotations` and `if TYPE_CHECKING: from ...run import Run`.

#### A16 — Sensitive variable values may leak in `--debug` output

**Context**: Variables with `sensitive=True` are masked in normal CLI output, but the `--debug` flag traces all API payloads. If a variable's value appears in a request/response body during debug logging, it is exposed in plaintext even though the user marked it sensitive.

**Action**: Filter or redact `value` fields for sensitive variables in debug-mode API response logging. Add a `__repr__` override on `Variable` that masks the value when `sensitive=True`.

---

#### A12 — run_cmd.py decomposition
- **Context**: 850 lines mixing CLI glue with complex log streaming and polling state machines.
- **Action**: Extract `RunMonitor` or move polling logic to `RunsAPI`.

---

#### F9 — `workspace update` command and API update method

**Intent**: Complete the workspace CRUD operations (F3) by supporting update/patch operations on workspace configurations.

**Success Criteria**:
- `tfc workspace update <name> [--tf-version <v>] [--execution-mode <m>] [--working-dir <d>] [--project-id <p>] [--project-name <pn>]`
- API support: `client.workspaces.update(workspace_id, ...)`
- Standard TDD/BDD tests verifying the modifications are propagated correctly.

---

#### A17 — Export all SDK models in package root

**Intent**: Export standard models like `VariableSet`, `RunTrigger`, `Apply`, `StateVersion`, `StateVersionOutput`, and `RunStatus` directly from the `terrapyne` package root.

**Success Criteria**:
- Package imports: `from terrapyne import VariableSet, RunTrigger, Apply, StateVersion, StateVersionOutput, RunStatus` work seamlessly.
- Models are added to `__all__` in `src/terrapyne/__init__.py`.

---

#### D9 — Update reference docs for missing models

**Intent**: Add documentation for missing models (`VariableSet`, `VariableSetVariable`, `RunTrigger`) to `docs/reference/sdk.md`.

**Success Criteria**:
- Import example and model lists in `docs/reference/sdk.md` contain references to `VariableSet`, `VariableSetVariable`, and `RunTrigger`.


