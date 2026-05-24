# TODO — Terrapyne Product Backlog

> [!IMPORTANT]
> **AGENTS**: Before pulling tasks from this backlog or writing any code, you MUST read `AGENTS.md` and strictly follow the TDD/BDD Adzic/Farley rules, ACP commit protocol, and the Adversarial Review (Bart) workflow.

## Development Requirements

All new features and fixes must strictly follow:
1. **Red/Green TDD**: Write a failing test first, make it pass with minimal code, then refactor.
2. **Adzic BDD**: Use Gojko Adzic's Specification by Example principles to write `.feature` files.
3. **ACP (Atomic Commit Protocol)**: Every commit must be atomic, verified, and uses Conventional Commits.

## Test Environment

For evaluating live TFC behaviour, use:
- `/home/unop/oneTakeda/terraform-dce-developer-ShalomBhooshi/iac/dev`

---

## Open Work

**Impact**: 🔴 High (4), 🟡 Medium (2), 🟢 Low (1)
**Effort**: S=1, M=2, L=3
**WSJF** = Impact / Effort

| # | Finding | Impact | Effort | WSJF | Epic |
|---|---|---|---|---|---|
| **BART FEEDBACK (from review)** |
| BF1 | ~30 inline `console.print("[red]Error...")` calls bypass `handle_cli_errors` — validation errors still go to stdout | 🟡 | M | 1.0 | EPIC-002 |
| BF2 | `sdk_pagination.feature` has no pytest-bdd step definitions — BDD contract not executable | 🟢 | S | 1.0 | EPIC-005 |
| BF3 | `RunTriggerAPI.list` still silently truncates (single unpaginated request) | 🟡 | S | 2.0 | EPIC-005 |
| **NEW FEATURES** |
| F4 | Workspace notifications (webhook/Slack config) | 🟡 | M | 1.0 | — |
| F5 | Policy sets / Sentinel outcome reporting | 🟡 | M | 1.0 | — |
| F6 | Private registry query (modules + providers) | 🟡 | M | 1.0 | — |
| F7 | Agent pools — list and show self-hosted agents | 🟡 | M | 1.0 | — |
| F8 | SSH keys / VCS OAuth token management | 🟢 | L | 0.33 | — |
| **ARCHITECTURE** |
| A12 | `run_cmd.py` decomposition (852 lines) | 🟢 | L | 0.3 | EPIC-007 |
| A13 | `paginate()` and `paginate_with_meta()` divergent | 🟢 | M | 0.5 | EPIC-005 |

---

## Task Details

### BF1 — Inline validation errors still write to stdout

**Intent**: Complete the stdout/stderr separation started in EPIC-002.

**Context**: `handle_cli_errors` now routes API errors to stderr, but ~30 call sites use `console.print("[red]Error...")` + `raise typer.Exit(1)` for validation errors (missing org, missing flags). These bypass the decorator and pollute stdout.

**Action**: Replace `console.print` with `error_console.print` at each validation-error site, or introduce a `ux.error()` helper.

---

### BF2 — sdk_pagination.feature missing step definitions

**Intent**: Make the BDD feature file executable via pytest-bdd.

**Context**: `tests/features/sdk_pagination.feature` was created as documentation but has no corresponding step definitions. The unit tests cover the same scenarios.

**Action**: Add step definitions in `tests/test_api/test_sdk_pagination_bdd.py`.

---

### BF3 — RunTriggerAPI.list silently truncates

**Intent**: Apply the same pagination fix from EPIC-005 to `RunTriggerAPI.list`.

**Context**: `RunTriggerAPI.list` does a single unpaginated request, silently dropping results beyond page size. Same class of bug as the original `RunsAPI.list`.

**Action**: Add pagination loop matching the pattern in `RunsAPI.list`.

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

---

### A12 — run_cmd.py decomposition

**Intent**: Extract orchestration logic from the CLI layer into the SDK.

**Context**: `run_cmd.py` mixes CLI glue with complex log streaming and polling state machines. This blocks EPIC-007 (push orchestration into SDK).

**Action**: Extract `RunMonitor` or move polling logic to `RunsAPI`.

---

### A13 — Pagination divergence

**Intent**: Unify `paginate()` and `paginate_with_meta()` into a single consistent pagination strategy.

**Context**: Two pagination helpers with different semantics. `paginate_with_meta` overwrites `included` on each page (B3 was a symptom, now fixed, but the root divergence remains).

**Action**: Consolidate into one paginator that accumulates metadata correctly.
