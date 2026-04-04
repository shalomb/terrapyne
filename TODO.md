# Terrapyne — Backlog

## Now

- [ ] Run ID truncation — `no_wrap=True` on ID columns so copy-paste works
- [ ] `parse-plan --format json` stdout fix — use `print()` not `console.print()`
- [ ] Remove debug stubs (`debug run`, `debug workspace`) or exit non-zero
- [ ] StateVersion `class Config` → `ConfigDict` (pydantic deprecation)
- [ ] pyproject.toml: fix license/classifier mismatch, status → Alpha
- [ ] .gitignore: exclude `build/`, `.ipynb_checkpoints/`
- [ ] `--raw` flag on `state outputs` for CI-friendly single values

## Next

- [ ] `workspace list --project` — resolve name to ID (currently silently ignored)
- [ ] `project show` without args — resolve from current workspace context
- [ ] `parse-plan` stdin support (`-` for piping)
- [ ] `--yes` on all mutating commands (clone, var-set, var-copy, apply, delete)
- [ ] `state diff` — surface errors instead of silently aborting
- [ ] `workspace show` enrichment — project name, queued runs, health, VCS commit
- [ ] `project show` enrichment — workspace summary, active runs across project
- [ ] `--wait` on `run trigger`/`apply` — stream logs, exit non-zero on failure

## Later

- [ ] `workspace costs` / `project costs` — extract cost estimates from plans
- [ ] `--debug` flag — log API calls (URL, method, status, timing) to stderr
- [ ] `team access` / `team access-compare` CLI commands
- [ ] `vcs set-branch` — rename from `update-branch` for consistency
- [ ] IDP-friendly JSON exports — stable schema for Backstage/Harness integration
- [ ] Local response cache with TTL for expensive API calls
- [ ] Coverage push to 80% (state_versions 0%, CLI commands ~15%)
- [ ] Import plan parser 30-fixture test suite from authoritative source
- [ ] TFC 1.12+ structured log format — detect and warn

## Done

- [x] `workspace show/variables/vcs` context resolution (PR #12)
- [x] `run logs` missing `-o` flag + 404 handling (PR #13)
- [x] `state outputs` arg ambiguity — accepts workspace name/ID/sv-ID (PR #21)
- [x] `state show` defaults to latest (PR #21)
- [x] `state list` HTTP 400 fix (PR #8)
- [x] `project find` performance — `filter[names]` for exact match (PR #20)
- [x] Exit code 0 on help screens (PR #9, #14)
- [x] `--format json` on all list/show commands (PR #18)
- [x] `--search` + wildcard search on workspace/team/project list (PR #10)
