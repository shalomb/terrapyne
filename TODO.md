# TODO — Exploratory Testing Findings

Bugs and improvements found during exploratory testing against live TFC.

## Priority Matrix

Effort: S (< 30min), M (1-2h), L (half day+)
Impact: 🔴 High (broken/unusable), 🟡 Medium (annoying), 🟢 Low (nice-to-have)

| # | Finding | Impact | Effort | Score | Status |
|---|---|---|---|---|---|
| 7 | `tfc project find` takes 1m38s — use `filter[names]` for exact match | 🔴 | S | 🏆 | ✅ PR #20 |
| 3 | `tfc state outputs 'workspace-name'` errors — arg treated as state version ID | 🔴 | S | 🏆 | ✅ PR #21 |
| 4 | `tfc state outputs 'ws-ID'` errors — same arg ambiguity | 🔴 | S | 🏆 | ✅ PR #21 |
| 5 | `tfc state show` without args should default to latest | 🟡 | S | ⭐ | ✅ PR #21 |
| 2 | `tfc state outputs` without workspace should auto-detect from context | 🟡 | S | ⭐ | ✅ PR #21 |
| 1 | `tfc project show` without args should resolve project from current workspace | 🟡 | M | ⭐ | TODO |
| 1b | `tfc workspace show` could include project name, last run, health summary | 🟢 | M | 💡 | TODO |
| 6 | `--debug` flag for API call tracing (URLs, response codes, timing) | 🟡 | M | 💡 | TODO |
| 8 | Local file-based response cache with TTL for expensive API calls | 🟢 | L | 💡 | TODO |

## Remaining Details

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
