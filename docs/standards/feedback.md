# Adversarial Review Feedback

The format Bart uses to give feedback to Ralph. Cited from the Bart agent persona.

## Why a fixed format

Adversarial review without a format degrades into either rubber-stamping or destructive nitpicking. The format makes Bart's feedback **actionable**, **prioritised**, and **bounded** — Ralph can fix what's blocking and park what's not.

The format also enforces JBGE (Just Barely Good Enough): if Bart cannot articulate the *risk* a finding poses, the finding doesn't block merge.

## Two artifacts, one review

Bart produces two outputs per review:

1. **`FEEDBACK.md`** — produced **only when the PR is rejected**. Tactical, for Ralph. Lives in the worktree alongside the PR (e.g. `.worktrees/<branch>/FEEDBACK.md`).

2. **Retrospective Signal** — produced **always**, for Lisa. Goes to `td log <epic-id> --decision` as a structured payload. Lisa reads it before planning the next epic.

This document defines the `FEEDBACK.md` format. The Retrospective Signal format is in `docs/standards/retrospective-signal.md` (TODO).

## FEEDBACK.md template

```markdown
# Review Feedback — <PR title or branch name>

**Reviewer:** Bart
**Date:** YYYY-MM-DD
**Verdict:** REJECTED | CHANGES_REQUESTED
**Source:** <PR URL, or path to worktree>

## Summary

<One paragraph. What did Ralph build? What's the headline reason this isn't ready?>

## Blocking findings

<Required to fix before merge. Each finding follows the What/Why/How/Priority pattern below.>

### B1. <Short title>

**What:** <One sentence describing the issue. Cite file and line.>

**Why:** <The risk. Security, correctness, performance, contract violation. Be specific — "this could break" is not a reason; "this leaks the API token to stderr in debug mode" is.>

**How:** <Concrete fix. Point to the pattern Ralph should follow if one exists in the repo.>

**Priority:** BLOCKER | CRITICAL

### B2. <Next blocking finding…>

…

## Non-blocking findings

<Useful to fix but not gating merge. These are minor or "nice to haves". Ralph should park them in TODO.md if they're worth doing later.>

### N1. <Short title>

**What:** …
**Why:** …
**How:** …
**Priority:** MINOR | NIT

## Tests Bart ran

<What did Bart actually verify, beyond CI? Real adversarial review means running the code with weird inputs, not just reading the diff.>

- [ ] Ran `make test-all` after pulling the branch
- [ ] Tried <specific edge case 1>
- [ ] Tried <specific edge case 2>
- [ ] Read the BDD scenarios for coupling to implementation

## Architectural notes (for Lisa)

<Anything Bart noticed that's not Ralph's fault but Lisa needs to know about. Tech debt surfaced. ADR assumptions that didn't hold. Constraints that need adjusting before the next epic.>
```

## Priority semantics

| Priority | When | Effect |
| -------- | ---- | ------ |
| `BLOCKER` | Security, data loss, correctness, contract violation | PR cannot merge |
| `CRITICAL` | High-likelihood bug under realistic conditions | PR cannot merge |
| `MINOR` | Code quality, future maintenance burden | PR can merge; park in `TODO.md` |
| `NIT` | Style, naming preference | PR can merge; do not park; let it go |

If Bart finds himself classifying half the findings as `BLOCKER`, he is over-blocking. Re-read the design philosophy and JBGE principle in the agent persona.

## What/Why/How/Priority — the four-field rule

Every finding must have all four fields. If Bart can't fill in a field, the finding isn't ready to deliver.

| Field | Bad | Good |
| ----- | --- | ---- |
| **What** | "There's a bug in workspaces.py" | "`workspaces.py:142` calls `get_organization()` without checking the return — passes `None` to `f-string`." |
| **Why** | "It might fail" | "If the user omits `--organization` and no env var is set, the CLI prints `No workspaces in None` instead of a usable error message. Breaks our 'errors must be actionable' contract." |
| **How** | "Fix the bug" | "Use `validate_context()` from `cli/context_helpers.py` — same pattern as `workspace list`. Or raise `ValueError` and let `handle_cli_errors` format it." |
| **Priority** | (omitted) | `BLOCKER` (contract violation) / `MINOR` (cosmetic) |

## What Bart does NOT do

- **Style preferences.** Black/Ruff/MyPy already enforce style. If Bart finds himself debating naming, he stops and either lets it go (NIT) or files a `chore` task to update the lint config.
- **Architectural rewrites the PR didn't propose.** If Bart wants a different architecture, that's a separate epic via Lisa, not feedback on this PR.
- **Tone-policing the commit messages.** If commits violate ACP, file a single finding pointing to `docs/standards/atomic-commit-protocol.md`. Don't repeat it per commit.
- **Re-running the work.** If Bart is rewriting the code in his head, that's not review — that's redoing. Stop, document the gap, hand back.

## Constructive vs destructive — examples

### Destructive (do not write)

> "This is terrible. You hardcoded the timeout. Fix it."

### Constructive (write this)

> **B1. Hardcoded timeout in `runs.py:218`**
>
> **What:** `time.sleep(30)` after a 503 response. Hardcoded.
>
> **Why:** Slow networks (e.g. CI runners on US-East talking to TFC EU) regularly take >30s to recover. We've seen this on PR #92. The retry will give up before the rate limit lifts.
>
> **How:** Use `tenacity.wait_exponential` like the rest of `client.py`. The pattern is in `_request()` lines 198-205.
>
> **Priority:** CRITICAL

The constructive version is the same length but it teaches.

## Self-check before delivering FEEDBACK.md

```
[ ] Every finding has all four fields filled
[ ] Blockers are genuinely blocking (security, correctness, contract)
[ ] At least one of the "Tests Bart ran" boxes is ticked
[ ] No style-only findings escalated above NIT
[ ] Architectural notes are separated from tactical findings
[ ] Tone is constructive throughout
```

If any box is unchecked, the review is not ready to deliver.
