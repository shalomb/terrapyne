# TODO — Exploratory Testing Findings

Bugs and improvements found during exploratory testing against live TFC.

## Priority Matrix

Effort: S (< 30min), M (1-2h), L (half day+)
Impact: 🔴 High (broken/unusable), 🟡 Medium (annoying), 🟢 Low (nice-to-have)

| # | Finding | Impact | Effort | Score | Status |
|---|---|---|---|---|---|
| 7 | `tfc project find` takes 1m38s — client-side filtering instead of server-side `filter[names]` | 🔴 | S | 🏆 | TODO |
| 3 | `tfc state outputs 'workspace-name'` errors — positional arg treated as state version ID | 🔴 | S | 🏆 | TODO |
| 4 | `tfc state outputs 'ws-ID'` errors — same arg ambiguity | 🔴 | S | 🏆 | TODO |
| 5 | `tfc state show` without args should default to `--latest` | 🟡 | S | ⭐ | TODO |
| 2 | `tfc state outputs` without workspace should auto-detect from context | 🟡 | S | ⭐ | TODO |
| 1 | `tfc project show` without args should resolve project from current workspace | 🟡 | M | ⭐ | TODO |
| 1b | `tfc workspace show` could include project name, last run, health summary | 🟢 | M | 💡 | TODO |
| 6 | `--debug` flag for API call tracing (URLs, response codes, timing) | 🟡 | M | 💡 | TODO |
| 8 | Local file-based response cache with TTL for expensive API calls | 🟢 | L | 💡 | TODO |

Score: 🏆 = do first (high impact, low effort), ⭐ = do next, 💡 = backlog

## Details

### 7. Project find performance (🏆)
`tfc project find 93126-MAN` takes 1m38s. The `ProjectAPI.list()` uses `q=` (substring search)
which still paginates many results. The TFC API supports `filter[names]` for exact name matching.
The `find` command should use `filter[names]` when the pattern has no wildcards, and `q=` only
for substring/wildcard searches.

### 3/4. State outputs arg ambiguity (🏆)
`tfc state outputs` takes a positional arg that's defined as `state_version_id` but users
naturally pass a workspace name or workspace ID. The fix: detect the arg prefix — `sv-` is a
state version ID, `ws-` is a workspace ID, anything else is a workspace name. Or: make the
positional arg the workspace and use `--version` for the state version ID.

### 5. State show default to latest (⭐)
`tfc state show` without args or `--latest` errors. Should default to showing the latest
state version for the auto-detected workspace, same as `tfc state pull` does.

### 2. State outputs auto-detect workspace (⭐)
`tfc state outputs` requires an explicit workspace or state version ID. Should auto-detect
workspace from context (terraform.tf / tfstate) like every other workspace-scoped command.

### 1. Project show from context (⭐)
`tfc project show` without args should resolve: context → workspace → project_id → project.
Requires one extra API call (get workspace, read project_id relationship).

### 1b. Workspace show enrichment (💡)
`tfc workspace show` could include the project name, last run status/age, and a health
summary — similar to `tfc workspace health` but inline in the show output.

### 6. Debug flag (💡)
A `--debug` or `-v` flag that logs API calls (URL, method, status code, timing) to stderr.
Could use Python's `logging` module with `httpx`'s event hooks. Useful for diagnosing
slow commands and understanding what the tool is doing.

### 8. Response caching (💡)
Cache expensive API responses (workspace list, project list, team list) in
`~/.cache/terrapyne/` with a configurable TTL (default 5min). Invalidate on any write
operation. Would make repeated `tfc project show` or `tfc workspace list` near-instant.

Other Findings
- `terraform workspace show` - could show the project, last run status, health status
