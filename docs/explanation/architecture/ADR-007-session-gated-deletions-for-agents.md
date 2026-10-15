# ADR-007: Session-Gated Deletions for Agents

**Date:** 2026-10-15  
**Status:** Accepted  
**Relates to:** agent_context.py, ADR-006, AX-agent-safety, cli-command-hierarchy.md  

## Context

Terrapyne is increasingly invoked by autonomous AI coding agents (Claude, Gemini, Antigravity, Copilot, Cursor, headless CI pipelines) with tool-calling capabilities.

In human interactive sessions, destructive operations (e.g., deleting a workspace, removing workspace variables or variable sets, deleting a team, or issuing `tfc api -X DELETE`) are guarded by `typer.confirm()` interactive prompts or explicit `--force` / `-y` flags.

In agent and automated contexts:
1. **Interactive prompts fail or deadlock:** Headless subprocesses lack an interactive TTY, resulting in `EOFError` or hangs.
2. **Agents unconditionally pass `--force` / `-f`:** LLMs quickly learn to add `--force` to every command to avoid non-interactive aborts.
3. **Severe blast radius:** When an agent misinterprets a prompt, hallucinates a workspace name, or enters a retry loop, combining autonomous execution with `--force` can irrevocably destroy production state, configurations, or teams in Terraform Cloud.
4. **Command flags are not an agent safety boundary:** If safety relies on a flag (e.g. `--allow-delete`), an autonomous agent seeing the refusal message will simply re-run the command with the flag appended, completely bypassing the human's intent.

To establish a genuine safety boundary, destructive permissions must originate from an **external human grant** attached to the session rather than an in-band CLI argument.

---

## Decision Anchor (The Y-Statement)

| Dimension | Detail |
|---|---|
| **Context** | Autonomous agents invoke destructive CLI commands with `--force`, creating severe risk of unintended resource deletion in TFC. |
| **Constraint(s)** | Safety boundary cannot be bypassed by an agent adding CLI flags (`DRV-01`, `DRV-02`); human interactive UX must remain frictionless (`DRV-04`). |
| **Requirement(s)** | Gated deletion by resource class in agent context with self-documenting refusal and execution wrapper (`DRV-01`, `DRV-03`, `DRV-05`). |
| **Decision** | Implement session-gated deletions via `TERRAPYNE_ALLOW_DELETE` and `tfc harness exec --allow-delete=<class>`. Refuse un-granted deletions before API calls. |
| **Alternatives Rejected** | In-band CLI flags (`--allow-delete`); blanket deletion ban for all agents; interactive prompt fallback in headless sessions. |
| **Rationale** | External session-scoped grants ensure human-in-the-loop authorization without breaking legitimate automation workflows. |
| **Tradeoff Accepted** | Humans running agents for destructive tasks must pre-authorize the session or handle the refusal relay. |
| **Decision Authority** | Lisa (Architecture Agent) & Bart (Reviewer) — 2026-10-15 |

---

## Decision Drivers

- **DRV-01 (Blast Radius Containment):** Destructive actions in automated contexts must be blocked client-side before any network request reaches Terraform Cloud.
- **DRV-02 (External Grant Boundary):** Authorization must be established outside the autonomous agent's loop so the model cannot grant permissions to itself.
- **DRV-03 (Agent Discoverability & Non-Pivoting):** Refusals must clearly explain the grant gap, provide the exact human authorization command, and signal that it is NOT an authentication/network failure (preventing retry loops).
- **DRV-04 (Human Non-Interference):** Humans working interactively at a TTY retain existing confirmation prompts and `--force` flag behaviors without added friction.
- **DRV-05 (Universal Surface Coverage):** Gating must protect both first-class resource commands (`workspace delete`, `team delete`, `var remove`) and the raw HTTP gateway (`tfc api -X DELETE`).

---

## Decision

### 1. Authoritative Signal & Detection
Gating activates whenever `agent_context.detect().is_agent` is `True` (per ADR-006: non-TTY stdout, CI environment, or agent harness).

