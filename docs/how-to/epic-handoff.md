# Epic Handoff

How an Epic moves from Marge (intent) through Lisa (architecture) to Ralph (execution) to Bart (review). The handoff artifact is `TODO-{td-id}.md`. This document defines its format.

## Why a fixed format

Each agent has a different reading lens. Marge cares about user value; Lisa cares about architecture; Ralph cares about constraints; Bart cares about contracts. A single shared file with predictable sections lets each agent find their lens quickly without wading through everything.

The format is **intentionally short**. If the file is more than ~150 lines, decompose the epic.

## When the file is created

| Step | Who | Action |
| ---- | --- | ------ |
| 1 | Marge | Adds `## EPIC-XXX` to `PLAN.md`. Logs `td epic create`, captures the ID. |
| 2 | Marge | Logs `td log <epic-id> --decision "marge_approved"`. |
| 3 | Lisa | Reads the epic from `PLAN.md`. Runs ToT to pick an architectural approach. |
| 4 | Lisa | **Creates `TODO-{td-id}.md`** in the repo root. This is the handoff artifact. |
| 5 | Lisa | Logs `td log <epic-id> --decision "lisa_handoff: <hypothesis-name>"`. |
| 6 | Ralph | Reads `TODO-{td-id}.md` once at session start. **Does not modify it.** |
| 7 | Ralph | Decomposes into `td` tasks (per `docs/standards/task-decomposition.md`). |
| 8 | Bart | Reviews against the constraints in `TODO-{td-id}.md`. |

`TODO-{td-id}.md` is **read-once context**, not a task list. Tasks live in `td`.

## Where the file lives

```
<repo-root>/TODO-{td-id}.md
```

One file per active epic. When the epic merges, the file is **deleted** (not archived) — the durable artifact is `PLAN.md` plus the merged commits plus the ADRs Lisa drafted, not the handoff scratch file.

`.gitignore` does **not** exclude `TODO-{td-id}.md`. The file is committed during the epic's life so cross-session agents can read it.

## The format

```markdown
# TODO-{td-id} — <Epic title>

**Epic:** EPIC-XXX (see `PLAN.md`)
**Status:** Active
**Lisa-approved hypothesis:** <one-line summary>

---

## 1. Intent (from Marge)

> Pasted directly from `PLAN.md`. Do not rewrite — this is the immutable contract.

### Problem Statement

<copied from PLAN.md>

### User Value

<copied from PLAN.md>

### Acceptance Criteria

<copied — pointer to the .feature file is fine>

See `tests/features/<file>.feature`.

---

## 2. Context & Constraints (from Lisa)

### Architectural hypothesis

<2-3 sentences naming the chosen approach. e.g. "Add a tiny ux helper module exposing warn/error/progress that wrap error_console. Migrate cli/* to use it; do not change error_console behaviour itself.">

### Why this approach over alternatives

<3-5 bullet points. Reference rejected approaches.>

- Considered <X>; rejected because <reason>.
- Considered <Y>; rejected because <reason>.

### Relevant ADRs

- ADR-NNN — <title> — relevant because <reason>
- (if a new ADR is needed) **Proposed: ADR-NNN — <title>** — drafting in `docs/explanation/architecture/ADR-NNN-<slug>.md`

### Tech debt landmines (do NOT touch in this epic)

<Things Lisa knows are wrong but are out of scope. Ralph must avoid them.>

- `cli/utils.py` is a deprecated stub. Do not patch it; do not import from it.
- `terrapyne.Terraform` deprecation is being handled in a separate epic.

### Quality gates (Ralph must satisfy these)

- [ ] All BDD scenarios in `tests/features/<file>.feature` pass.
- [ ] No regression in `make test-all`.
- [ ] No file in `src/` exceeds 500 lines after this epic (or a `refactor:` task is filed).
- [ ] Farley Index of new tests ≥ 7.0.
- [ ] Adzic Index of new scenarios ≥ 7.0.

---

## 3. Scope reminders (for Ralph and Bart)

### In scope

<bullet list — be explicit>

### Out of scope

<bullet list — explicit non-goals; prevents scope creep>

### Open questions for Lisa

<If Ralph hits something that breaks the hypothesis, escalate here. Lisa updates this section in place.>

---

## 4. Done definition

The epic is done when:

1. All acceptance scenarios in `tests/features/<file>.feature` pass.
2. The success metrics in `PLAN.md` for EPIC-XXX are demonstrably met.
3. Bart has approved the PR.
4. ADRs in §2 are merged in `Accepted` status (if proposed).
5. `PLAN.md` epic status is updated to `Done` and the `td` epic is closed.
6. This file (`TODO-{td-id}.md`) is deleted in the merge commit.
```

