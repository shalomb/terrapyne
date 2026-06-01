# TODO — Terrapyne Product Backlog

> [!IMPORTANT]
> **AGENTS**: Before pulling tasks from this backlog or writing any code, you MUST read `AGENTS.md` and strictly follow the TDD/BDD Adzic/Farley rules, ACP commit protocol, and the Adversarial Review (Bart) workflow.


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

## Iteration Plan (May 2026)

Based on recent Agent-Native CLI design research, the backlog is currently structured into the following upcoming PR Batches:

- **PR Batch 3: The Agent Experience (AX) Core** *(In Progress — feat/ax-core)*
  Focus: Eliminating agent "glue logic" (bash pipes, jq, polling loops).
  Includes: AX1 ✅, AX2 ✅, AX3 ✅, AX4 ✅, AX5 ✅, AX6 ✅, AX7 (Deep Error Context Surfacing).

- **PR Batch 4: Scripting & Automation Polish** *(In Progress — fix/scripting-polish)*
  Focus: Fixing bugs that break non-interactive shell scripting and automation pipelines.
  Includes: B13 (exit code), B14 (missing --yes), B12 (truncation), B9 (name lookup bug), B15 (flag position).

- **PR Batch 5: CLI Surface Refactoring & Security**
  Focus: Paying down technical debt, improving consistency, and patching data leaks.
  Includes: A18 (var command refactor), A16 (sensitive leak), D10 (docs).

- **PR Batch 6: Automation & Agent Contract**
  Focus: Closing the gap between documented CLI design principles and actual implementation.
  Includes: AX-stdout (stderr separation), AX-json-mutations (structured output for mutations), AX-next-action (IDs + next-step hints), AX-no-interactive (flag bypasses), AX-tty-aware (pipe-safe output).

---

## Priority Matrix (WSJF)

**Impact**: 🔴 High (4), 🟡 Medium (2), 🟢 Low (1)
**Effort**: S=1, M=2, L=3
**WSJF** = Impact / Effort

