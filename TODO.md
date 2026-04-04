# Terrapyne — Backlog

Consolidated from exploratory testing findings, FEEDBACK.md code review, and TODO items.

## Bugs

| # | Issue | Effort | Status |
|---|---|---|---|
| B1 | `workspace show/variables/vcs` discards resolved workspace name | S | ✅ PR #12 |
| B2 | `run logs` missing `-o` flag | S | ✅ PR #13 |
| B3 | `run logs` 404 on errored runs shows raw traceback | S | ✅ PR #13 |
| B4 | `state outputs` treats workspace name as state version ID | S | ✅ PR #21 |
| B5 | `state show` requires `--latest` instead of defaulting | S | ✅ PR #21 |
| B6 | `state list` HTTP 400 — missing org filter | S | ✅ PR #8 |
| B7 | `project find` takes 1m38s — client-side filtering | S | ✅ PR #20 |
| B8 | Exit code 2 on help screens | S | ✅ PR #9, #14 |
| B9 | `workspace list --project` silently ignored — name not resolved to ID | S | TODO |
| B10 | `run list` truncates Run IDs — copy-paste unusable | S | TODO |
| B11 | `parse-plan --format json` to stdout produces invalid JSON (Rich mangles it) | S | TODO |
| B12 | `state diff` silently aborts on error | S | TODO |
| B13 | `debug run`/`debug workspace` are stubs that exit 0 | S | TODO |
| B14 | Pydantic V2 deprecation in `state_version.py` (`class Config`) | S | TODO |

## Features

| # | Feature | Effort | Status |
|---|---|---|---|
| F1 | `--format json` on all list/show commands | M | ✅ PR #18 |
| F2 | `--search` on workspace/team/project list | S | ✅ PR #10 |
| F3 | Wildcard workspace search (`search[wildcard-name]`) | S | ✅ PR #10 |
| F4 | `project show` without args resolves from current workspace | M | TODO |
| F5 | `workspace show` enrichment (project name, last run, health) | M | TODO |
| F6 | `--debug` flag for API call tracing to stderr | M | TODO |
| F7 | `run parse-plan` stdin support (`-` for piping) | S | TODO |
| F8 | `team access` / `team access-compare` CLI commands | M | TODO |
| F9 | `vcs set-branch` (rename from `update-branch`) | S | TODO |
| F10 | `--yes` on all mutating commands | M | TODO |
| F11 | Local file-based response cache with TTL | L | TODO |

## Quality

| # | Item | Effort | Status |
|---|---|---|---|
| Q1 | Coverage: 64% → 80% (state_versions 0%, CLI commands ~15%) | L | TODO |
| Q2 | Stale `utils.py` alongside `utils/` package — audit/remove | S | TODO |
| Q3 | `pyproject.toml` license/classifier mismatch | S | TODO |
| Q4 | Development status classifier: Production/Stable → Alpha | S | TODO |
| Q5 | `.gitignore`: exclude `build/`, `.ipynb_checkpoints/` | S | TODO |
| Q6 | Import plan parser 30-fixture test suite from authoritative source | M | TODO |
| Q7 | TFC 1.12+ structured log format: detect and warn | M | TODO |

## Priority Order

### Do now (S effort, high impact)
1. B10 — Run ID truncation (`no_wrap=True`)
2. B11 — `parse-plan` JSON stdout fix (`print()` not `console.print()`)
3. B13 — Remove or mark debug stubs
4. B14 — StateVersion ConfigDict
5. Q3/Q4/Q5 — pyproject.toml + .gitignore housekeeping

### Do next (S-M effort, medium impact)
6. B9 — `--project` name resolution in workspace list
7. F4 — `project show` from context
8. F7 — `parse-plan` stdin support
9. F10 — `--yes` on mutating commands
10. B12 — `state diff` error surfacing

### Backlog (M-L effort, nice-to-have)
11. F5 — Workspace show enrichment
12. F6 — `--debug` flag
13. F8 — Team access CLI commands
14. F11 — Response caching
15. Q1 — Coverage push to 80%
16. Q6 — Import parser fixture suite
17. Q7 — TFC 1.12+ structured log detection