## Worked example

Here's what a real handoff would look like for EPIC-001. (Hypothetical — `td-XXXX` is illustrative.)

```markdown
# TODO-td-1042 — Restore Test-Suite Repeatability

**Epic:** EPIC-001 (see `PLAN.md`)
**Status:** Active
**Lisa-approved hypothesis:** Single autouse fixture that snapshots and restores all six mutable Console fields, plus a structural lint that fails on patches against deprecated stubs.

---

## 1. Intent (from Marge)

### Problem Statement

The test suite reports 815 passing under `make test-all`, but running subsets …
[copied from PLAN.md]

### Acceptance Criteria

See `tests/features/test_repeatability.feature`.

---

## 2. Context & Constraints (from Lisa)

### Architectural hypothesis

Place an autouse, function-scoped fixture in `tests/conftest.py` that
snapshots and restores six attributes on the two shared Console instances.
Ship a one-line fix to the broken `patch()` site at the same time. Do NOT
refactor the singletons themselves — that's a separate epic (logged to
TODO.md).

### Why this approach over alternatives

- Considered making `console` a per-test fixture: rejected, would require
  changing every CLI command's import.
- Considered `monkeypatch.setattr` per-test: rejected, error-prone, easy
  to forget.
- Considered no autouse fixture and a static lint instead: rejected, can't
  catch runtime mutations cleanly.

### Relevant ADRs

- (No new ADR. Implementation is internal to test infrastructure.)

### Tech debt landmines

- `cli/utils.py` is a deprecated stub. Do not import from it.
  The broken patch site at `tests/test_cli/test_run_commands.py:1151`
  must be fixed to point at `terrapyne.cli.run_cmd.validate_context`.
- `terrapyne.rendering.logging` console singletons are NOT to be refactored
  in this epic.

### Quality gates

- [ ] `pytest tests/test_cli/` passes alone.
- [ ] `pytest tests/unit/test_workspace_context.py` passes alone.
- [ ] Full suite passes after shuffled order (3 seeds).
- [ ] `make audit-patches` passes.

---

## 3. Scope reminders

### In scope

- `tests/conftest.py` autouse fixture.
- One-line fix to `tests/test_cli/test_run_commands.py:1151`.
- `make audit-patches` recipe.
- `tests/features/test_repeatability.feature`.

### Out of scope

- Refactoring the Console singletons.
- Adding `pytest-randomly` to dev deps (separate task).
- Migrating the deprecated `terrapyne.Terraform` import.

### Open questions for Lisa

(none currently)

---

## 4. Done definition

1. All scenarios in `tests/features/test_repeatability.feature` pass.
2. `pytest tests/test_cli/` and `pytest tests/unit/` both pass alone.
3. `make audit-patches` is wired into `make test-fast`.
4. Bart approved.
5. PLAN.md EPIC-001 → Status: Done.
6. This file deleted in merge commit.
```

## Anti-patterns

- **Lisa writes a task list.** No. Tasks come from `td`. The handoff file is *narrative context*. If Lisa is enumerating tasks, she's stealing Ralph's job and the decomposition is no longer co-owned.
- **Ralph edits §1 or §2.** No. The handoff is immutable from Ralph's perspective. If reality breaks the hypothesis, escalate via §3 ("Open questions for Lisa") and `td log --uncertain`.
- **Marge edits anything below §1.** No. Marge owns Intent only.
- **No quality gates.** No. Without explicit gates, "done" becomes a feeling, not a check.
- **Long handoff file.** A 400-line handoff means the epic is too big. Decompose.

## Self-check before Lisa hands off

```
[ ] §1 (Intent) is copied verbatim from PLAN.md
[ ] §2 (Architectural hypothesis) is one paragraph, not a design doc
[ ] §2 names at least one rejected alternative
[ ] §2 lists tech debt landmines explicitly
[ ] Quality gates are concrete and verifiable
[ ] In/Out of scope are both populated
[ ] File is < 150 lines
```
