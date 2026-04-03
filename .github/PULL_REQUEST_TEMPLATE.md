<!--
  REVIEWER: Start at "Risk and review focus" — that's where the author
  tells you where to look. If "Driver" or "Alternatives rejected" is
  vague, send it back.
-->
<!--
  Terrapyne Pull Request

  Three things this PR body needs to do:
    1. Let a reviewer orient in under 60 seconds — problem, fix, where to look
    2. Show the change is safe to ship — tested scenarios, blast radius
    3. Leave enough context that someone in 18 months doesn't have to reconstruct
       your reasoning from the diff and a Slack thread

  Fill in every section. Delete the > prompt text before opening — it's for you,
  not the reviewer. PRs opened with prompts still visible will be sent back.
-->

## Summary

> One sentence. What was broken or missing, and what does this PR do about it?

closes #<!-- number -->

---

## Why

> What forced this change? Name the alternatives you ruled out and say why.

**Driver:**
<!-- Who hit this problem? What happened? -->

**Alternatives rejected:**
<!-- Name them. "None considered" is wrong. -->

---

## What changed

> What components did you touch? The diff shows lines — this explains what the diff *means*.

**Affected:** <!-- e.g. api/teams.py · cli/workspace_cmd.py · models/run.py -->

<details>
<summary>Breaking changes</summary>

<!-- Delete this section entirely if the PR has no breaking changes. -->

- [ ] This PR has breaking changes — PR title uses `feat!:` or `fix!:`

| Area | Detail |
|------|--------|
| CLI commands | <!-- added / removed / renamed flags or subcommands --> |
| SDK API | <!-- changed method signatures, removed classes --> |
| Models | <!-- changed field names, types, or removed fields --> |

**Migration:**
```python
# Before

# After
```

</details>

---

## Risk and review focus

> Tell the reviewer where to look and what could go wrong.

**Look here first:** <!-- The part most likely to be wrong is... -->

**Edge cases left for later:**
<!-- What did you deliberately skip? Say why. -->

**Skip:** <!-- What looks like it changed but doesn't need manual attention? -->

---

## Testing

> What did you verify beyond what CI checks? Name the scenarios.
> "All tests pass" is not a scenario — CI already tells us that.

**Scenarios tested:**
<!-- e.g. "bulk var-set with 10 KEY=VAL pairs", "clone workspace with no VCS" -->

**Coverage delta:** <!-- e.g. 71% → 74% -->

---

<details>
<summary>Pre-submission checklist</summary>

**Process**
- [ ] PR title follows [Conventional Commits](https://www.conventionalcommits.org/) format
- [ ] Commits are atomic — code + tests together in each
- [ ] [TODO.md](TODO.md) updated if this adds new backlog items

**Quality**
- [ ] `make test-fast` passes locally (lint + typecheck)
- [ ] `make test-all` passes locally (full test suite)
- [ ] New code has tests — unit or BDD as appropriate
- [ ] `docs/SDK.md` updated if this adds or changes public API

**Security**
- [ ] No hardcoded secrets or credentials
- [ ] Sensitive values masked in CLI output
- [ ] Input validation in place where needed

**GenAI**
- [ ] This PR contains code generated with GenAI assistance _(leave unchecked if no GenAI used)_
- [ ] All generated code has been reviewed, tested, and validated

</details>
