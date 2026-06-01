# ADR-006: TTY-Aware Output Defaults

**Date:** 2026-06-01  
**Status:** Accepted  
**Relates to:** agent_context.py, AX-tty-aware, EPIC-002  

## Context

Terrapyne is used by both humans at interactive terminals and by automated
agents (Claude Code, pi, kiro, agy, CI pipelines, shell scripts). These two
audiences need fundamentally different output:

- **Humans** want rich tables, colour, progress spinners, truncation for
  readability.
- **Automation** wants structured JSON: no ANSI codes, no truncation, no
  progress noise, consistent field names.

The current implementation in `agent_context.py` uses a tiered detection
strategy to decide which mode to use:

- **Tier 1** — explicit env vars (`CI`, `GITHUB_ACTIONS`, `NO_COLOR`, etc.)
- **Tier 2** — known agent harness self-identification (`CLAUDECODE`,
  `PI_CODING_AGENT`, `AWS_EXECUTION_ENV=AmazonQ*`, etc.)
- **Tier 3** — structural inference: `not sys.stdout.isatty()`

Empirical testing across four agents (Claude Code, pi, kiro/Amazon Q, agy)
confirmed that Tier 2 correctly identifies three of them. agy sets no
identifying variable and falls through to Tier 3.

This raises a maintenance concern: the Tier 2 whitelist must be updated every
time a new agent harness emerges. If a new agent is not on the list and happens
to allocate a pseudo-TTY for subprocess calls (as agy may, given `TERM=dumb`),
detection fails silently and the agent receives human-formatted output.

## Decision

**TTY state alone is the authoritative signal for output format selection.**

If `sys.stdout.isatty()` is `False`, JSON output is the default. If it is
`True`, human-readable (tabular/Rich) output is the default. The explicit
`--format` flag always overrides detection in either direction.

The Tier 1/2 agent-specific variables are retained as belt-and-suspenders for
cases where an agent allocates a PTY but still wants JSON (e.g. an agent that
sets `CLAUDECODE=1` but runs with a PTY). They are no longer the primary
detection mechanism and the whitelist is no longer load-bearing.

## Rationale

**If stdout is not a tty, the output is being consumed by a program.**

This is true whether the consumer is an agent, a CI pipeline, `grep`, `jq`,
or a shell script. In all these cases, JSON is the correct output — a human
is not reading it directly in a terminal.

**If stdout is a tty, a human is (probably) watching.**

This is the only case where rich tables, colour, and truncation add value. A
human who wants JSON at a terminal can pass `--format json` explicitly.

**The whitelist cannot be kept current.**

New agent harnesses emerge continuously. The window between "new agent ships"
and "terrapyne ships a whitelist update" means broken output for that agent's
users. The TTY heuristic requires no updates — it works for any agent that
does not allocate a PTY, which is the common case for headless tool invocation.

**`--format` as an explicit override covers all edge cases.**

- Agent running with PTY but wants JSON: set `TERRAPYNE_OUTPUT=json` or pass
  `--format json`.
- Human piping output but wants tables: pass `--format human`.
- CI pipeline needing human-readable logs: pass `--format human`.

## Consequences

### What changes

- `agent_context.detect()` is simplified: Tier 3 (`not isatty()`) becomes the
  primary signal. Tiers 1 and 2 are retained only as overrides for PTY edge
  cases.
- The Tier 2 agent var whitelist is no longer extended. Existing entries remain
  for compatibility but no new entries are added.
- Documentation updated to reflect TTY as the primary contract.

### What does not change

- `--format json` and `--format human` flags continue to work as explicit
  overrides.
- `TERRAPYNE_OUTPUT=json` env var continues to work as an explicit override.
- Rich output (tables, colour, progress) is preserved for interactive terminals.
- The `AgentContext` dataclass and its `reason` field are preserved for
  `--debug` output.

### Trade-offs

- **False positives at the terminal**: a human running `tfc workspace list | grep foo`
  gets JSON. This is acceptable — the output is being consumed by a program
  (`grep`), not read directly. If the human wants a table, they read it first
  then filter: `tfc workspace list` (no pipe).
- **Agents with PTY allocation** (e.g. agy): these must set `TERRAPYNE_OUTPUT=json`
  or `NO_COLOR` explicitly, or rely on Tier 1/2 vars. This is a known limitation,
  documented in the agent integration guide.

## Alternatives Considered

### A1: Keep and grow the Tier 2 whitelist

Extend the list as new agents are identified. Reliable for known agents,
silent failure for unknown ones. Rejected: maintenance burden is unbounded;
new agents break without a terrapyne release.

### A2: TTY only, remove all Tier 1/2 detection

Pure TTY check, no env var overrides. Simpler, but removes the ability for
agents running with a PTY to opt in to JSON. Rejected: too inflexible for
edge cases.

### A3: Opt-in JSON (current partial state)

Require `--format json` explicitly everywhere. Rejected: agents that don't
know to pass the flag get broken output; this is the problem we are solving.

### A5: `TERM=dumb` as a Tier 1 signal

Use `TERM=dumb` to detect PTY-allocating agents that suppress colour (empirically
observed in agy). Rejected: `TERM=dumb` is a legitimate setting for human
terminals — Emacs `M-x shell`, serial terminals, and degraded SSH sessions all
use it. This would silently serve JSON to human users with no way to know why.
agy is correctly caught by Tier 3 when it runs subprocesses without a PTY, which
is the normal headless case.

### A4: `TERRAPYNE_AGENT=1` convention

Ask all agent harnesses to set a single well-known var. Rejected: we have no
ability to mandate this for external tools; same bootstrap problem as the
whitelist.

## Related

- `src/terrapyne/cli/agent_context.py`
- ADR-002: Run Model Enrichment
- `docs/explanation/design-philosophy.md` — TTY-aware output principle
- EPIC-002: Honour the Documented Automation Contract
- TODO: AX-tty-aware
