# TODO — Terrapyne Product Backlog

Bugs, gaps, and improvements. Sources:
- Exploratory testing against live TFC
- Product fitness appraisal against TFC API model (April 2026)
- Field use: vault dynamic credentials debugging session (May 2026)
- Field use: workspace provisioning for PAM KV credential test (May 2026)
- Agent friction analysis: pi/gemini/claude conversation logs (May 2026) — patterns where agents corrected commands, fell back to tfc-api curl scripts, or worked around missing features

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
| **BUGS (May 2026)** |
| B7 | `run follow` / `run logs` silent on pre-plan errors — falls back to `"Run failed before generating logs"` with no error text | 🔴 | S | 4.0 | TODO |
| B8 | `run logs` returns empty for errored runs even when log is available via archivist URL | 🔴 | S | 4.0 | TODO |
| B9 | `run list` fails by workspace name for some workspaces — requires workspace ID workaround | 🟡 | S | 2.0 | TODO |
| B10 | `workspace clone` 422 "Agent pool not found" — drops agent-pool relationship from create payload | 🔴 | S | 4.0 | TODO |
| B11 | `workspace create` missing `--project` flag — no way to assign workspace to a project at creation | 🔴 | S | 4.0 | TODO |
| B12 | `workspace list` name truncation — no `--no-truncate` or `--max-width` option | 🟡 | S | 2.0 | TODO |
| B13 | `run trigger` exits non-zero on success — breaks `&&` chains and scripting | 🟡 | S | 2.0 | TODO |
| B14 | `workspace var-rm` no `--yes`/`-y` flag — always prompts interactively, unusable in scripts | 🟡 | S | 2.0 | TODO |
| B15 | `--quiet` flag position-sensitive — `terrapyne workspace list --quiet` fails; must be `terrapyne --quiet workspace list` | 🟢 | S | 1.0 | TODO |
| B16 | `hostname` silently dropped from auto-detected backend — `validate_context` returns org/workspace but discards the hostname; all commands except `workspace clone` default to `app.terraform.io`, breaking private TFE instances | 🔴 | M | 2.0 | TODO |
| B17 | `--hostname` / `TFC_HOSTNAME` missing from most commands — only `workspace clone` has the flag; agents must `export TFC_TOKEN=<token-for-other-host>` and hope the default hostname matches | 🔴 | M | 2.0 | TODO |
| B18 | `run follow` missing `--auto-apply` flag — `run watch` has it but `run follow` does not; agents attempting to stream logs and auto-apply in one step must use two separate commands | 🟡 | S | 2.0 | TODO |
| B19 | Pydantic V2 deprecation warnings on every invocation — `PydanticDeprecatedSince20` for `class-based config` pollutes all output including `--format json`; interferes with scripted JSON parsing | 🟡 | S | 2.0 | TODO |
| B20 | `ImportError: cannot import name 'StateVersionsAPI' from 'terrapyne'` — `StateVersionsAPI` not exported from the package root; breaks SDK users who import directly from `terrapyne` | 🟡 | S | 2.0 | TODO |
| **NEW FEATURES** |
| F4 | Workspace notifications (webhook/Slack config) | 🟡 | M | 1.0 | TODO |
| F5 | Policy sets / Sentinel outcome reporting | 🟡 | M | 1.0 | TODO |
| F6 | Private registry query (modules + providers) | 🟡 | M | 1.0 | TODO |
| F7 | Agent pools — list and show self-hosted agents | 🟡 | M | 1.0 | TODO |
| F8 | SSH keys / VCS OAuth token management | 🟢 | L | 0.33 | TODO |
| F9 | `workspace update` command and API update method | 🔴 | M | 2.0 | TODO |
| F10 | `run cancel` command — agents repeatedly fell back to `curl -X POST .../actions/cancel`; no terrapyne equivalent | 🟡 | S | 2.0 | TODO |
| F11 | Projects API search (`project list --search`) — TFC Projects API does not support `q=` filter; terrapyne must paginate and post-filter client-side (currently undocumented; agents used tfc-api curl scripts instead) | 🟡 | M | 1.0 | TODO |
| F12 | `workspace lock` / `workspace unlock` commands — agents had to fall back to raw curl calls to lock/unlock workspaces before triggering runs | 🟡 | S | 2.0 | TODO |
| F13 | `workspace set-branch <name> <branch>` — agents used `PATCH /workspaces/{id}` with vcs-repo.branch directly; `workspace vcs` exists but doesn't expose branch switching; was the most common single PATCH call seen in sessions | 🔴 | S | 4.0 | TODO |
| F14 | `workspace list --tag <tag>` — agents used `?filter[tagged]=X` to scope workspace lists by tag but terrapyne `workspace list` has no `--tag` filter | 🟡 | S | 2.0 | TODO |
| F15 | `run events <run-id>` — agents used `GET /runs/{id}/run-events` for audit timeline (who triggered, confirmed, cancelled); no terrapyne equivalent; useful for KEDB/incident investigations | 🟡 | S | 2.0 | TODO |
| F16 | `run plan-json <run-id>` — agents used `GET /plans/{id}/json-output` for machine-readable structured plan data; `run parse-plan` handles text but not the structured JSON endpoint | 🟡 | S | 2.0 | TODO |
| F17 | `workspace team-access add/remove` — agents used `POST /team-workspaces` to grant team read/write/admin access to workspaces; no terrapyne equivalent; had to fall back to curl for every workspace provisioning | 🟡 | M | 1.0 | TODO |
| F18 | `team workspaces <team-name>` — agents used `GET /teams/{id}/workspaces` to audit which workspaces a team has access to; `team list` exists but no workspace-access introspection | 🟢 | S | 1.0 | TODO |
| F19 | `registry module list/show/register/delete` — agents used registry API heavily for module status checks and lifecycle (register VCS, delete stale modules); `F6` covers list/show but not register/delete | 🟡 | M | 1.0 | TODO |
| F20 | `workspace consumers` — agents used `GET /workspaces/{id}/relationships/remote-state-consumers` to understand cross-workspace state dependencies; no terrapyne equivalent | 🟢 | S | 1.0 | TODO |
| F21 | `terrapyne ping` / `terrapyne auth` — agents used `GET /account/details` (18× across sessions) to verify token validity and connectivity before starting work; no convenience command; must use curl or inspect a workspace | 🟡 | S | 2.0 | TODO |
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

