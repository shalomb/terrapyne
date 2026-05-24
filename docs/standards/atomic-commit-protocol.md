# Atomic Commit Protocol (ACP)

Canonical definition. Cited from `docs/how-to/agent-workflow.md`, `docs/how-to/commits-and-review.md`, and the Ralph agent persona.

## What "atomic" means here

A commit is **atomic** when:

1. **One reason to change.** The commit addresses exactly one concern. If the commit message needs the word "and" twice, split it.
2. **Self-contained.** The commit reverts cleanly. No partial state, no orphaned imports, no half-renamed symbols.
3. **Verified.** The commit was created from a working tree that passes the verification suite.
4. **Documented.** The commit message explains *why*, not what. The diff shows what.

Commits that match this definition can be reordered, cherry-picked, reverted, and read in isolation 18 months from now. Commits that don't match it become technical debt the moment they land.

## The verification gate

Before any commit lands, this must pass locally:

```bash
make test-fast    # ruff + import-linter + mypy + ruff-lint
make test-all     # full pytest suite
```

If `make test-fast` fails, the commit is not safe to make. If `make test-all` fails, the commit is not safe to push. There is no shortcut.

For agents using the `commit` skill, the skill runs this gate. Do not bypass it with `--no-verify`.

## Conventional Commits format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**`<type>`** — exactly one of:

| Type | When |
| ---- | ---- |
| `feat` | New user-facing capability |
| `fix` | Bug fix that affects users |
| `docs` | Documentation only — no code change |
| `test` | Test-only changes — no production code |
| `refactor` | Internal restructuring with no behaviour change |
| `chore` | Build, dependencies, tooling; nothing that ships to users |
| `perf` | Performance improvement (use sparingly; needs measurement) |

Append `!` for breaking changes (`feat!:`, `fix!:`).

**`<scope>`** — optional but encouraged. Use the affected module: `workspace-cmd`, `runs-api`, `plan-parser`, `cli`, `models`. Lowercase, hyphenated, singular.

**`<subject>`** — imperative, present tense, lowercase, no trailing period, ≤ 50 characters.

| Good | Bad |
| ---- | --- |
| `feat(workspace-cmd): add --no-truncate flag` | `Added --no-truncate flag.` |
| `fix(runs-api): paginate beyond 100 runs` | `Fixed pagination` |
| `refactor(cli): split run_cmd into per-command files` | `WIP cli refactor` |

## Commit body — the *why*

The diff already shows what changed. The body explains *why this change matters now* and *what alternatives were rejected*.

A good body answers three questions:

1. What problem does this solve?
2. Why this approach over the obvious alternative?
3. What would break if I reverted this commit?

Three short paragraphs is usually enough. Reference issues, ADRs, and EPIC IDs in the footer.

```
fix(runs-api): paginate beyond 100 runs

RunsAPI.list silently truncated at 100 because it issued a single page
request rather than using client.paginate. A user passing limit=500 had
no way to see the truncation — the SDK promise of "high-level
abstractions" was broken.

This delegates to client.paginate, which already does this correctly for
WorkspaceAPI.list. The asymmetry is removed and the limit parameter now
behaves as named.

Closes EPIC-005
Refs ADR-003 (API include parameters)
```

## Atomicity in practice

### Splitting before committing

If you have unrelated changes in your working tree:

```bash
git add -p <file>          # stage only the relevant hunks
git commit -m "feat(...): ..."
git stash                  # stash the rest
# next session: git stash pop, repeat
```

Or:

```bash
git add tests/test_foo.py src/foo.py        # one concern
git commit -m "feat(foo): ..."
git add tests/test_bar.py src/bar.py        # different concern
git commit -m "fix(bar): ..."
```

### Tests + production code in the same commit

Tests and the production code they exercise belong **in the same commit**. A test commit followed by an implementation commit produces a CI-failing intermediate state — not atomic.

Exception: when adding tests against existing production code (no production change), commit them alone with `test(...):`. Mark whether they cover an existing bug (`test: cover regression in plan parser`) or just close a coverage gap.

### Refactor commits

A `refactor(...):` commit must be behaviourally indistinguishable from its parent. If `make test-all` would have produced different results before and after the commit, it's not a refactor — it's a `feat` or `fix`.

The clean signal: a refactor commit can be dropped from a series and the user-visible behaviour is identical to the resulting tree.

## Two-step "Green then Refactor" pattern

The Red-Green-Refactor TDD cycle maps to two commits, in order:

1. **Green commit.** Tests pass, code may be ugly. Commit the messy-but-correct state.
2. **Refactor commit.** Same tests pass, code is clean. Commit the polish.

Do **not** combine them. The Green commit is the safety net; the Refactor commit is the cleanup. Keeping them separate makes each easy to review and easy to revert.

## What to never put in a commit message

- AI markers — no `Co-Authored-By: Claude`, no `Generated with`, no agent attribution. The repo is enforcing this; `make audit-ai-markers` will fail the push.
- Trailing periods on the subject line.
- Past tense (`Added X`, `Fixed Y`). Imperative only.
- The string "WIP" — work-in-progress doesn't belong in `main`. If you need to checkpoint, branch.
- Bug numbers without context (`fix #42`). Include enough subject text that the message is readable without resolving the link.

## Footer fields

| Field | When | Format |
| ----- | ---- | ------ |
| `Closes` | Issue / EPIC fully resolved by this commit | `Closes #42`, `Closes EPIC-001` |
| `Refs` | Related but not closed | `Refs ADR-005` |
| `Co-Authored-By` | Real human collaborator | `Co-Authored-By: Name <email>` (NOT for agents) |
| `BREAKING CHANGE` | Required for `feat!:`/`fix!:` | One paragraph describing migration |

## When you mess up

You will mess up. The recovery patterns:

```bash
# Last commit was wrong; not pushed yet
git commit --amend            # for message-only fixes
git reset --soft HEAD~1       # to re-stage and re-commit

# Last commit was wrong; already pushed
git revert <sha>              # never force-push to a shared branch

# Series of commits is wrong; not pushed
git rebase -i origin/main     # squash / split / reorder

# Series of commits is wrong; pushed
# Stop. Open a new branch with the corrections. Don't rewrite shared history.
```

## Self-check before committing

```
[ ] Subject ≤ 50 chars, imperative, no period
[ ] Body explains why, not what
[ ] One reason to change (no "and" twice)
[ ] make test-fast passes
[ ] make test-all passes
[ ] No AI markers anywhere
[ ] No new TODO without a ticket reference
```

If any box is unchecked, fix it before `git commit`.