| # | Finding | Impact | Effort | WSJF | Status |
|---|---|---|---|---|---|
| **BUGS (May 2026)** |
| B7 | `run follow` / `run logs` silent on pre-plan errors — falls back to `"Run failed before generating logs"` with no error text | 🔴 | S | 4.0 | ✅ [#114](https://github.com/shalomb/terrapyne/pull/114) |
| B8 | `run logs` returns empty for errored runs even when log is available via archivist URL | 🔴 | S | 4.0 | ✅ [#114](https://github.com/shalomb/terrapyne/pull/114) |
| B9 | `run list` fails by workspace name for some workspaces — requires workspace ID workaround | 🟡 | S | 2.0 | ✅ |
| B10 | `workspace clone` 422 "Agent pool not found" — drops agent-pool relationship from create payload | 🔴 | S | 4.0 | ✅ |
| B11 | `workspace create` missing `--project` flag — no way to assign workspace to a project at creation | 🔴 | S | 4.0 | ✅ |
| B12 | `workspace list` name truncation — no `--no-truncate` or `--max-width` option | 🟡 | S | 2.0 | 🔄 fix/scripting-polish |
| B13 | `run trigger` exits non-zero on success — breaks `&&` chains and scripting | 🟡 | S | 2.0 | 🔄 fix/scripting-polish |
| B14 | `workspace var-rm` no `--yes`/`-y` flag — always prompts interactively, unusable in scripts | 🟡 | S | 2.0 | 🔄 fix/scripting-polish |
| B15 | `--quiet` flag position-sensitive — `terrapyne workspace list --quiet` fails; must be `terrapyne --quiet workspace list` | 🟢 | S | 1.0 | 🔄 fix/scripting-polish (partial: `workspace --quiet list` now works) |
| **NEW FEATURES** |
| F13 | `workspace set-branch <workspace> <branch>` — switch VCS branch from CLI | 🟡 | S | 2.0 | ✅ |
| F4 | Workspace notifications (webhook/Slack config) | 🟡 | M | 1.0 | TODO |
| F5 | Policy sets / Sentinel outcome reporting | 🟡 | M | 1.0 | TODO |
| F6 | Private registry query (modules + providers) | 🟡 | M | 1.0 | TODO |
| F7 | Agent pools — list and show self-hosted agents | 🟡 | M | 1.0 | TODO |
| F8 | SSH keys / VCS OAuth token management | 🟢 | L | 0.33 | TODO |
| F10 | Context honoring (org/workspace) in `run list` and `run logs` | 🟡 | S | 2.0 | TODO |
| **COMPLETED** |
| F9 | `workspace update` command and API update method | 🔴 | M | 2.0 | ✅ |
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
| D4 | SDK models table incomplete | 🟡 | S | 2.0 | ✅ |
| D5 | `plan-parser.md` is a planning artifact, not explanation | 🟡 | S | 2.0 | ✅ |
| D6 | ADR-004 Gherkin examples diverged from feature file | 🟡 | S | 2.0 | ✅ |
| D9 | Update reference docs for missing models | 🟢 | S | 1.0 | ✅ |
| **ARCH** |
| A12 | `run_cmd.py` decomposition (852 lines) | 🟢 | L | 0.3 | TODO |
| A13 | `paginate()` and `paginate_with_meta()` divergent | 🟢 | M | 0.5 | TODO |
| A14 | Domain errors defined in API layer | 🟢 | S | 1.0 | TODO |
| **COMPLETED** |
| A15 | `utils/` is an unconstrained catch-all | 🟢 | L | 0.3 | ✅ |
| A17 | Export all SDK models in package root | 🟡 | S | 2.0 | ✅ |
| A16 | `sensitive=True` variables may leak values in `--debug` log output | 🟡 | S | 2.0 | ✅ |
| A8 | Three uncoordinated `Console()` instances | 🟡 | M | 1.33 | ✅ |
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



---

### B7 — `run follow` / `run logs` silent on pre-plan errors

**Context**: During vault dynamic credentials debugging (May 2026), runs were failing in TFC's pre-init phase (before `terraform plan` runs). `terrapyne run follow <run-id>` reported:

```
Run failed before generating logs: errored
```

with no error text. The actual error (`failed authenticating to Vault: role not found`) was only accessible by manually fetching the archivist log URL via raw TFC API calls:

```bash
PLAN_ID=$(curl ... "$BASE/runs/$RUN_ID" | jq -r '.data.relationships.plan.data.id')
LOG_URL=$(curl ... "$BASE/plans/$PLAN_ID" | jq -r '.data.attributes["log-read-url"]')
curl -sk "$LOG_URL"
```

**Root cause**: `run follow` likely checks for a non-empty log via the streaming endpoint before the archivist URL is populated, and bails early when nothing is streamed. Pre-init failures write logs to the archivist URL (same as normal plan logs) but may not trigger the streaming path.

**Fix**: When a run errors and no streamed log is available, fall back to fetching the plan log via the archivist URL (`plans/{id}.log-read-url`) and print it. This is the same path used for normal plan log retrieval.

**Success Criteria**:
- `run follow <run-id>` prints the full plan log (including pre-init Vault auth errors) for errored runs
- `run logs <run-id>` also works for runs that errored before the plan phase
- Existing streaming behaviour for in-progress runs is unchanged

---

### B8 — `run logs` returns empty for errored runs

**Context**: Same debugging session. After a run had already errored and `run follow` failed, `run logs <run-id>` was tried:

```
Logs for plan stage are empty or not yet ready.
```

The logs were neither empty nor unready — they were available at the archivist URL. The command appears to be polling a streaming/live endpoint that is already closed for a completed (errored) run.

**Root cause**: `run logs` likely uses a log streaming endpoint that only serves data while a run is active. For terminal runs (errored, applied, cancelled), logs must be fetched from the archivist URL instead.

**Fix**: For terminal run states, skip the streaming endpoint and fetch directly from `plans/{id}.log-read-url` (plan stage) or `applies/{id}.log-read-url` (apply stage).

**Success Criteria**:
- `run logs <run-id>` returns the plan log for any errored run regardless of when it is called
- Works for both pre-init failures and mid-plan failures
- `--stage plan|apply` flag respected

---

### B10 — `workspace clone` 422 "Agent pool not found"

**Context**: During provisioning of `tec-man-dad-dev-10803-appstream` (an agent-pool workspace in the `10803-MAN` project), `terrapyne workspace clone` returned HTTP 422 with `"Agent pool not found"`.

**Root cause**: `workspace clone` reads the source workspace's attributes (including `execution-mode: agent`) but does not copy the `agent-pool-assignment` relationship into the `POST /workspaces` create payload. TFC rejects the request because execution mode `agent` requires an explicit agent-pool relationship.

**Workaround used**: Raw API call including the relationship:
```bash
curl -s -X POST \
  -H "Authorization: Bearer $TFC_TOKEN" \
  -H "Content-Type: application/vnd.api+json" \
  "$BASE/organizations/Takeda/workspaces" \
  -d '{
    "data": {
      "type": "workspaces",
      "attributes": { "name": "...", "execution-mode": "agent", ... },
      "relationships": {
        "agent-pool": { "data": { "type": "agent-pools", "id": "<pool-id>" } }
      }
    }
  }'
```

**Fix**: When the source workspace has `execution-mode: agent`, include the `agent-pool` relationship (from `source.relationships["agent-pool"].data.id`) in the create payload.

**Success Criteria**:
- `workspace clone <source> <dest>` succeeds when source is an agent-pool workspace
- Cloned workspace has the same agent-pool assignment as the source
- Non-agent workspaces unaffected

---

### B11 — `workspace create` missing `--project` flag

**Context**: There is no `--project` flag on `workspace create` (nor on `workspace clone`). Workspaces created without a project assignment land in the organisation's default project, requiring a separate patch to move them.

**Workaround used**: Raw API `POST /workspaces` with `"relationships": { "project": { "data": { "type": "projects", "id": "<proj-id>" } } }`.

**Fix**: Add `--project-id` and/or `--project-name` to `workspace create`. When `--project-name` is given, resolve to ID via `projects.find()`.

**Success Criteria**:
- `tfc workspace create <name> --project 10803-MAN` assigns workspace to that project at creation
- `workspace clone <src> <dest> --project <p>` overrides source project with target project
- Help text documents that omitting the flag places the workspace in the default project

---

### B12 — `workspace list` name truncation

**Context**: `workspace list` truncates workspace names in tabular output, making it impossible to distinguish long names (e.g. `tec-man-dad-dev-10803-appstream` vs `tec-man-dad-dev-10803-appstream-2`). There is no `--no-truncate` or `--max-width` option.

**Fix**: Add a `--no-truncate` flag (or `--max-width 0` for unlimited) that disables column truncation. When output is piped (non-TTY), disable truncation by default.

**Success Criteria**:
- `tfc workspace list --no-truncate` shows full names in all columns
- Piped output (`tfc workspace list | grep ...`) is never truncated
- Default TTY output is unchanged

---

### B13 — `run trigger` exits non-zero on success

**Context**: `terrapyne run trigger <workspace>` exits with a non-zero exit code even when the run is successfully queued. This breaks `&&` chains in scripts:
```bash
terrapyne run trigger tec-dce-inn-dev-93400-shalombhooshi && echo "triggered"
# "triggered" never printed despite run being queued
```

**Fix**: Audit exit code logic in `run trigger`. Return 0 when a run ID is returned from the API. Non-zero only on API error or missing workspace.

**Success Criteria**:
- `terrapyne run trigger <ws>; echo $?` prints `0` after a successful queue
- `terrapyne run trigger <nonexistent>; echo $?` prints non-zero

---

### B14 — `workspace var-rm` no `--yes`/`-y` flag

**Context**: `workspace var-rm` always prompts interactively for confirmation. This makes it unusable in scripts or automated workflows without PTY allocation.

**Fix**: Add `--yes`/`-y` flag to skip confirmation. Follow the pattern established by `workspace delete --force`.

**Success Criteria**:
- `tfc workspace var-rm <ws> <var> --yes` removes without prompting
- Without `--yes`, interactive prompt behaviour is preserved

---

### B15 — `--quiet` flag is position-sensitive

**Context**: `terrapyne workspace list --quiet` fails or is ignored. The flag must be placed before the subcommand: `terrapyne --quiet workspace list`. This is non-obvious and differs from CLI conventions where global flags are accepted anywhere.

**Fix**: Register `--quiet` as a Typer global option that is accepted in any position (before or after the subcommand group). Or document the required position clearly in help text.

**Success Criteria**:
- Both `terrapyne --quiet workspace list` and `terrapyne workspace list --quiet` suppress progress output
- `--help` output makes the global-flag requirement clear if position restriction is intentional

---

### B9 — `run list` fails by workspace name for some workspaces

**Context**: `list-runs.sh` (tfc-api skill) returned `"Workspace not found"` for `tec-dce-inn-dev-93400-shalombhooshi` despite the workspace existing. The `terrapyne run list` command may have the same issue.

**Likely cause**: Workspace name lookup uses an exact-match search that is case-sensitive or encoding-sensitive, or the underlying `workspaces.get_by_name()` call uses a filter that doesn't match workspace names containing multiple hyphens or digits correctly.

**Fix**: Verify that `workspaces.get_by_name()` uses `filter[names]` or exact-name endpoint (`/organizations/{org}/workspaces/{name}`) rather than a fuzzy search. Add a test covering workspace names with digits and multiple hyphens.

**Success Criteria**:
- `run list tec-dce-inn-dev-93400-shalombhooshi` returns runs without error
- Workspace name lookup is consistent with `workspace show` (which works correctly)

---

## Documentation & Architecture Audit (April 2026)

### Priority Matrix Additions

| # | Finding | Impact | Effort | WSJF | Status |
|---|---|---|---|---|---|
| **DOCS** |
| D10| `cli-reference.md` missing several commands (`varset`, `workspace create`) | 🟡 | S | 2.0 | TODO |
| D4 | SDK models table incomplete | 🟡 | S | 2.0 | ✅ |
| D5 | `plan-parser.md` is a planning artifact, not explanation | 🟡 | S | 2.0 | ✅ |
| D6 | ADR-004 Gherkin examples diverged from feature file | 🟡 | S | 2.0 | ✅ |
| D9 | Update reference docs for missing models | 🟢 | S | 1.0 | ✅ |
| **ARCH** |
| A18 | Fragmented `workspace var-*` commands instead of noun-verb | 🟡 | S | 2.0 | TODO |
| A16 | `sensitive=True` variables may leak values in `--debug` log output | 🟡 | S | 2.0 | TODO |
| A8 | Three uncoordinated `Console()` instances | 🟡 | M | 1.33 | TODO |
| A12 | `run_cmd.py` decomposition (852 lines) | 🟢 | L | 0.3 | TODO |
| A13 | `paginate()` and `paginate_with_meta()` divergent | 🟢 | M | 0.5 | TODO |
| A14 | Domain errors defined in API layer | 🟢 | S | 1.0 | ✅ |
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

---

#### D10 — `cli-reference.md` missing several commands

**Intent**: Document all available CLI commands to ensure users can discover them.

**Context**: `tfc varset`, `tfc workspace create`, `tfc workspace delete`, `tfc workspace triggers`, and `tfc vcs list` are completely missing from the CLI reference document. Additionally, `tfc vcs update-branch` is documented but doesn't exist.

**Success Criteria**:
- Add missing commands to `docs/reference/cli-reference.md` with accurate help text.
- Remove `vcs update-branch` or implement it.

---

#### A18 — Fragmented `workspace var-*` commands

**Intent**: Standardize variable management under a consistent `workspace var` subcommand group.

**Context**: Workspace variables currently use hyphenated verbs (`var-set`, `var-rm`, `var-copy`, `variables`) instead of a cleaner noun-verb subgroup (e.g., `workspace var set`). This fragments the CLI surface and is inconsistent with top-level variable sets (`varset`).

**Success Criteria**:
- Refactor `var-set`, `var-rm`, `var-copy`, and `variables` into a new `workspace var` subcommand group.
- Example: `tfc workspace var list`, `tfc workspace var set`.

---

## Automation & Agent Contract: Implementation Gaps

These items close the gap between the principles documented in `docs/explanation/design-philosophy.md` and the current implementation. Each maps to a named principle.

| # | Principle | Gap | Impact | Effort | Status |
|---|---|---|---|---|---|
| AX-stdout | stdout/stderr separation | `console.print` writes non-data output to stdout; breaks `cmd \| jq` | 🔴 | M | TODO |
| AX-json-mutations | Structured output contract | `workspace create`, `workspace clone`, `run trigger` lack `--format json` | 🔴 | S | TODO (AX5) |
| AX-next-action | Output guides next action | Successful mutations don't consistently echo the resource ID and next-step hint | 🟡 | S | TODO |
| AX-actionable-errors | Actionable errors | API errors lack fix-command hints; only AX7 (title+detail) implemented so far | 🟡 | M | PARTIAL |
| AX-no-interactive | No interactive requirements | `workspace var-rm` has no `--yes`; `--quiet` is position-sensitive (B14, B15) | 🟡 | S | TODO |
| AX-tty-aware | TTY-aware output | `workspace list` truncates in pipes; no auto-disable of truncation on non-TTY (B12) | 🟡 | S | TODO |

### AX-stdout — stderr separation

**Intent**: Non-data output (progress, warnings, tables, confirmations) must not contaminate stdout, which is reserved for machine-readable data.

**Context**: `console = Console()` (without `stderr=True`) writes Rich output to stdout. Any command with `--format json` is polluted by progress lines unless the caller redirects explicitly.

**Fix**: Switch the shared `console` to `Console(stderr=True)`, or introduce a separate `console_err` for progress/warnings and use `print()` / `sys.stdout.write()` only for structured data output.

**Success Criteria**:
- `terrapyne workspace list --format json 2>/dev/null` produces valid JSON with no non-JSON lines
- `terrapyne run trigger my-ws --format json | jq .id` works without shell gymnastics

### AX-next-action — Output guides the next action

**Intent**: Every successful mutation should print the ID of the created/modified resource on a predictable line, and where relevant, suggest the next command.

**Context**: `workspace create` prints `✓ Workspace created` but buries the ID in a table. An agent parsing stdout for the ID has no reliable target line.

**Fix**: For mutations, always emit the resource ID as the last line of stdout (or as the `id` field in `--format json`). For wait commands, print the concluding `run show <id>` or equivalent on success.

**Success Criteria**:
- `terrapyne workspace create my-ws | tail -1` reliably outputs just the workspace ID
- `--format json` output always contains an `id` field for singular resources

---

## Agent Experience (AX) Epic

These features are specifically designed to reduce the "glue logic" (bash pipes, `jq`, `grep`, `while` loops) that AI coding agents must write to orchestrate complex TFC workflows.

### AX1 — Universal ID Resolver Utility
**Context**: When agents need to fallback to raw `curl` for unsupported API endpoints, they need the exact TFC ID (e.g. `ws-*`, `prj-*`, `team-*`). Currently they must run `list` or `show --format json` and pipe to `jq`.
**Fix**: Add an `id` command to all entity subgroups that prints ONLY the raw ID string to stdout.
**Success Criteria**:
- `terrapyne workspace id my-ws` outputs `ws-xyz123`
- `terrapyne project id my-project` outputs `prj-xyz123`

### AX2 — The "Latest Run" Lookups
**Context**: Triggering an action on the most recent run requires listing runs, parsing JSON, extracting the first element's ID, and passing it to the next command.
**Fix**: Add a `--latest` flag to run read commands (`run show`, `run logs`).
**Success Criteria**:
- `terrapyne run logs --workspace my-ws --latest` works without needing a run ID.

### AX3 — The "Trigger and Wait" Loop
**Context**: CI/CD automation and agents hate writing `while` loops to poll run status. `run follow` exists but streams verbose logs which bloats context windows.
**Fix**: Add a `--wait` flag to `run trigger` that blocks until the run hits a terminal state, returning a non-zero exit code if it errored, without streaming logs.
**Success Criteria**:
- `terrapyne run trigger my-ws --wait` pauses execution silently and exits 0 on applied, or >0 on errored/canceled.

### AX4 — State Output Extraction
**Context**: Passing outputs from one workspace to another requires parsing the full state JSON payload.
**Fix**: Add a dedicated `state output` command to extract a single raw output value.
**Success Criteria**:
- `terrapyne state output my-ws vpc_id` prints the raw string value of the output.

### AX5 — Structured & Parseable Output for Mutations
**Context**: While read commands support `--format json`, mutation commands (create, clone, trigger) only print rich console text. Agents need JSON to reliably capture newly created IDs without parsing ANSI text.
**Fix**: Add a `--format json` flag (or ensure `--json` works globally) to all mutation commands (`workspace create`, `workspace clone`, `run trigger`).
**Success Criteria**:
- `terrapyne workspace create my-ws --format json` prints a JSON object with the new workspace ID.

### AX6 — Idempotence and Safe Retries
**Context**: If an agent runs `workspace create` and gets interrupted, running it again fails with a 409 Conflict. Agents often retry on error, creating a loop.
**Fix**: Add idempotency flags to mutation commands, such as `--ignore-exists` for `workspace create`.
**Success Criteria**:
- `terrapyne workspace create my-ws --ignore-exists` succeeds (or exits gracefully without a fatal error) if the workspace is already provisioned.

### AX7 — Deep Error Context Surfacing
**Context**: When a CLI command fails, it often prints a high-level error (e.g. `Status: ❌ errored` or `API Error (422)`) and exits `1`. For an AI agent, this is a dead end. The agent must re-run the command with `--debug` or issue a new command (`run errors <id>`) to discover why it failed, bloating context windows and risking hallucination.
**Fix**: Update `@handle_cli_errors` to automatically extract and print the detailed JSON `errors` payload from TFCAPIError responses. Additionally, update `run_trigger` and `run_watch` to automatically fetch and print `get_error_summary()` upon terminal run failure before exiting `1`.
**Success Criteria**:
- API failures (e.g. `workspace create` with a duplicate name) explicitly print the `title` and `detail` of the TFC JSON error.
- Wait loops (`run trigger --wait`) automatically print the Terraform error block if the run hits an errored state.

---

### F10 — Context honoring (org/workspace) in run list and run logs
**Context**: During agent sessions, we found that `run list` and `run logs` do not honor the local Terraform context (organization and workspace). This causes friction and forces a fallback to the TFC API (e.g. `tfc-api` or curl) or requiring explicit flags when running commands from inside a terraform directory.
**Fix**: Implement context discovery (similar to `tfc run trigger`) so that `run list` and `run logs` automatically infer `--workspace` and `--org` from the `.terraform` directory or `terraform.tf` files if invoked without explicit flags.
**Success Criteria**:
- `terrapyne run list` executed in a directory with initialized terraform backend prints the runs for the inferred workspace.