### B16 — Hostname silently dropped from auto-detected backend

**Context**: Discovered during `workspace costs` use against a private TFE instance (`terraform-amer.takeda.com`). The `terraform.tf` `cloud` / `backend "remote"` block contains a `hostname` field. `validate_context()` returns `(org, workspace)` but drops the hostname entirely. Every command then constructs `TFCClient(organization=org)` with no `host=` argument, defaulting to `app.terraform.io`.

Agents hit this as a confusing authentication failure — the token was valid for the right host, but terrapyne was sending requests to the wrong host:

```
# terraform.tf has: hostname = "terraform-amer.takeda.com"
terrapyne workspace costs  # silently hits app.terraform.io → 401
# Agent workaround:
export TFC_TOKEN=$(jq -r '.credentials."terraform-amer.takeda.com".token' ~/.terraform.d/credentials.tfrc.json)
export TFC_HOSTNAME=terraform-amer.takeda.com
```

**Fix**: `validate_context()` must return a 3-tuple `(org, workspace, hostname)` (or a context dataclass). All commands that call `TFCClient(organization=org)` must pass `host=hostname` when a hostname was detected from the backend config.

**Success Criteria**:
- `workspace costs` / `workspace list` / `run list` etc. hit the correct TFE host when hostname is in `terraform.tf`
- `TFC_HOSTNAME` env var overrides the auto-detected hostname (12-factor)
- Existing behaviour for `app.terraform.io` is unchanged

---

### B17 — `--hostname` / `TFC_HOSTNAME` missing from most commands

**Context**: Only `workspace clone` (line 583 of `workspace_cmd.py`) has an explicit `--hostname` flag. All other commands (list, show, costs, run list, run trigger, etc.) have no way for users to override the TFE endpoint when auto-detection is not available (e.g. running outside a Terraform directory).

