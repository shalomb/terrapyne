# PLAN.md — Terrapyne Product Plan

> **Intent Layer.** This file is owned by Marge (Product Agent). Each epic captures the *Why* and *What*. Implementation tasks live in `TODO.md` (the operational backlog) and individual `.feature` files under `tests/features/` (the executable BDD specifications).

## How this file works

- **PLAN.md** = epics + feature briefs (durable, stakeholder-readable, *why this matters*).
- **TODO.md** = WSJF-ranked, sized, status-tracked task backlog (*what to do next*).
- **tests/features/*.feature** = executable acceptance criteria (*proof we built the right thing*).

Each epic has an ID `EPIC-XXX`. Feature scenarios in `.feature` files cite their `EPIC-XXX` in tags so traceability is preserved without tooling.

---

## Epic index

| ID         | Title                                                | Track            | Priority | Status      |
| ---------- | ---------------------------------------------------- | ---------------- | -------- | ----------- |
| EPIC-001   | Restore Test-Suite Repeatability                     | Quality / TDD    | P0       | In Progress |
| EPIC-002   | Honour the Documented Automation Contract            | Agent Experience | P0       | Done        |
| EPIC-003   | Structured Output for Mutating Commands              | Agent Experience | P0       | Done        |
| EPIC-004   | Frictionless Scripting & Non-Interactive Use         | Scripting        | P1       | Done        |
| EPIC-005   | Pagination Honesty in the SDK                        | SDK Correctness  | P1       | Done        |
| EPIC-006   | Decompose CLI Command Modules                        | Maintainability  | P2       | Done        |
| EPIC-007   | Push Orchestration from CLI into the SDK             | Architecture     | P2       | Draft       |
| EPIC-008   | OpenTofu Support in `terrapyne.local`                | Platform Reach   | P1       | Draft       |
| EPIC-009   | Async TFCClient                                      | Platform Reach   | P3       | Parked      |
| EPIC-010   | Plugin Model for Custom Command Groups               | Platform Reach   | P3       | Parked      |

Priority legend: **P0** = blocks trust in the product; **P1** = visible user pain; **P2** = compounds into pain over time; **P3** = future-looking.

---

## EPIC-001 — Restore Test-Suite Repeatability

**Track:** Quality / TDD  •  **Priority:** P0  •  **Status:** In Progress

### Problem Statement

The test suite reports 815 passing under `make test-all`, but running subsets (e.g. `pytest tests/test_cli/`) produces 32+ failures, and at least one test ordering causes pytest to hang. The cause is module-level mutable state on the shared Rich `console` singleton (`console.quiet`, `console._force_terminal`, `console.no_color`) that tests mutate but never reset. A separate, latent issue: a BDD step in `test_run_commands.py` patches `terrapyne.cli.utils.validate_context`, but `cli/utils.py` is a deprecated stub — the patch silently no-ops, the real `validate_context` is called, and credential resolution is attempted against the live filesystem.

### Progress

- PR #121 (`chore: agent guardrails, audit targets, and conftest hardening`) addressed conftest hardening and some fixture isolation.
- Remaining: randomised ordering verification, full subset isolation, patch-target audit.

### User Value

The CI build is a lie if the suite isn't repeatable. Contributors waste hours chasing phantom failures that depend on test order.

### Success Metrics

- `pytest tests/` passes in any subset and any order (verified with shuffled execution).
- `pytest -p pytest_randomly` remains green across N=10 random orderings.
- `make test-fast` time stays under 10 seconds.
- Zero broken `patch()` targets in the test tree.

### Acceptance Criteria

```gherkin
Feature: Test suite is repeatable across orderings

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

**Track:** Agent Experience  •  **Priority:** P0  •  **Status:** ✅ Done

### Delivered By

- PR #125 (`fix(cli): route error messages to stderr via error_console`)

### Summary

`error_handlers.py` now routes all API errors to stderr via `error_console`. BDD feature file and step definitions verify the contract. ~30 inline validation-error sites remain on stdout (tracked as BF1 follow-up).

---

## EPIC-003 — Structured Output for Mutating Commands

**Track:** Agent Experience  •  **Priority:** P0  •  **Status:** ✅ Done

### Delivered By

- PR #119 (`feat(ax): Add Agent Experience (AX) CLI primitives`) — AX5: `--format json` for mutations
- PR #122 (`fix(ax7): deep error context surfacing`) — structured error JSON on failures

### Summary

All mutating commands now support `--format json`. The JSON envelope includes `id`, `type`, and resource details. Error responses include structured `title`/`detail` from the TFC API.

---

## EPIC-004 — Frictionless Scripting & Non-Interactive Use

**Track:** Scripting  •  **Priority:** P1  •  **Status:** ✅ Done

### Delivered By

- PR #118 (`fix(scripting): PR Batch 4 — scripting and automation polish (B9, B12, B13, B14, B15)`)

### Summary

All scripting bugs resolved:
- B13: `run trigger` exits 0 on success.
- B14: `--yes` flag added to destructive commands.
- B12: `--no-truncate` flag for workspace list.
- B9: Workspace name lookup fixed.
- B15: `--quiet` works as sub-app flag.

---

## EPIC-005 — Pagination Honesty in the SDK

**Track:** SDK Correctness  •  **Priority:** P1  •  **Status:** ✅ Done

### Delivered By

- PR #124 (`fix(sdk): paginate RunsAPI.list beyond 100 items`)

### Summary

`RunsAPI.list` now paginates beyond 100 items when `limit > 100` and fetches all when `limit=None`. BDD feature file and unit tests cover multi-page, all-pages, and single-page scenarios. Follow-up: `RunTriggerAPI.list` still truncates (tracked as BF3).

---

## EPIC-006 — Decompose CLI Command Modules

**Track:** Maintainability  •  **Priority:** P2  •  **Status:** ✅ Done

### Delivered By

- PR #108 (`refactor: decompose codebase to reduce module bloat`)
- PR #116 (`refactor(workspace): introduce workspace var subgroup and sync cli-reference`)

### Summary

CLI modules decomposed. `workspace_cmd.py` split into subgroup structure. Variable commands moved to `workspace var` subgroup. No file exceeds the target line count.

---

## EPIC-007 — Push Orchestration from CLI into the SDK

**Track:** Architecture  •  **Priority:** P2  •  **Status:** Draft

### Problem Statement

`run trigger` (184 lines) interleaves orchestration logic — discarding active runs, queue-waiting, polling — with CLI concerns. This logic isn't reusable from the SDK. An automation script importing `terrapyne` cannot do `client.runs.trigger(workspace_id, queue_strategy="wait")`.

### User Value

SDK consumers can build on the same primitives the CLI uses. The CLI shrinks to a thin presentation layer.

### Success Metrics

- `RunsAPI` exposes high-level workflows: `trigger` with queue strategy, `stream_logs`, `get_error_summary`.
- CLI command bodies are < 50 lines each.

### Acceptance Criteria

```gherkin
Feature: SDK exposes high-level run workflows

  Scenario: SDK can trigger a run and discard active runs first
    Given a workspace with one active run
    When I call client.runs.trigger(workspace_id, queue_strategy="discard_active")
    Then the active run is discarded
    And a new run is created
```

---

## EPIC-008 — OpenTofu Support in `terrapyne.local`

**Track:** Platform Reach  •  **Priority:** P1  •  **Status:** Draft

### Problem Statement

`terrapyne.local.Terraform` hard-binds to the `terraform` binary. OpenTofu users can't use Terrapyne for local execution. The design exists in `feature/opentofu-support` worktree.

### User Value

OpenTofu users get a safe local-execution wrapper. Mixed-fleet organisations don't need separate tooling.

### Success Metrics

- `from terrapyne.local import OpenTofu` works.
- Auto-detection from `.terraform.lock.hcl` and version-manager files.
- Detection of OpenTofu blocks `tfc` API commands with an actionable error.
- `--force-runner tofu` bypass for migration.

### Acceptance Criteria

```gherkin
Feature: Terrapyne safely runs both Terraform and OpenTofu locally

  Scenario: An initialized OpenTofu project picks the tofu binary
    Given a directory with a .terraform.lock.hcl from "tofu init"
    When I instantiate the runner via auto-detection
    Then an OpenTofu instance is returned

  Scenario: Missing matching binary fails fast
    Given a directory that auto-detects as OpenTofu
    And the tofu binary is not on $PATH
    When I instantiate the runner via auto-detection
    Then a clear error is raised naming "tofu"
    And no fallback to "terraform" is attempted

  Scenario: TFC API operations are blocked on OpenTofu projects
    Given a directory that auto-detects as OpenTofu
    When I run "tfc workspace list" inside that directory
    Then the command fails with an actionable error
```

---

## EPIC-009 — Async TFCClient *(parked)*

**Track:** Platform Reach  •  **Priority:** P3  •  **Status:** Parked

An async API surface (`AsyncTFCClient`) would unlock concurrent polling across many workspaces and integration with async-native agent frameworks. Parked until concrete demand surfaces.

---

## EPIC-010 — Plugin Model for Custom Command Groups *(parked)*

**Track:** Platform Reach  •  **Priority:** P3  •  **Status:** Parked

A Typer-friendly entry-point–based plugin model for enterprise custom commands. Parked until at least one external organisation requests it.

---

## Sequencing Recommendation

1. **EPIC-001** — finish test repeatability (partially done via PR #121).
2. **EPIC-002** — stdout/stderr separation (the last P0 blocker).
3. **EPIC-005** — pagination honesty (SDK correctness).
4. **EPIC-007** — push orchestration into SDK (architecture improvement).
5. **EPIC-008** — OpenTofu support (independent track, can parallel with 007).

P3 epics (009, 010) remain parked.

---

## Open Decisions for Lisa

- **D1 (EPIC-002):** Introduce a `ux.warn/error/progress` helper module, or migrate every `console.print` call site directly?
- **D3 (EPIC-005):** `RunsAPI.list` — paginate by default, or rename `limit` → `page_size` and document the cap?
- **D4 (EPIC-007):** SDK workflow naming. `trigger(workspace_id, queue_strategy="wait")` or `trigger_with_queue_management(...)`?
- **D5 (EPIC-008):** `LocalIACRunner` base + subclasses, or composition-based runner?
