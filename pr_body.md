## Summary

Establishes world-class open-source standards by rewriting the README for impact, adding community governance files, and restructuring documentation according to the Diataxis framework.

---

## Why

Terrapyne was previously documentation-lite and contained internal brand references. To reach world-class open-source status, it required professional-grade governance and a clear documentation taxonomy.

**Driver:** Open-source readiness and project maturity.

**Alternatives rejected:** 
- **Minimal README:** Ruled out as it failed to convey the higher-order automation value to DevOps engineers.
- **Internal-only docs:** Ruled out to facilitate community contributions.

---

## What changed

Establish documentation hubs and community governance.

**Affected:** README.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, docs/, .github/ISSUE_TEMPLATE/

- Rewrote README.md to emphasize DevOps workflows and SDK type-safety.
- Added CONTRIBUTING.md (with BDD/TDD standards), CODE_OF_CONDUCT.md, and SECURITY.md.
- Restructured `docs/` into Diataxis hubs: Tutorials, How-to, Reference, Explanation.
- Scrubbed all PII and internal brand references (Takeda, oneTakeda, TEC).
- Formalized Double-Loop (BDD + TDD) coherence in engineering guardrails.

---

## Risk and review focus

**Look here first:** Root documentation hubs (`docs/README.md`, `docs/explanation/README.md`, etc.) to ensure navigation is intuitive.

**Edge cases left for later:** Full walkthroughs for all 40+ subcommands are marked as planned.

---

## Testing

**Scenarios tested:**
- Verified all documentation links locally.
- Performed exhaustive grep for brand leaks (0 results).
- Ran `uv run pytest` to confirm zero regressions in test discovery.

**Coverage delta:** No change (documentation-only PR).

---

<details>
<summary>Pre-submission checklist</summary>

**Process**
- [x] PR title follows [Conventional Commits](https://www.conventionalcommits.org/) format
- [x] Commits are atomic — code + tests together in each
- [ ] [TODO.md](TODO.md) updated if this adds new backlog items

**Quality**
- [x] `make test-fast` passes locally (lint + typecheck)
- [x] `make test-all` passes locally (full test suite)
- [x] New code has tests — unit or BDD as appropriate
- [x] `docs/SDK.md` updated if this adds or changes public API

**Security**
- [x] No hardcoded secrets or credentials
- [x] Sensitive values masked in CLI output
- [x] Input validation in place where needed

**GenAI**
- [x] This PR contains code generated with GenAI assistance
- [x] All generated code has been reviewed, tested, and validated

</details>
