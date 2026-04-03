# Terrapyne — Code Review Feedback

> Generated: 2026-04-03  
> Reviewer: pi coding agent  
> Branch assessed: `main` (HEAD `22f85d0`)

---

## Summary

Terrapyne is a well-structured Python TFC API client and CLI. The architecture is clean, the
tooling is solid, and the feature set is genuinely useful. The blocking issue for CI is a
coverage gap (64% vs 80% threshold). Several housekeeping items also need attention.

---

## Test Suite

**283 pass, 1 skip. Suite is green — but exits with ERROR due to coverage.**

```
FAIL Required test coverage of 80% not reached. Total coverage: 64.17%
```

### Low-coverage modules

| Module | Coverage | Issue |
|---|---|---|
| `api/state_versions.py` | **0%** | No unit tests at all |
| `api/workspace_clone.py` | **15%** | Clone logic untested |
| `cli/run_cmd.py` | **14%** | Most subcommands have no mocked tests |
| `cli/state_cmd.py` | **16%** | New module, barely touched |
| `cli/workspace_cmd.py` | **18%** | Most commands uncovered |
| `api/client.py` | **29%** | HTTP methods not exercised in unit tests |
| `core/plan_parser.py` | **16%** | Rich parser, sparse coverage |
| `core/state_diff.py` | **31%** | Diff engine missing scenarios |
| `utils/browser.py` | **28%** | URL-open logic untested |

**Recommendation**: Add `pytest-httpx` mocked unit tests for the API modules and CLI
commands. `api/state_versions.py` at 0% is the easiest win — it has a clear contract.

---

## Code Issues

### 1. Pydantic V2 deprecation warning (non-fatal, will break in V3)

`src/terrapyne/models/state_version.py:22` uses V1-style `class Config`:

```python
# Current (deprecated)
class StateVersion(BaseModel):
    class Config:
        ...

# Fix
from pydantic import ConfigDict
class StateVersion(BaseModel):
    model_config = ConfigDict(...)
```

### 2. Stale `utils.py` at 0% coverage

`src/terrapyne/utils.py` (flat file) sits alongside `src/terrapyne/utils/` (package).
The flat file is at 0% coverage — likely dead code from a pre-package-refactor era.
Audit and remove or fold into `utils/__init__.py`.

### 3. `pyproject.toml` classifier/license mismatch

```toml
# license field says:
license = { text = "Apache License Version 2.0" }

# but classifiers say:
"License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)"
```

One of these is wrong. Decide and make them consistent.

### 4. Development status classifier overstated

```toml
# Current
"Development Status :: 5 - Production/Stable"

# Should be (for v0.0.1 at 64% coverage)
"Development Status :: 3 - Alpha"
```

---

## Repository Hygiene

### 5. `build/` directory tracked in git

The `build/` artefact directory appears in the repo tree. Add to `.gitignore`:

```gitignore
build/
dist/
*.egg-info/
.ipynb_checkpoints/
```

### 6. Jupyter checkpoint in source

`src/terrapyne/.ipynb_checkpoints/utils-checkpoint.py` is tracked. Remove it and add
`.ipynb_checkpoints/` to `.gitignore`.

---

## Strengths

- Clean layered architecture: `api/` → `models/` → `cli/` — no circular dependencies
- Context auto-detection (reads `terraform.tf` / `.terraform/` for org + workspace) is slick
- `TFCClient` retry/pagination via tenacity is solid and well-tested in isolation
- Plan parser uses Strategy + State Machine patterns cleanly — handles ANSI stripping,
  error boxes, multi-action resources, GitLab CI format
- BDD tests (pytest-bdd) give the CLI commands readable acceptance-level coverage
- `ruff` + `mypy` + `pre-commit` tooling is properly configured

---

## Priority Order

