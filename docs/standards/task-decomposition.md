# Task Decomposition

How an Epic becomes a sequence of testable, independently-shippable tasks. Cited from the Ralph agent persona.

## Where this fits

Marge writes the `EPIC-XXX` in `PLAN.md`. Lisa hands Ralph a `TODO-{td-id}.md` context file (see `docs/how-to/epic-handoff.md`). Ralph decomposes the epic into `td` tasks **once**, at the start of his first session on that epic, and logs the decomposition decision so future sessions inherit it.

This document defines the rules for that decomposition.

## INVEST

Each task must be:

| Letter | Means | Test |
| ------ | ----- | ---- |
| **I**ndependent | Has no hard dependency on a sibling task | Could be picked up first or last |
| **N**egotiable | The "how" is not yet locked in | Reads as a behaviour, not a checklist |
| **V**aluable | Delivers something a reviewer can verify | A reviewer can write a one-line test plan |
| **E**stimable | Effort is roughly knowable | "Half a day" or "an afternoon" — not "a week" |
| **S**mall | Fits in one focused session | One or two ACP commits, max |
| **T**estable | Has a Red test before any Green code | The Red test is the first artifact |

If a task fails any letter, decompose further or merge with a sibling.

## Decomposition strategies

Pick the cut that exposes the most risk first. Strategies in roughly ascending complexity:

### Strategy 1 — Happy path → error paths

Cut the work into:

1. The simplest success scenario (one user, one input, one output).
2. Each error path as a separate task.

Use when the success path is clear but the error envelope is fuzzy. Common for new commands, new SDK methods.

**Example (EPIC-003 / `run trigger --format json`):**
- Task 1: Successful trigger emits `{id, type, name, url, next_actions}`.
- Task 2: Trigger against missing workspace emits `{error}` with non-zero exit.
- Task 3: Trigger blocked by active run emits `{error, blocking_run_id}`.

### Strategy 2 — Boundary first

Cut along the architectural seam. Build the boundary class/method/contract first with a minimal pass-through, then layer behaviour onto it.

Use when the epic introduces a new architectural seam (a new SDK method, a new CLI subgroup).

**Example (EPIC-008 / OpenTofu):**
- Task 1: `LocalIACRunner` base class with `Terraform` subclass that's behaviourally equivalent to today's `Terraform`.
- Task 2: `OpenTofu` subclass that delegates to `tofu` binary.
- Task 3: `detect_runner()` factory using `.terraform.lock.hcl` heuristic.
- Task 4: TFC-API blocking guard for OpenTofu projects.

### Strategy 3 — Data variation

Same operation, different shapes of input. Each shape is a task; each gets its own scenario.

Use for parsers, formatters, validators.

**Example (existing plan parser):**
- Task 1: Parse a basic create-only plan.
- Task 2: Parse a plan with destroys.
- Task 3: Parse a plan with imports.
- Task 4: Parse a plan with module-nested resources.

### Strategy 4 — Layer by layer

Cut along the layering boundary: model → API → CLI. Each layer is a task and the inner-loop test for that layer is the gate.

Use when the change spans the full stack and the model layer is the riskiest part.

**Example (EPIC-007 / push orchestration to SDK):**
- Task 1: `RunsAPI.trigger(queue_strategy=...)` SDK method with unit tests.
- Task 2: CLI `run trigger` command body shrinks to ~30 lines using new SDK method.
- Task 3: Documentation update (`docs/reference/sdk.md`).

### Strategy 5 — Refactor as the first task

For epics where messy existing code blocks clean addition, the first task is a **pure refactor** (no behavioural change), and subsequent tasks add the new behaviour onto the refactored shape.

Use when the existing code is a hub or has known structural problems (EPIC-006).

**Example (EPIC-006 / split CLI command modules):**
- Task 1: Move `run list`, `run show` into their own files. No behaviour change. Full suite passes.
- Task 2: Move `run trigger`, `run watch`. Same gate.
- Task 3: Move `run follow`, `run logs`. Same gate.
- Task 4: Move remaining `run` commands; `run_cmd.py` becomes only a re-export.

The `refactor:` commits in this strategy are valuable precisely because they introduce no risk of behavioural regression.

## Sequencing the tasks

Once decomposed, sequence by **risk-first, dependency-aware**:

1. **Foundational boundary first.** If a task introduces a new seam, the next task can use it. Get the seam right before piling onto it.
2. **Happy path before error paths.** Error handling without a success path is testing a vacuum.
3. **Risky/unknown before well-understood.** If you suspect a task may surface an "Option Viability Failure" (Lisa's architecture won't survive contact with reality), do that task first. A failure on Task 1 lets Lisa replan cheaply; a failure on Task 5 wastes Tasks 2-4.

Encode dependencies as explicit `td dep add` links between tasks.

## When decomposition is wrong

You'll know decomposition is wrong if:

- You write a Green commit that doesn't deliver a reviewable behaviour change → tasks too small / too coupled.
- You can't write the Red test until the next task lands → tasks have hidden dependencies; merge or reorder.
- You finish the epic and realise tasks should have been one task → over-decomposed; note the lesson in the Retrospective Signal.
- You finish a task and three more pop into existence → underdecomposed; pause, expand the task list before pushing on.

## Logging the decomposition

After decomposing, log the decision so future sessions don't redo it:

```bash
td log <epic-id> --decision \
  "decomposed by [strategy-name] — [one-sentence rationale]"
```

Future sessions read this with `td show <epic-id>` and inherit the decomposition intent rather than reinventing it.

## Anti-patterns

- **"Implement X" tasks.** Verb without behaviour. Decompose further.
- **"Write tests for X" as a separate task from "Build X".** Tests and production code ship together (ACP). The tests are part of the build task, not a sibling of it.
- **"Refactor + new feature in one task".** Refactor is its own task with its own commit (Green-then-Refactor split, or Strategy 5).
- **Tasks with sibling order coupling.** Task 2 cannot start until Task 1 ships *and* the file structure of Task 1 is preserved → these are one task, not two.

## Self-check after decomposing

```
[ ] Each task could be picked up by a different agent
[ ] Each task has a Red test as its first deliverable
[ ] No task takes more than two ACP commits
[ ] Sequencing puts risk first
[ ] The decomposition strategy is logged via td log --decision
```
