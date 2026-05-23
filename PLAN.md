# PLAN.md — Terrapyne Product Plan

> **Intent Layer.** This file is owned by Marge (Product Agent). Each epic captures the *Why* and *What*. Implementation tasks live in `TODO.md` (the operational backlog) and individual `.feature` files under `tests/features/` (the executable BDD specifications).

## How this file works

- **PLAN.md** = epics + feature briefs (durable, stakeholder-readable, *why this matters*).
- **TODO.md** = WSJF-ranked, sized, status-tracked task backlog (*what to do next*).
- **tests/features/*.feature** = executable acceptance criteria (*proof we built the right thing*).
- **`td`** = ephemeral epic/task IDs once initialised (`td init && td epic create ...`).

Each epic has an ID `EPIC-XXX` that maps 1:1 to a `td` epic ID once registered. Feature scenarios in `.feature` files cite their `EPIC-XXX` in tags so traceability is preserved without tooling.

---

## Epic index

| ID         | Title                                                | Track            | Priority | Status |
| ---------- | ---------------------------------------------------- | ---------------- | -------- | ------ |
| EPIC-001   | Restore Test-Suite Repeatability                     | Quality / TDD    | P0       | Draft  |
| EPIC-002   | Honour the Documented Automation Contract            | Agent Experience | P0       | Draft  |
| EPIC-003   | Structured Output for Mutating Commands              | Agent Experience | P0       | Draft  |
| EPIC-004   | Frictionless Scripting & Non-Interactive Use         | Scripting        | P1       | Draft  |
| EPIC-005   | Pagination Honesty in the SDK                        | SDK Correctness  | P1       | Draft  |
| EPIC-006   | Decompose CLI Command Modules                        | Maintainability  | P2       | Draft  |
| EPIC-007   | Push Orchestration from CLI into the SDK             | Architecture     | P2       | Draft  |
| EPIC-008   | OpenTofu Support in `terrapyne.local`                | Platform Reach   | P1       | Draft  |
| EPIC-009   | Async TFCClient                                      | Platform Reach   | P3       | Parked |
| EPIC-010   | Plugin Model for Custom Command Groups               | Platform Reach   | P3       | Parked |

Priority legend: **P0** = blocks trust in the product; **P1** = visible user pain; **P2** = compounds into pain over time; **P3** = future-looking.

---

## EPIC-001 — Restore Test-Suite Repeatability

**td:** *(unregistered)*  •  **Track:** Quality / TDD  •  **Priority:** P0

### Problem Statement

The test suite reports 815 passing under `make test-all`, but running subsets (e.g. `pytest tests/test_cli/`) produces 32+ failures, and at least one test ordering causes pytest to hang. The cause is module-level mutable state on the shared Rich `console` singleton (`console.quiet`, `console._force_terminal`, `console.no_color`) that tests mutate but never reset. A separate, latent issue: a BDD step in `test_run_commands.py` patches `terrapyne.cli.utils.validate_context`, but `cli/utils.py` is a deprecated stub — the patch silently no-ops, the real `validate_context` is called, and credential resolution is attempted against the live filesystem.

### User Value

The CI build is a lie if the suite isn't repeatable. Contributors waste hours chasing phantom failures that depend on test order. New BDD authors hit failures that have nothing to do with their changes. Once Repeatable is restored, every other quality signal (coverage, Farley index, Adzic index) becomes trustworthy.

### Success Metrics

- `pytest tests/` passes in any subset and any order (verified with shuffled execution and individual file runs).
- `pytest -p pytest_randomly` is added to the inner-loop test ladder; suite remains green across N=10 random orderings.
- `make test-fast` time stays under 10 seconds.
- Zero broken `patch()` targets in the test tree (verified by a small grep-based lint).

### Unknowns

- Whether other shared singletons (logger handlers, `os.environ` mutations from `setup_logging`) leak across tests in addition to the console.
- Whether re-using `pytest-xdist` (already in dev deps) would surface additional ordering bugs.

### Risks

- Adding an `autouse` reset fixture could mask intentional console state in tests that *want* to assert on it. Mitigation: the fixture restores prior values rather than forcing defaults.

### Out of Scope

- Refactoring the Rich console singletons themselves (deferred to EPIC-006/EPIC-007).
- Adding pytest-randomly to dev deps in this epic; do that as a follow-up after the autouse fixture is in.

### Acceptance Criteria — `tests/features/test_repeatability.feature` *(to author)*

```gherkin
Feature: Test suite is repeatable across orderings
  As a contributor
  I want the test suite to pass regardless of execution order
  So I can trust CI signals and onboard new tests safely

  Scenario: Running individual test files in isolation passes
    Given any single test file under tests/
    When that file is invoked alone via pytest
    Then it passes with the same outcome as in the full-suite run

  Scenario: Running the suite under randomised ordering passes
    Given the full test suite
    When pytest is invoked with a randomised order seed
    Then the suite passes for ten consecutive runs

  Scenario: A test that mutates the shared console does not leak
    Given a test that sets console.quiet to True
    When the test completes
    Then the next test observes console.quiet at its prior value
```

---

## EPIC-002 — Honour the Documented Automation Contract

**td:** *(unregistered)*  •  **Track:** Agent Experience  •  **Priority:** P0

### Problem Statement

`docs/explanation/design-philosophy.md` makes five explicit promises about CLI behaviour:

1. Output guides the next action.
2. **stdout for data, stderr for everything else.**
3. Structured output is a contract, not a convenience.
4. Errors are actionable.
5. No interactive requirements (every prompt has a non-interactive bypass).

Items 2 and 3 are partially broken today. The single greatest violation: `tfc workspace list -o nonexistent --format json 2>/dev/null` writes the human-readable error to **stdout**, polluting the JSON stream. `error_console = Console(file=stderr)` exists in `rendering/logging.py` but is used by only one CLI module (`state_cmd.py`); 220 `console.print()` call sites across 12 CLI files write all UX (errors, warnings, progress) to stdout.

### User Value

When the contract holds, `tfc anything --format json | jq` Just Works — and that's the foundation every CI script, agent toolchain, and pipe-based automation depends on. When it doesn't, every consumer has to wrap calls in error-stripping logic, defeating the purpose of having `--format json` at all.

### Success Metrics

- `tfc <any-read-command> --format json 2>/dev/null` produces valid JSON in every error scenario.
- `tfc <any-read-command> --format json >/dev/null` shows all human messages on stderr.
- Adding a regression test that pipes JSON output to `jq` for every read command and expects exit code 0.
- A linting rule (or audit script) flags `console.print(` for messages that contain `[red]Error` or `[yellow]Warning`.

### Unknowns

- Whether to introduce a thin `ux.warn()` / `ux.error()` / `ux.progress()` helper layer or migrate every call site directly. Lisa to decide.
- Whether to also redirect *progress spinners* (currently absent) to stderr by convention.

### Risks

- A wide refactor risks regression. Mitigation: drive it from a generated audit list, file by file, with the test suite as guardrail (after EPIC-001 is fixed).

### Out of Scope

- Introducing the `ux` helper module — that's a Lisa-track design decision.
- Adding `--format json` to mutations (covered by EPIC-003).

### Acceptance Criteria — `tests/features/stdout_stderr_separation.feature` *(to author)*

```gherkin
Feature: stdout carries data, stderr carries human text
  As an automation author
  I want clean separation between machine output and human output
  So that piping JSON to jq always works, even on errors

  Scenario: A successful read command writes JSON to stdout only
    Given a command that supports --format json
    When the command runs successfully
    Then stdout contains valid JSON
    And stderr is empty or contains only progress messages

  Scenario: A failing read command emits error text to stderr
    Given an organization name that does not exist
    When I run "tfc workspace list -o ghost --format json"
    Then stdout is either empty or contains valid JSON
    And stderr contains the human-readable error
    And the exit code is non-zero

  Scenario: Progress messages do not contaminate JSON output
    Given a command that prints progress hints in TTY mode
    When stdout is redirected to a file and --format json is used
    Then the file contains exactly one valid JSON document
```

---

## EPIC-003 — Structured Output for Mutating Commands

**td:** *(unregistered)*  •  **Track:** Agent Experience  •  **Priority:** P0

### Problem Statement

The design philosophy commits to `--format json` on every command, "including mutations". Today, `emit_json` is called from 19 sites — all on read paths. `workspace create`, `workspace clone`, `workspace update`, `workspace delete`, `run trigger`, `run apply`, `run discard`, `run cancel`, `var set`, `var remove`, `var copy`, `varset apply`, `team create`, `team add-member`, and others have no JSON output at all. The result: agents and CI scripts cannot chain mutations:

```bash
WS_ID=$(tfc workspace create app-staging --format json | jq -r '.id')   # Today: parses ANSI human text
tfc run trigger -w app-staging --format json | jq -r '.run_id'           # Today: empty
```

### User Value

Pipelines, GitOps bots, and AI agents stop needing fragile screen-scraping. The "Output guides the next action" principle becomes real: a mutation tells the caller exactly what was created and what to do next.

### Success Metrics

- Every mutating command supports `--format json`.
- The JSON envelope is consistent across mutations:
  ```json
  {
    "id": "ws-abc123",
    "type": "workspace",
    "name": "app-staging",
    "url": "https://app.terraform.io/app/my-org/workspaces/app-staging",
    "next_actions": ["tfc run trigger -w app-staging"]
  }
  ```
- BDD coverage: one scenario per mutation verifies the JSON envelope shape.

### Unknowns

- Final shape of the JSON envelope (single `{"data": {...}}` wrapper, or flat?). Marge proposes flat with `id` + `type` always present; Lisa to validate.
- Whether `next_actions` is an array of strings (commands) or structured objects (`{"command": "...", "description": "..."}`). Strings are simplest; objects degrade gracefully if requirements grow.

### Risks

- Inconsistent envelopes across mutations would defeat the purpose. Mitigation: introduce a tiny `emit_mutation_result()` helper that all commands use.
- Backwards compatibility: human-output should still work for terminal users. Verify with `--format table` (default) tests on every mutation.

### Out of Scope

- Idempotence flags (`--ignore-exists`, `--auto-approve`) — covered by EPIC-004.
- Universal ID resolver (`tfc workspace use NAME` semantics) — TODO.md AX1, deferred.

### Acceptance Criteria — `tests/features/mutation_json_output.feature` *(to author)*

```gherkin
Feature: Mutations emit machine-readable output
  As an agent or pipeline
  I want JSON output from create/update/delete/trigger commands
  So I can chain operations without parsing human text

  Scenario Outline: A successful mutation emits a JSON envelope
    Given the appropriate target resource exists or does not exist
    When I run "<command> --format json"
    Then stdout contains a JSON object with keys "id", "type", "url"
    And the JSON contains a "next_actions" array with at least one suggestion

    Examples:
      | command                                     |
      | tfc workspace create app-staging            |
      | tfc workspace clone src --new-name dst      |
      | tfc workspace update app-staging --tf-version 1.9.0 |
      | tfc run trigger -w app-staging              |
      | tfc workspace var set -w app-staging --key region --value eu-west-1 |

  Scenario: A failing mutation still emits structured error JSON
    Given a workspace name that already exists
    When I run "tfc workspace create app-staging --format json"
    Then stderr contains the error message
    And stdout contains a JSON object with key "error"
    And the exit code is non-zero
```

---

## EPIC-004 — Frictionless Scripting & Non-Interactive Use

**td:** *(unregistered)*  •  **Track:** Scripting  •  **Priority:** P1

### Problem Statement

A handful of small bugs make `tfc` unfit for unattended scripts:

- **B13**: `run trigger` exits non-zero on success, breaking `&&` chains.
- **B14**: `workspace var-rm` always prompts; no `--yes`/`-y`. Unusable in CI.
- **B15**: `--quiet` is position-sensitive — `tfc workspace list --quiet` fails; only `tfc --quiet workspace list` works. Every shell user types it the wrong way at least once.
- **B12**: `workspace list` truncates names; no `--no-truncate` or `--max-width`. Output isn't deterministic for downstream tools.
- **B9**: `run list -w <name>` fails for some workspaces — must use workspace ID.

Each bug individually is small; collectively they signal "not built for scripts."

### User Value

Engineers stop reaching for the TFC web UI for "just one quick thing in a script." Confidence in CI grows. Onboarding new engineers becomes faster (no tribal knowledge about flag positions).

### Success Metrics

- Every flag works in any position (root or sub-app).
- Every interactive prompt has a non-interactive bypass (`--yes` / `--auto-approve`).
- `run trigger` exits 0 on success.
- `tfc workspace list --no-truncate --format table` produces stable, deterministic output.
- `tfc run list -w <name>` works for any workspace name.

### Unknowns

- Root cause of B9 (workspace name lookup): may be a TFC API quirk vs name normalisation in `WorkspaceAPI.get`. Investigation task before implementation.
- Whether `--quiet` should propagate via Typer `context_settings` or via env var (`TERRAPYNE_QUIET=1`).

### Risks

- Changing exit codes is a backwards-incompatible behavioural change. Mitigation: 0.x version freedom, document in CHANGELOG.

### Out of Scope

- The deeper `tfc local` / `tfc cloud` split (covered by EPIC-008).

### Acceptance Criteria — `tests/features/scripting_polish.feature` *(to author; portions exist)*

```gherkin
Feature: Terrapyne is friendly to non-interactive scripts
  As a CI pipeline
  I want flags that work in any position and prompts I can bypass
  So that scripts behave predictably

  Scenario: --quiet works as a sub-app flag
    When I run "tfc workspace list -o my-org --quiet"
    Then the command succeeds
    And no progress text is printed

  Scenario: var-rm has a --yes bypass
    Given a workspace with variable "region"
    When I run "tfc workspace var remove --key region -w app --yes"
    Then no prompt is shown
    And the variable is removed

  Scenario: run trigger exits 0 on a successful trigger
    Given a workspace ready for runs
    When I run "tfc run trigger -w app && echo CHAINED"
    Then "CHAINED" appears in the output

  Scenario: workspace list output is deterministic with --no-truncate
    Given workspaces with long names
    When I run "tfc workspace list --no-truncate"
    Then no name in the output is suffixed with an ellipsis
```

---

## EPIC-005 — Pagination Honesty in the SDK

**td:** *(unregistered)*  •  **Track:** SDK Correctness  •  **Priority:** P1

### Problem Statement

`RunsAPI.list(workspace_id, limit=20)` accepts a `limit` parameter that is silently capped at 100 because it issues a single page request (`page[size]=min(limit, 100)`). A user passing `limit=500` gets back the most recent 100 runs and has no signal that data was truncated. Other API methods (e.g. `WorkspaceAPI.list`) correctly use `client.paginate`; this asymmetry is a footgun. The SDK's promise of "high-level abstractions" is broken when one API truncates and others paginate.

### User Value

SDK consumers can write `for run in client.runs.list(ws_id, limit=500): ...` and get 500 runs (or fewer if fewer exist), not 100 with no warning. Trust in the SDK is foundational for the agent-automation use case.

### Success Metrics

- `RunsAPI.list` paginates beyond 100 by default, capped only at the requested `limit`.
- A clear contract: if `limit` is `None`, fetch all; if numeric, fetch up to that many.
- Audit of every `*API.list` method in `src/terrapyne/api/`: each either paginates or uses `page_size` instead of `limit` in its signature.

### Unknowns

- Whether to add a streaming iterator API (`client.runs.iter_all(ws_id)`) for long histories. Possibly in a follow-up epic; out of scope here.

### Risks

- Slowing down the default `tfc run list` if pagination is too aggressive. Mitigation: keep CLI default at 20, but make the SDK honest about what it's returning.

### Out of Scope

- Async iteration (deferred to EPIC-009).

### Acceptance Criteria — `tests/features/sdk_pagination.feature` *(to author)*

```gherkin
Feature: SDK pagination is honest
  As an SDK consumer
  I want list APIs to either paginate or to advertise their page-size
  So I never silently lose data

  Scenario: runs.list with limit > 100 returns up to limit items
    Given a workspace with 250 runs
    When I call client.runs.list(workspace_id, limit=200)
    Then the result contains 200 runs
    And the total count metadata reports 250

  Scenario: list APIs uniformly accept page_size or paginate
    Given any *API.list method
    When the method signature is inspected
    Then it either paginates internally or exposes page_size, not limit
```

---

## EPIC-006 — Decompose CLI Command Modules

**td:** *(unregistered)*  •  **Track:** Maintainability  •  **Priority:** P2

### Problem Statement

`cli/run_cmd.py` is 987 lines with 14 commands and 59 `console.print` calls. `cli/workspace_cmd.py` is 957 lines with 17 commands and a nested `var` subgroup. `api/workspace_clone.py` is 739 lines for a single API operation. The pattern of "one big `*_cmd.py` per noun" doesn't scale: every PR touching a command hits a hub file; tests for individual commands have to import a 957-line module; pre-commit hook output for hub-safety fires on most CLI changes. The code is well-written; there's just too much of it in one place.

### User Value

Faster, safer feature work for contributors. Each command becomes 1:1 with a test file, and PRs touch focused files. New command additions don't require navigating thousand-line modules. Hub-safety warnings stop being false-positive noise.

### Success Metrics

- No `cli/*_cmd.py` exceeds 300 lines.
- Each command has a 1:1 file under `cli/<group>/<command>.py`.
- `cli/run/__init__.py` (and equivalents) re-exports the Typer `app` for backwards compatibility.
- Import-linter contracts remain green.

### Unknowns

- Whether to also split `api/workspace_clone.py` (separate API operation). Probably yes; do as a final pass within this epic.

### Risks

- Refactor regression. Mitigation: drive entirely behind the existing test suite (after EPIC-001), with no behavioural changes in this epic.

### Out of Scope

- Pushing orchestration down to the SDK (EPIC-007).
- Any user-visible behaviour changes.

### Acceptance Criteria

This epic is internal refactoring with no behavioural change. Acceptance is:

- All existing tests pass after refactor (Repeatability gate from EPIC-001 must hold).
- No file in `src/terrapyne/cli/` exceeds 300 lines.
- `make test-fast` time does not regress by more than 10 %.

---

## EPIC-007 — Push Orchestration from CLI into the SDK

**td:** *(unregistered)*  •  **Track:** Architecture  •  **Priority:** P2

### Problem Statement

`run trigger` (184 lines in `cli/run_cmd.py`) interleaves orchestration logic — discarding active runs, queue-waiting, polling — with CLI concerns (argument parsing, console output). This logic isn't reusable from the SDK: an automation script importing `terrapyne` cannot do `client.runs.trigger_with_queue_management(...)`; it has to either duplicate the logic or shell out to the CLI. Same pattern applies to log streaming in `run follow` and error-summary computation.

### User Value

SDK consumers (CI tooling, agents, internal portals) can build on the same primitives the CLI uses. The CLI shrinks to a thin presentation layer over a richer SDK.

### Success Metrics

- `RunsAPI` exposes high-level workflows: `trigger_with_queue_management`, `stream_logs`, `get_error_summary` (latter exists already; verify completeness).
- CLI command bodies are < 50 lines each, mostly mapping arguments to SDK calls and rendering results.
- SDK reference docs (`docs/reference/sdk.md`) document the new methods.

### Unknowns

- Naming. Marge prefers verbs that read like sentences: `client.runs.trigger(workspace_id, queue_strategy="wait")` over `client.runs.trigger_with_queue_management(...)`. Lisa to decide on signature shape.

### Risks

- Over-abstraction. Mitigation: only push down logic that's already battle-tested in the CLI and clearly user-facing.

### Out of Scope

- New high-level workflows that don't exist in the CLI today (e.g. cross-workspace orchestration).

### Acceptance Criteria — `tests/features/sdk_workflows.feature` *(to author)*

```gherkin
Feature: SDK exposes high-level run workflows
  As an SDK consumer
  I want to trigger a run with queue-management without re-implementing it
  So I can build automation without duplicating logic

  Scenario: SDK can trigger a run and discard active runs first
    Given a workspace with one active run
    When I call client.runs.trigger(workspace_id, queue_strategy="discard_active")
    Then the active run is discarded
    And a new run is created

  Scenario: SDK can stream logs without ANSI codes
    Given a run in progress
    When I call client.runs.stream_logs(run_id) and read 5 lines
    Then no ANSI escape sequences appear in any line
```

---

## EPIC-008 — OpenTofu Support in `terrapyne.local`

**td:** *(unregistered)*  •  **Track:** Platform Reach  •  **Priority:** P1

### Problem Statement

The OpenTofu fork has measurable enterprise adoption. `terrapyne.local.Terraform` currently hard-binds to the `terraform` binary discovered on `$PATH`. Users on OpenTofu projects either can't use Terrapyne for local execution or risk the dangerous footgun of running `terraform` against a `tofu`-managed lockfile (or vice versa). The design has been thought through: see the worktree `feature/opentofu-support` and `docs/features/opentofu-support.md`. The high-level approach: heuristic auto-detection from `.terraform.lock.hcl` and version-manager files, with explicit failure when the matching binary is missing.

A second, related constraint: HashiCorp restricts OpenTofu from natively using Terraform Cloud as a backend. Therefore `terrapyne.api` and `tfc` CLI must explicitly block TFC API operations on detected-OpenTofu projects, with a clear error message rather than a silent failure.

### User Value

OpenTofu users get a Pythonic local-execution wrapper that's safe. Mixed-fleet organisations don't need separate tooling. Migration teams (Terraform → OpenTofu) get a `--force-runner` bypass for the transition window.

### Success Metrics

- `from terrapyne.local import OpenTofu` works.
- Auto-detection from `.terraform.lock.hcl` (registry URL) and `.opentofu-version` / `.terraform-version` files succeeds for common project shapes.
- Detection of OpenTofu in a project blocks `tfc` API commands with an actionable error.
- The migration workflow works via explicit `force_runner=True` (SDK) or `--force-runner tofu` (CLI).
- A safety test: when OpenTofu is detected but `tofu` is not on `$PATH`, terrapyne fails fast — never silently falls back to `terraform`.

### Unknowns

- Final API shape: `detect_runner(directory) -> Terraform | OpenTofu` factory, or a unified `LocalIACRunner.from_directory(...)` constructor? Lisa decision.
- Whether to introduce a `tfc local` command group at the same time, or keep that as a follow-up.

### Risks

- Misdetection corrupting state. Mitigation: heuristics are conservative — if signals conflict, fail rather than guess.
- Drift between Terraform and OpenTofu behaviour. Mitigation: subclass with overrides only where needed; share the bulk of logic via `LocalIACRunner` base.

### Out of Scope

- Full `tfc local plan`, `tfc local validate` agnostic command group (separate epic).
- Migrating `tests/test_terrapyne_base.py` away from the deprecated `terrapyne.Terraform` import (do as part of this epic's cleanup, but track separately if it grows).

### Acceptance Criteria — `tests/features/opentofu_support.feature` *(to author; design doc exists)*

```gherkin
Feature: Terrapyne safely runs both Terraform and OpenTofu locally
  As a developer working in a mixed-fleet organisation
  I want Terrapyne to detect the correct runner from project files
  So I never accidentally corrupt state with the wrong binary

  Scenario: An initialized Terraform project picks the terraform binary
    Given a directory with a .terraform.lock.hcl from "terraform init"
    When I instantiate the runner via auto-detection
    Then a Terraform instance is returned

  Scenario: An initialized OpenTofu project picks the tofu binary
    Given a directory with a .terraform.lock.hcl from "tofu init"
    When I instantiate the runner via auto-detection
    Then an OpenTofu instance is returned

  Scenario: Missing matching binary fails fast
    Given a directory that auto-detects as OpenTofu
    And the tofu binary is not on $PATH
    When I instantiate the runner via auto-detection
    Then a clear error is raised
    And the error message names "tofu" explicitly
    And no fallback to "terraform" is attempted

  Scenario: TFC API operations are blocked on OpenTofu projects
    Given a directory that auto-detects as OpenTofu
    When I run "tfc workspace list" inside that directory
    Then the command fails with an actionable error
    And the error explains that TFC API operations are unsupported on OpenTofu

  Scenario: Migration override is honoured
    Given a directory that auto-detects as Terraform
    When I instantiate the runner with force_runner="tofu"
    Then an OpenTofu instance is returned
    And a one-time warning is emitted on stderr
```

---

## EPIC-009 — Async TFCClient *(parked)*

**td:** *(unregistered)*  •  **Track:** Platform Reach  •  **Priority:** P3 (parked)

### Problem Statement

`httpx.AsyncClient` is a sibling of the sync client already in use. An async API surface (`AsyncTFCClient` mirroring `TFCClient`) would unlock concurrent run-status polling across many workspaces, async log streaming, and integration with async-native agent frameworks. Cost is moderate (parallel API class hierarchy) but well-understood given the existing sync structure.

### User Value

Future-looking. Concrete demand will come once Terrapyne is embedded in larger orchestration systems (internal portals, AI agents managing 10+ workspaces concurrently).

### Status

**Parked** until a concrete user pulls. Tracked here so it isn't forgotten.

---

## EPIC-010 — Plugin Model for Custom Command Groups *(parked)*

**td:** *(unregistered)*  •  **Track:** Platform Reach  •  **Priority:** P3 (parked)

### Problem Statement

Once enterprises adopt Terrapyne, they will want to add internal commands (`tfc internal-policy-check`, `tfc cost-allocate`) without forking. A Typer-friendly entry-point–based plugin model (similar to `pip` or `pytest` plugins) would solve this. Not urgent.

### Status

**Parked** until at least one external organisation requests it.

---

## Sequencing Recommendation

Marge's view, applied through the GECR loop:

1. **EPIC-001 first.** Nothing else can be measured trustworthy until the suite is repeatable.
2. **EPIC-002 and EPIC-003 in parallel** (different files, both governed by the same automation contract). Together they constitute "PR Batch 6" from `TODO.md`.
3. **EPIC-004** as scripting-polish cleanup once 002/003 have stabilised the contract surface.
4. **EPIC-005** alongside 004 — same SDK area, same kind of correctness work.
5. **EPIC-006** before **EPIC-007** — split first, then push down. Easier reviews, fewer merge conflicts.
6. **EPIC-008** independent track — can run in parallel with 006/007 once the architecture seam is established.

P3 epics (009, 010) are parked until concrete demand surfaces.

---

## Open Decisions for Lisa

These are architectural decisions Marge is deferring to Lisa:

- **D1 (EPIC-002):** Introduce a `ux.warn/error/progress` helper module, or migrate every `console.print` call site directly?
- **D2 (EPIC-003):** Final shape of the mutation-result JSON envelope. Marge proposes `{id, type, name, url, next_actions[]}`.
- **D3 (EPIC-005):** `RunsAPI.list` — paginate by default, or rename `limit` → `page_size` and document the cap?
- **D4 (EPIC-007):** SDK workflow naming. Verb-based (`trigger`) or noun-based (`trigger_with_queue_management`)?
- **D5 (EPIC-008):** `LocalIACRunner` base + subclasses, or composition-based runner?