1. **Coverage** — get to 80%: start with `api/state_versions.py` (0%), then CLI commands
2. **Pydantic deprecation** — fix `StateVersion.Config` → `ConfigDict`
3. **`.gitignore`** — exclude `build/`, `*.egg-info/`, `.ipynb_checkpoints/`
4. **Remove stale `utils.py`** — or document why it coexists with `utils/`
5. **Fix `pyproject.toml`** — align license field + classifier, drop Production/Stable status

---

## CLI Live Assessment

> Tested against: `Takeda` org, workspace `tec-man-qua-dev-93126-empower-qc`  
> Test environment: inside `iac/dev/` (`.terraform/terraform.tfstate` present)

---

### Context Auto-Detection

Context is resolved from `.terraform/terraform.tfstate` first, then `terraform.tf` as
fallback. From **outside** a terraform directory, all commands fail with a clear, actionable
error message — correct behaviour.

From **inside** `iac/dev/`, results are mixed:

| Command | No-arg result | Root cause |
|---|---|---|
| `tfc workspace health` | ✅ auto-detects | Uses resolved value correctly |
| `tfc run list` | ✅ auto-detects | Uses resolved value correctly |
| `tfc state inventory` | ✅ auto-detects | Uses resolved value correctly |
| `tfc run errors` | ✅ auto-detects org | Uses resolved value correctly |
| `tfc workspace show` | ❌ crashes | Bug: resolved ws discarded |
| `tfc workspace variables` | ❌ crashes | Bug: resolved ws discarded |
| `tfc workspace vcs` | ❌ crashes | Bug: resolved ws discarded |
| `tfc workspace health` (with arg) | ✅ works | Raw arg is non-None so bypass |

#### The Bug — `org, _ = validate_context(...)` (4 locations in `workspace_cmd.py`)

`validate_context` resolves the workspace name and returns it as the second tuple element,
but these four commands assign it to `_` (discarding it), then fall back to the raw CLI arg
which is still `None`:

```python
# workspace_cmd.py lines 98, 141, 196, 262 — broken pattern
org, _ = validate_context(organization, workspace, require_workspace=True)
ws = client.workspaces.get(workspace or "")  # passes "" → API returns list → crash

# Correct pattern (used by run_cmd.py and state_cmd.py)
org, ws_name = validate_context(organization, workspace, require_workspace=True)
ws = client.workspaces.get(ws_name)  # ✅
```

**Fix**: Change `_` → `ws_name` at lines 98, 141, 196, 262 and use `ws_name` in the
subsequent `.get()` call in each function. Two-character fix per site.

---

### Help Screen vs Implementation Coverage

All registered commands appear in their group's `--help` output — nothing is hidden.
However, several gaps exist between what the help advertises and what actually works or
is implemented:

#### `tfc debug` — fully stubbed, advertised as real

```
tfc debug run        → "Coming soon: Run failure diagnostics (Priority 4)"
tfc debug workspace  → "Coming soon: Workspace health checks (Priority 4)"
```

Both commands are listed in `tfc debug --help` with no indication they are stubs.
A user running `tfc debug run` gets a yellow "coming soon" message and exit 0 — no error,
no help text suggesting an alternative. Either implement or mark clearly as `[PLANNED]`
in the help string, and exit non-zero.

#### `tfc run logs` — missing `--organization` / `-o` flag

`run logs` constructs its `TFCClient()` with no organisation argument and has no `-o`
option — the only command in the CLI that doesn't follow the pattern. Works when called
from inside a terraform directory (credentials inferred), but fails from outside with a
cryptic error rather than "specify --organization".

#### `tfc run logs` — plan log 404 on errored runs

The `/plans/{plan_id}/logs` endpoint returns 404 for plans that errored before completing.
The command surfaces the raw httpx `404` traceback instead of a user-friendly message
(e.g., "Plan logs unavailable — run may have errored before plan completed").

#### `tfc workspace list --project` — option silently ignored

`--project` accepts a name string but `WorkspaceAPI.list()` filters by `project_id`.
The CLI layer never resolves the name to an ID — `project_id` is always `None` in the
API call. The option is advertised but has no effect.