When `is_agent` is `False`, the CLI operates in interactive human mode (interactive confirmation prompts or `--force` flag bypass).

### 2. Authorization Grant
In an agent context, a deletion is authorized if and only if the resource class is granted in `TERRAPYNE_ALLOW_DELETE` (a comma-separated list of allowed classes or `all`):

```bash
export TERRAPYNE_ALLOW_DELETE=workspace,var
# or
export TERRAPYNE_ALLOW_DELETE=all
```

Alternatively, a human can run an agent or a specific command inside an authorized session wrapper:
```bash
tfc harness exec --allow-delete=workspace -- <command>
```
`tfc harness exec` sets the grant environment variable for the child process.

### 3. Resource Classes
Deletions are classified into discrete operational domains:
- `workspace`: `tfc workspace delete`
- `var`: `tfc workspace var remove`, `tfc workspace var-rm`
- `varset`: `tfc varset remove`
- `team`: `tfc team delete`, `tfc team remove-member`
- `trigger`: `tfc workspace triggers remove`
- `api`: `tfc api <endpoint> -X DELETE`
- `all`: Wildcard granting all deletion classes.

### 4. Refusal Behavior & Contract
If an agent context attempts an unauthorized deletion:
1. **Immediate Abort:** The CLI halts immediately with exit code `1` before dispatching any API call.
2. **Stderr Output (Human/Log Readable):**
   ```text
   Refusal: Deletion of 'workspace' is gated in automated/agent sessions.
   To authorize this deletion, run via:
     tfc harness exec --allow-delete=workspace -- <command>
   or export:
     export TERRAPYNE_ALLOW_DELETE=workspace
   ```
3. **Structured JSON Output (`--format json` or auto-detected agent mode):**
   ```json
   {
     "error": "deletion_gated",
     "resource_class": "workspace",
     "message": "Deletion of 'workspace' is gated in automated/agent sessions.",
     "hints": [
       "Ask the human to authorize this session: tfc harness exec --allow-delete=workspace -- <command>",
       "Or export TERRAPYNE_ALLOW_DELETE=workspace in the host environment"
     ]
   }
   ```
4. **Hard Rule for Agents:** Refusal is a grant gap, NOT an auth failure or a bug. The agent must relay the printed command to the human user rather than attempting to self-authorize or retry.

---

## Multi-Criteria Comparison Matrix

| Evaluation Criteria | Option A: In-Band Flag (`--allow-delete`) | Option B: Blanket Agent Ban | Option C: Session-Scoped Grant (Chosen) |
|---|---|---|---|
| **DRV-01 Blast Radius** | ❌ Fails: LLMs easily append the flag | ✅ Strong: No deletes ever | ✅ Strong: Blocked unless pre-granted |
| **DRV-02 External Boundary** | ❌ None: Agent self-authorizes | ✅ Complete | ✅ Complete: Requires external human opt-in |
| **DRV-03 Agent Usability** | ⚠️ High retry risk | ❌ Breaks legitimate agent automation | ✅ Clear actionable relay message |
| **DRV-04 Human Non-Interference**| ⚠️ Adds extra flags for humans | ✅ No impact on humans | ✅ No impact on humans |
| **DRV-05 Surface Coverage** | ⚠️ Inconsistent flag spread | ❌ Inflexible | ✅ Uniform across CLI verbs and `api -X DELETE` |

---

## Consequences

### Positive
- **Guaranteed containment:** Rogue or hallucinating agents cannot wipe TFC workspaces or variables without prior human sign-off.
- **Zero human friction:** Interactive terminal users see zero change in their daily workflows.
- **Clear remediation paths:** When an agent legitimately needs to delete a resource, the human receives the exact one-liner needed to authorize it.

### Negative / Trade-offs Accepted
- **Pre-configuration required:** Automated CI jobs intended to tear down ephemeral workspaces must set `TERRAPYNE_ALLOW_DELETE=workspace` or run under `tfc harness exec`.