Agents in private TFE contexts (`terraform-amer.takeda.com`, `terraform-dev.takeda.com`) had to set `TFC_TOKEN` to the right token and rely on auto-detection, or fall back to tfc-api curl scripts.

**Fix**: Add `--hostname` / `-H` (or `--host`) to the global options, backed by `TFC_HOSTNAME` env var. Pass through to `TFCClient(host=hostname)`. Consistent with how `--organization` is a global option.

**Success Criteria**:
- `terrapyne --hostname terraform-amer.takeda.com workspace list` works
- `TFC_HOSTNAME=terraform-amer.takeda.com terrapyne workspace list` works
- Help text shows both the flag and the env var

---

### B18 — `run follow` missing `--auto-apply` flag

**Context**: `run watch <run-id> --auto-apply` exists and watches an existing run, automatically confirming it when planning completes. `run follow <run-id>` streams logs in real-time but has no `--auto-apply` flag. Agents noticed the gap when looking at `run follow --help` and had to chain two commands:

```bash
terrapyne run follow <run-id>   # stream logs
terrapyne run watch <run-id> --auto-apply  # then apply
```

The user message in the antigravity log reads: _"Looking at `terrapyne run follow --help`, the command signature was just `terrapyne run follow <run-id>` with no visible flags for auto-apply"_ — this was flagged as an improvement to make in a PR.

**Fix**: Add `--auto-apply` and `--comment`/`-m` flags to `run follow`, mirroring `run watch`. After streaming ends in a confirmable state (`cost_estimated` or `planned`), auto-confirm via the apply API.

**Success Criteria**:
- `terrapyne run follow <run-id> --auto-apply` streams logs and confirms the run when the plan completes
- Without `--auto-apply`, existing log-streaming-only behaviour is preserved
- Help text notes the difference from `run watch` (which polls status; `run follow` streams logs then confirms)

---

### B19 — Pydantic V2 deprecation warnings on every invocation

**Context**: All Pydantic models use the old class-based `Config` inner class rather than `model_config = ConfigDict(...)`. This emits `PydanticDeprecatedSince20` warnings on every command invocation, including when piping `--format json` output:

```
PydanticDeprecatedSince20: Support for class-based `config` is deprecated...
terrapyne/models/workspace.py:24: PydanticDeprecatedSince20
terrapyne/models/project.py:13: PydanticDeprecatedSince20
...
```

This corrupts JSON output for scripted consumers and creates noise in agent sessions that makes it harder to see actual errors.

**Affected models**: `workspace.py`, `project.py`, `vcs.py`, `team_access.py`, `plan.py`, `run.py`, `team.py`, `variable.py`, `state_version.py`.

**Fix**: Migrate all models from `class Config: ...` to `model_config = ConfigDict(...)`. This is a mechanical change with no behaviour impact.

**Success Criteria**:
- `terrapyne workspace list 2>&1 | grep Deprecated` returns nothing
- `terrapyne workspace list --format json` produces clean JSON on stdout with no stderr noise
- All existing tests pass

---

### B20 — `StateVersionsAPI` not exported from package root

**Context**: `from terrapyne import StateVersionsAPI` raises `ImportError`. Agents working with the SDK directly hit this when trying to type-hint or use the API class. The class exists at `terrapyne.api.state_versions.StateVersionsAPI` but is not re-exported from `src/terrapyne/__init__.py`.

**Fix**: Add `StateVersionsAPI` to `__init__.py` exports and `__all__`. Review all API manager classes for similar gaps (see also A17).

**Success Criteria**:
- `from terrapyne import StateVersionsAPI` works
- `from terrapyne import StateVersionsAPI, WorkspaceAPI, RunsAPI, ProjectsAPI` all work from the package root

---

### F10 — `run cancel` command

**Context**: Agents repeatedly fell back to raw curl calls when a run needed to be cancelled:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TFC_TOKEN" \
  "$BASE/runs/$RUN_ID/actions/cancel"