#### `tfc state list` — HTTP 400 crash

Crashes with a full tenacity retry traceback. The TFC API `/state-versions` endpoint
requires `filter[organization][name]` alongside `filter[workspace][id]`, but the API
client only sends the workspace ID. Retries 3× (with exponential backoff) before
failing — meaning a user waits ~6 seconds before seeing an error.

#### `tfc state diff` — silently aborts

Exits with no output and no error message. Likely caused by the same `state list` 400
underneath — but the error is swallowed rather than surfaced.

#### `tfc run list` — Run IDs truncated in output

Run IDs are truncated with `…` in the table (e.g., `run-JJpgJdhM5…`). This makes `tfc
run show <id>` and `tfc run logs <id>` unusable with copy-pasted output from `tfc run
list` — the truncated ID produces a 404. The `Run ID` column needs a fixed minimum
width or the table needs `no_wrap=True` on that column.

---

### API Layer vs CLI Coverage

Several API methods have no CLI surface:

| API method | Notes |
|---|---|
| `TeamsAPI.set_project_access()` | No CLI command — useful for IaC team onboarding |
| `TeamsAPI.compare_project_access()` | No CLI command |
| `TeamsAPI.get_project_access()` | No CLI command |
| `WorkspaceAPI.create_variable()` | Exposed via `var-set` only in bulk mode; no single-var create |
| `WorkspaceAPI.update_variable()` | No direct CLI command (only via `var-set` overwrite) |
| `RunsAPI.poll_until_complete()` | Used internally by `run watch`; not directly addressable |
| `StateVersionsAPI.find_version_before()` | Used internally by `state diff`; not exposed directly |

---

### What Works Well

- `tfc workspace health` — excellent single-command workspace overview, renders cleanly
- `tfc run list --status errored` — filters correctly, useful for triage
- `tfc run errors --project <name>` — scoped error mining works well when project name
  matches exactly; returns clean table with workspace, run ID, age, message
- `tfc state inventory` — rich output, filtering by `--type`, `--module`, `--format` all
  work; JSON output is pipeable
- `tfc project show` — shows workspace list with environment/version/branch at a glance
- `tfc run show` — clean detail view with resource change counts and deep-link URL
- Auto-detection error messages (when outside a terraform dir) are clear and actionable

---

### Updated Priority Order

1. **`workspace show` / `variables` / `vcs` context bug** — `_` → `ws_name` in 4 places
2. **Run ID truncation** — add `min_width` or `no_wrap` to Run ID column in table renderer
3. **`state list` HTTP 400** — add `filter[organization][name]` to state versions API call
4. **`run logs` missing `-o` flag** — align with every other command's option set
5. **`run logs` 404 on errored runs** — catch 404, emit friendly message
6. **`workspace list --project` silently ignored** — resolve name → ID via `ProjectAPI`
7. **`debug` stubs** — mark as `[PLANNED]` in help text, exit non-zero
8. **Coverage** — get to 80%: `api/state_versions.py` (0%) first
9. **Pydantic deprecation** — `StateVersion.Config` → `ConfigDict`
10. **`.gitignore` / `pyproject.toml` housekeeping**

---

## Proposed CLI Interface

A ground-up redesign of the command surface, based on full API layer review.

### Design principles

1. **No phantom commands** — nothing in `--help` that isn't implemented; stubs removed
2. **Consistent global options** — `--org`/`-o`, `--workspace`/`-w`, `--format`/`-f`,
   `--limit`/`-n` present on every command where they apply
3. **Auto-detection is silent and reliable** — all workspace-scoped commands resolve
   org + workspace from context; explicit args always override
4. **Resolved value always used** — `validate_context()` return captured, never discarded
5. **IDs never truncated** — Run ID / workspace ID / state version ID columns use
   `no_wrap=True`; copy-paste from any list output must work as input to a show command
6. **Read vs write clarity** — mutating commands require `--yes`/`-y` to confirm
7. **Bounded by default** — `run errors` requires at least one scope flag; no unbounded
   org-wide scans
