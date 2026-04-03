# TODO — Exploratory Testing Findings

Bugs and improvements found during exploratory testing against live TFC.

## Development Requirements
All new features and fixes must strictly follow:
1. **Red/Green TDD**: Write a failing test first, make it pass with minimal code, then refactor.
2. **Adzic BDD**: Use Gojko Adzic's Specification by Example principles to write `.feature` files.
3. **ACP (Atomic Commit Protocol)**: Every commit must be atomic, verified, and use Conventional Commits.

## Test Environment
For evaluating live TFC behavior, use the following workspace directory:
- `/home/unop/oneTakeda/terraform-dce-developer-ShalomBhooshi/iac/dev`

## Priority Matrix

Effort: S (< 30min), M (1-2h), L (half day+)
Impact: 🔴 High (broken/unusable/blocks workflow), 🟡 Medium (annoying/workaround exists), 🟢 Low (nice-to-have)

| # | Finding | Impact | Effort | Score | Status |
|---|---|---|---|---|---|
| 7 | `tfc project find` takes 1m38s — use `filter[names]` for exact match | 🔴 | S | 🏆 | ✅ PR #20 |
| 3 | `tfc state outputs 'workspace-name'` errors — arg treated as state version ID | 🔴 | S | 🏆 | ✅ PR #21 |
| 4 | `tfc state outputs 'ws-ID'` errors — same arg ambiguity | 🔴 | S | 🏆 | ✅ PR #21 |
| 9 | `--raw` flag for `state outputs` for single unquoted values (CI/CD friendly) | 🟡 | S | 🏆 | TODO |
| 10 | `--wait` flag for `run trigger`/`apply` to stream logs & exit w/ code on failure | 🔴 | M | 🏆 | TODO |
| 5 | `tfc state show` without args should default to latest | 🟡 | S | ⭐ | ✅ PR #21 |
| 2 | `tfc state outputs` without workspace should auto-detect from context | 🟡 | S | ⭐ | ✅ PR #21 |
| 11 | `tfc workspace costs` to extract cost estimates (deltas and monthly) | 🟡 | M | ⭐ | ✅ PR |
| 12 | `tfc project costs` to aggregate cost estimates across workspaces | 🟡 | M | ⭐ | ✅ PR |
| 1 | `tfc project show` without args should resolve project from current workspace | 🟡 | M | ⭐ | TODO |
| 1b | `tfc workspace show` 'single glance' snapshot (queued runs, health, VCS commit) | 🟡 | M | ⭐ | TODO |
| 1c | `tfc project show` 'single glance' snapshot (workspaces summary, active runs) | 🟡 | M | ⭐ | TODO |
| 13 | `--json` full structured output for `workspace show` and `project show` (for IDPs) | 🟡 | S | ⭐ | TODO |
| 6 | `--debug` flag for API call tracing (URLs, response codes, timing) | 🟡 | M | 💡 | TODO |
| 8 | Local file-based response cache with TTL for expensive API calls | 🟢 | L | 💡 | TODO |

## Remaining Details

### 9. `--raw` flag for outputs (🏆)
When extracting outputs for bash scripts (e.g., `DB_URL=$(tfc state outputs db_endpoint --raw)`), we need a way to return just the unquoted string value to stdout without the table formatting or JSON structure.

### 10. CI/CD Wait States (🏆)
`tfc run trigger` and `tfc run apply` need a `--wait` flag. It should block execution, stream the logs to stdout, and critically, exit with a non-zero exit code if the run fails. This is essential for using the CLI inside GitHub Actions or Jenkins pipelines.

### 11 & 12. Workspace and Project Cost Estimates (⭐)
Power users and FinOps need cost visibility without opening the UI.
- `tfc workspace costs`: Look up the latest plan for a workspace and extract the estimated monthly cost and the cost delta (+/-).
- `tfc project costs`: Iterate through all workspaces in a project, extract their cost estimates, and provide an aggregated total for the project.

### 1. Project show from context (⭐)
`tfc project show` without args should resolve: context → workspace → project_id → project.
Requires one extra API call (get workspace, read project_id relationship).

### 1b. Workspace show enrichment (⭐)
`tfc workspace show` should act as a 'single glance' snapshot for power engineers. It needs to show if there are runs planned, how many are queued/lined up, health status, and VCS commit info. Essentially recreating the GUI's high-level dashboard but optimized for the terminal.

### 1c. Project show enrichment (⭐)
`tfc project show` should similarly act as a 'single glance' snapshot. It could aggregate workspace health, show total active runs across the project, and summarize workspace counts.

### 13. IDP-Friendly JSON Exports (⭐)
For integrations with Service Catalogs (Backstage, Harness IDP), `workspace show` and `project show` must support a `--json` flag that outputs a stable, comprehensive schema containing all the aggregated snapshot data.

### 6. Debug flag (💡)
A `--debug` or `-v` flag that logs API calls (URL, method, status code, timing) to stderr.
Could use Python's `logging` module with `httpx`'s event hooks. Useful for diagnosing
slow commands and understanding what the tool is doing.

### 8. Response caching (💡)
Cache expensive API responses (workspace list, project list, team list) in
`~/.cache/terrapyne/` with a configurable TTL (default 5min). Invalidate on any write
operation. Would make repeated `tfc project show` or `tfc workspace list` near-instant.