```

There is no `terrapyne run cancel <run-id>` command. The `run discard` command only works for unstarted runs (pre-plan); in-progress runs need the `/actions/cancel` endpoint.

**Fix**: Add `run cancel <run-id> [--comment <msg>] [--force]` command. `--force` maps to the `/actions/force-cancel` endpoint for stuck runs.

**Success Criteria**:
- `terrapyne run cancel run-abc123` cancels an in-progress run (planning, applying)
- `terrapyne run cancel run-abc123 --force` force-cancels a stuck run
- Error if run is already in a terminal state
- `run discard` docs clarify it is for pending (not yet planning) runs only

---

### F11 — Projects API client-side search is undocumented

**Context**: The TFC Projects API does not support the `q=` query parameter for fuzzy search. Agents using `terrapyne project list --search <pattern>` did not know whether this was handled server-side or client-side, and in one session fell back to tfc-api curl scripts to paginate manually.

The current implementation strips `*` from wildcard patterns and passes the remainder to `q=`, but does not document this limitation. Partial matches like `q=10234` return false positives for `my-10234-project` (B4, now fixed with fnmatch post-filtering).

**Fix**: Document in `project list --help` that search is client-side post-filtered pagination (not server-side). Add `--limit` awareness: warn or page-limit to avoid fetching thousands of projects for narrow searches.

**Success Criteria**:
- `project list --help` notes that `--search` uses client-side filtering
- Wildcard patterns (`10234-*`, `*-MAN`) are matched using `fnmatch` after fetching
- No silent false positives or missing results

---

### F12 — `workspace lock` / `workspace unlock` commands

**Context**: Agents needing to lock a workspace before triggering a run (to prevent concurrent executions) fell back to curl:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TFC_TOKEN" \
  "$BASE/workspaces/$WS_ID/actions/lock" \
  -d '{"reason": "deploying"}'
```

Terrapyne has no `workspace lock` or `workspace unlock` commands.

**Fix**: Add `workspace lock <name> [--reason <msg>]` and `workspace unlock <name>` commands, wrapping `/workspaces/{id}/actions/lock` and `/actions/unlock`.

**Success Criteria**:
- `terrapyne workspace lock my-ws --reason "CI deploy in progress"` locks the workspace
- `terrapyne workspace unlock my-ws` unlocks it
- Error if workspace is already locked/unlocked
- `workspace show` output includes lock status and who locked it

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

## Agent Curl Fallback Analysis (May 2026)

The following task details are derived from analysing agent session logs where pi/gemini/claude agents
fell back to raw `curl` calls or tfc-api scripts instead of using terrapyne. The tfc-api skill
(`~/.github/skills/tfc-api/`) wraps the most common operations; where agents used it repeatedly,
terrapyne is missing the equivalent.

---

### F13 — `workspace set-branch <name> <branch>`

**Context**: The most frequently observed manual PATCH across all sessions. Agents needed to change the
VCS branch tracked by a workspace (e.g. switching from `main` to a feature branch before triggering a
speculative plan, or pointing a workspace at a release branch). The existing `workspace vcs` shows VCS
config but provides no mutation. The tfc-api skill has a dedicated `set-workspace-branch.sh` for this.

```bash
# What agents did (set-workspace-branch.sh):
WORKSPACE_ID=$(curl ... organizations/$ORG/workspaces/$WS | jq -r .data.id)
curl -X PATCH ... workspaces/$WORKSPACE_ID \
  -d '{"data": {"type": "workspaces", "attributes": {"vcs-repo": {"branch": "feature/123"}}}}'
```

**Fix**: Add `workspace set-branch <workspace> <branch>` (or `workspace update --branch`). This is a
single-field PATCH; it wraps `WorkspaceAPI.update()` once F9 is implemented.

**Success Criteria**:
- `terrapyne workspace set-branch my-ws feature/123` updates the tracked branch
- `terrapyne workspace vcs my-ws` shows the new branch
- Auto-detect workspace from `terraform.tf` if name omitted

---

### F14 — `workspace list --tag <tag>`

**Context**: Agents used tag filters (`?filter[tagged]=platform`) to scope workspace lists to a subset
of workspaces relevant to their task, avoiding noisy org-wide listings with hundreds of results.
Terrapyne's `workspace list` has `--project` and `--search` filters but no `--tag` filter.

```bash
# What agents did:
curl ... "organizations/Takeda/workspaces?filter%5Btagged%5D=platform&page[size]=100"
```