8. **API surface parity** — every implemented API method has a CLI verb

---

### `tfc workspace`

```
tfc workspace list
    [-o ORG] [-p PROJECT_NAME] [-s SEARCH] [-n LIMIT] [--format table|json|csv]
    List workspaces. --project resolved from name to ID via ProjectAPI (currently ignored).

tfc workspace show [WORKSPACE]
    [-o ORG] [--format table|json]
    Show metadata, VCS, variables, last run. Auto-detects WORKSPACE from context.

tfc workspace health [WORKSPACE]
    [-o ORG]
    Lock state, last run status, VCS branch, variable count, tags.

tfc workspace variables [WORKSPACE]
    [-o ORG] [--category terraform|env|all] [--format table|json]
    List variables. Sensitive values shown as [SENSITIVE].

tfc workspace vcs [WORKSPACE]
    [-o ORG]
    Show VCS repo, branch, oauth token ID, working directory.

tfc workspace open [WORKSPACE]
    [-o ORG]
    Open workspace URL in browser.

tfc workspace clone SOURCE TARGET
    [-o ORG] [--with-variables] [--with-vcs] [--vcs-oauth-token-id ID] [--yes]
    Clone settings (and optionally variables + VCS) to a new workspace.

tfc workspace var-set [WORKSPACE] KEY=VALUE [KEY=VALUE ...]
    [-o ORG] [--category terraform|env] [--sensitive] [--hcl]
    [--description TEXT] [--yes]
    Create or update one or more workspace variables.

tfc workspace var-copy SOURCE TARGET
    [-o ORG] [--yes]
    Copy all variables from SOURCE to TARGET workspace.
```

---

### `tfc run`

```
tfc run list [WORKSPACE]
    [-o ORG] [-s STATUS] [-n LIMIT] [--format table|json]
    List runs. Run IDs always full-width — no truncation.
    STATUS: pending|planning|planned|applying|applied|errored|canceled|discarded

tfc run show RUN_ID
    [-o ORG] [--format table|json]
    Detail view: status, changes (+N ~N -N), timings, target/replace addrs, deep-link URL.

tfc run logs RUN_ID
    [-o ORG] [--type plan|apply]
    Stream plan or apply logs to stdout.
    On 404: friendly message ("Plan logs unavailable — run may have errored early")
    rather than raw traceback. Currently missing -o flag.

tfc run plan [WORKSPACE]
    [-o ORG] [-m MESSAGE] [--wait/--no-wait]
    Create a plan-only run. Polls to terminal if --wait (default).

tfc run trigger [WORKSPACE]
    [-o ORG] [-m MESSAGE] [-t TARGET_ADDR ...] [-r REPLACE_ADDR ...]
    [--refresh-only] [--destroy] [--auto-apply] [--watch] [--yes]
    Trigger a run with optional targeting or replacement.
    --destroy and --auto-apply require --yes.

tfc run apply RUN_ID
    [-o ORG] [-m COMMENT] [--wait/--no-wait] [--yes]
    Apply a planned run. Requires --yes.

tfc run watch RUN_ID
    [-o ORG]
    Poll until terminal state, printing status transitions.

tfc run errors
    [-o ORG] [-p PROJECT_NAME] [-w WORKSPACE] [-d DAYS] [-n LIMIT]
    [--format table|json]
    Find errored runs. Requires at least one of --project, --workspace,
    or --days ≤ 7 — never scans the whole org unbounded.

tfc run parse-plan [FILE|-]
    Read plain-text plan output from FILE or stdin (-) and emit
    PlanInspector-compatible JSON. Enables: terraform plan 2>&1 | tfc run parse-plan -
```

---

### `tfc state`

```
tfc state list [WORKSPACE]
    [-o ORG] [-n LIMIT] [--format table|json]
    List state versions, most recent first.
    Fix: must pass filter[organization][name] + filter[workspace][name] — not workspace ID.

tfc state show STATE_VERSION_ID
    [-o ORG]
    Metadata for a specific state version.

tfc state pull [WORKSPACE]
    [-o ORG] [--version STATE_VERSION_ID]
    Download state JSON to stdout (like terraform state pull). Defaults to latest.

tfc state outputs [WORKSPACE]
    [-o ORG] [--version STATE_VERSION_ID] [--format table|json]
    List output values. Sensitive outputs shown as [SENSITIVE].

tfc state inventory [WORKSPACE]
    [-o ORG] [--version STATE_VERSION_ID]
    [--type TYPE,...] [--module PATH] [--mode managed|data]
    [--fields type,name,id,arn,...] [--format table|markdown|json]
    Resource inventory. Supports dotted field paths (e.g. tags.Name).

tfc state diff [WORKSPACE]
    [-o ORG] --since YYYY-MM-DD
    [--type TYPE,...] [--module PATH] [--mode managed|data]
    [--fields FIELDS] [--format table|markdown|json|diff] [--diff-cmd CMD]
    Resources added/removed between a past state version and now.
    Currently silently aborts — fix: surface the underlying 400.
```

---

### `tfc project`

```
tfc project list
    [-o ORG] [-s SEARCH] [-n LIMIT] [--format table|json]

tfc project show PROJECT_NAME
    [-o ORG]
    Metadata plus workspace list with environment/version/branch.

tfc project find PATTERN
    [-o ORG]
    Substring/wildcard match (e.g. "93*-MAN").

tfc project teams PROJECT_NAME
    [-o ORG]
    Teams with access to a project and their access levels.
```

---

### `tfc team`

```
tfc team list
    [-o ORG] [-s SEARCH] [-n LIMIT] [--format table|json]

tfc team show TEAM_NAME
    [-o ORG]
    Metadata, member count, project access levels.

tfc team members TEAM_NAME
    [-o ORG]
    List members.

tfc team access TEAM_NAME              ← NEW (surfaces TeamsAPI.get_project_access)
    [-o ORG] [-p PROJECT_NAME]
    Show this team's access level on a project (or all projects if -p omitted).

tfc team access-compare TEAM_A TEAM_B  ← NEW (surfaces TeamsAPI.compare_project_access)
    [-o ORG] [--project-a PROJECT_A] [--project-b PROJECT_B]
    Compare access permissions between two teams field-by-field.

tfc team create TEAM_NAME    [-o ORG] [--description TEXT] [--yes]
tfc team update TEAM_NAME    [-o ORG] [--description TEXT] [--yes]
tfc team delete TEAM_NAME    [-o ORG] [--yes]
tfc team add-member    TEAM USER  [-o ORG] [--yes]
tfc team remove-member TEAM USER  [-o ORG] [--yes]
    All mutating commands require --yes.
```

---

### `tfc vcs`

```
tfc vcs show [WORKSPACE]
    [-o ORG]
    VCS repo, branch, oauth token, working directory.

tfc vcs repos
    [-o ORG]
    All GitHub repos connected to workspaces in the org, with workspace list per repo.

tfc vcs set-branch [WORKSPACE] BRANCH   ← renamed from update-branch
    [-o ORG] [--oauth-token-id TOKEN_ID] [--yes]
    Update tracked VCS branch. Requires --yes.
    Renamed for consistency with var-set naming pattern.
```

---

### Removed

```
tfc debug run        REMOVED — stub only, "coming soon" message, exit 0
tfc debug workspace  REMOVED — stub only, "coming soon" message, exit 0
```

Functionality intended for `debug` either already exists (`tfc workspace health`,
`tfc run errors`) or should be implemented properly before being advertised.

---

---

## Plan Parser Assessment

### The parser itself: solid

Tested against 30 real-world plan fixtures from the authoritative test suite
(`terraform-aws-RDS/examples/import/src/framework/parsers/tests/fixtures/`).
All 30 produce valid JSON when output goes to a file (`--output`):