**Fix**: Add `--tag` / `-t` option to `workspace list`. Multiple `--tag` flags should AND the filters
(TFC API supports multiple `filter[tagged]` values). Pass directly to the API as a server-side filter.

**Success Criteria**:
- `terrapyne workspace list --tag platform` returns only tagged workspaces
- `--tag` and `--project` can be combined
- `--format json` output unaffected

---

### F15 — `run events <run-id>`

**Context**: Agents investigating failed runs or auditing who confirmed an apply used
`GET /runs/{id}/run-events` to get a timestamped audit trail (triggered-by, confirmed-by, cancelled-by,
error events). Useful for KEDB write-ups and incident timelines.

```bash
# What agents did:
curl ... "runs/$RUN_ID/run-events" | jq '.data[] | {action: .attributes.action, created: .attributes."created-at", actor: .attributes.actor.name}'
```

**Fix**: Add `run events <run-id>` command. Table output: timestamp, action, actor.

**Success Criteria**:
- `terrapyne run events run-abc123` shows the run event timeline
- `--format json` supported
- `run show` optionally includes events with `--include-events`

---

### F16 — `run plan-json <run-id>`

**Context**: Agents needed structured plan data for programmatic analysis (resource counts by type,
import summaries, change detection). `GET /plans/{id}/json-output` returns the full Terraform plan JSON.
The existing `run parse-plan` works on text plan output but not on the JSON plan endpoint.

```bash
# What agents did:
PLAN_ID=$(curl ... runs/$RUN_ID | jq -r .data.relationships.plan.data.id)
curl -sL ... "plans/$PLAN_ID/json-output" -o plan.json
```

**Fix**: Add `run plan-json <run-id>` command that fetches plan JSON directly from TFC (no local
Terraform binary required). Optionally `--output plan.json` to save to file.

**Success Criteria**:
- `terrapyne run plan-json run-abc123` prints the plan JSON to stdout
- `--output plan.json` saves to file
- Error with helpful message if plan JSON not available (e.g. plan not yet complete)

---

### F17 — `workspace team-access add/list/remove`

**Context**: Every workspace provisioning workflow involved granting team access via
`POST /team-workspaces`. This was always done with curl because terrapyne has no team-workspace
access management. Agents had to look up team IDs, then construct the full JSON API payload.
The `team` command group exists but only covers team membership, not workspace access grants.

```bash
# What agents did (for every new workspace):
curl -X POST ... team-workspaces \
  -d '{"data": {"type": "team-workspaces", "attributes": {"access": "write"},
       "relationships": {"workspace": {"data": {"type": "workspaces", "id": "$WS_ID"}},
                         "team": {"data": {"type": "teams", "id": "$TEAM_ID"}}}}}'
```

**Fix**: Add `workspace team-access` subgroup:
- `workspace team-access list <workspace>` — show teams and their access levels
- `workspace team-access add <workspace> --team <name> --access read|write|admin`
- `workspace team-access remove <workspace> --team <name>`

**Success Criteria**:
- `terrapyne workspace team-access add my-ws --team okta-terraform-devs --access write` grants access
- `terrapyne workspace team-access list my-ws` shows current team grants
- Team resolved by name (lookup internally)

---

### F21 — `terrapyne auth` / `terrapyne ping`

**Context**: `GET /account/details` was called 18× across sessions — more than almost any other
endpoint. Agents used it as a connectivity and token validity check before starting any substantive
work: _"verify TFC token and access"_. Currently this requires either `curl` or `make tfc-token-check`.
There is no `terrapyne auth` or `terrapyne ping` command.

**Fix**: Add `terrapyne auth` (or `terrapyne ping`) that calls `GET /account/details` and prints the
authenticated username, token scope, and org memberships. Exit non-zero on auth failure.

**Success Criteria**:
- `terrapyne auth` prints: `Authenticated as: shalom.bhooshi@example.com (org: Takeda)`
- Non-zero exit + clear error message on 401/403
- `--format json` outputs full account details
- Useful as a pre-flight check in scripts: `terrapyne auth && terrapyne run trigger my-ws`