```
Result: 30 pass, 0 fail out of 30 fixtures
```

Handles: ANSI codes (TFC + GitLab CI formats), module addresses, indexed resources,
tainted resources, import operations, RDS tag maps, mixed JSON+plain-text TFC logs,
Windows line endings, validation errors, missing start/end markers.

### Critical bug: `--format json` to stdout produces invalid JSON

`run_parse_plan` builds the JSON correctly with `json.dumps(result, indent=2)` but
then passes it to `console.print(output_text)`. Rich's console interprets the string
content — embedded `\n` characters in multi-line attribute values (tags, arrays, maps)
become literal control characters in the output stream, breaking JSON parsers:

```
# Broken — Rich mangles the string
console.print(output_text)   # ❌ invalid JSON at stdout

# Fix — bypass Rich for machine-readable output
print(output_text)           # ✅ clean JSON
# or: sys.stdout.write(output_text + "\n")
```

Workaround: `--output file.json` writes via Python's file I/O, bypasses Rich entirely,
produces valid JSON. So `tfc run parse-plan plan.txt --format json --output -` (stdout
as `-`) would be a clean solution once stdin support is added.

**Affected**: any fixture containing multi-line values — tags, arrays, maps (~50% of
real-world plans). Error message: `json.JSONDecodeError: Invalid control character`.

### TFC 1.12+ structured log format: not parsed

Terraform Cloud 1.12+ emits pure JSON structured logs (`@level`, `@message`, `type`
fields) — no plain-text `"Terraform will perform the following actions:"` section.
The parser finds 0 `resource_changes` from these logs (correctly returns empty list
rather than crashing), and extracts the plan summary from the JSON `change_summary`
message. So it degrades gracefully but silently — a user piping TFC 1.12+ logs gets
an empty resource list with no explanation.

```json
// What the parser returns for a TFC 1.12+ log with 7 adds:
{ "resource_changes": [], "plan_summary": {"add": 7, ...}, "plan_status": "incomplete" }
```

The `plan_status: "incomplete"` is a hint, but the human output says
`📊 Resources: No changes` which is misleading.

**Recommendation**: detect structured JSON log format at the start of `parse_to_ir()`
and emit a clear warning: `"Note: TFC structured log format detected — resource-level
parsing not available. Plan summary extracted from JSON metadata only."`

### The parser has only 4 unit tests in terrapyne

The authoritative version (in `terraform-aws-RDS`) has 200+ test cases across unit and
BDD suites against 30 fixtures. Terrapyne's `tests/unit/test_plan_parser.py` has 4.
The 30-fixture suite should be imported wholesale.

### `run parse-plan` missing stdin support

Currently requires a `PATH` argument — no `-` for stdin. This breaks the natural
pipeline: `terraform plan 2>&1 | tfc run parse-plan -`. Adding stdin support is
straightforward with `typer.Argument` + `sys.stdin` fallback.

---

### Delta summary

| Area | Current | Proposed |
|---|---|---|
| Context resolution bug | `org, _` discards resolved ws | `org, ws_name` used downstream |
| Run ID column | truncated with `…` | `no_wrap=True`, always full |
| `run logs` | no `-o` flag | consistent `-o ORG` |
| `run logs` 404 | raw traceback | friendly message + exit 1 |
| `workspace list --project` | silently ignored | resolves name → ID via `ProjectAPI` |
| `run errors` unscoped | scans entire org | requires `--project`/`--workspace`/`--days ≤ 7` |
| `debug` group | two stubs, exit 0 | removed entirely |
| `team access` | no CLI verb | `tfc team access` + `tfc team access-compare` |
| `state list` | HTTP 400 crash | passes `filter[organization][name]` correctly |
| `state diff` | silently aborts | surfaces underlying error |
| `run parse-plan` | file arg only | also accepts `-` for stdin |
| `vcs update-branch` | inconsistent naming | `vcs set-branch` |
| Mutating commands | no confirmation guard | all require `--yes`/`-y` |
