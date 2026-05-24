# Adzic Index

Quantitative rubric for evaluating BDD feature files against Gojko Adzic's Specification by Example principles. The companion to the Farley Index.

This document is the in-repo reference for the index. The `adzic-index` skill in your agent toolkit applies it; this file is what the skill scores against.

## Why this exists

Farley measures whether unit tests are trustworthy. Adzic measures whether the BDD layer **communicates the right thing to the right people**.

The question shifts from "do our scenarios pass?" to "do our scenarios describe what the user actually needs, in language the user can read?"

## The six dimensions

| Dimension | Question it answers |
| --------- | ------------------- |
| **Business-Readable** | Can a non-technical stakeholder understand this scenario without explanation? |
| **Intention-Revealing** | Does the scenario describe *why* the system does this? |
| **Living** | Is every step backed by a real implementation? |
| **Declarative** | Does the scenario describe *what*, not *how*? |
| **Focused** | Does each scenario test exactly one behaviour? |
| **Atomic** | Can scenarios run in any order, with no shared state? |

## Scoring rubric (0-10 per dimension)

Same scoring scale as the Farley Index. The Adzic Index is the arithmetic mean across the six dimensions.

| Score | Meaning |
| ----- | ------- |
| 9-10 | Best in class. Could be shown to a stakeholder cold. |
| 7-8 | Good. Stakeholder-readable with minor jargon. |
| 5-6 | Workable but degrading; tests behave like UI scripts in places. |
| 3-4 | Reads as test code wearing Gherkin syntax. |
| 0-2 | Imperative test steps; no business value. |

**Target for terrapyne: every dimension ≥ 7.0.** Below 7.0 on any dimension is a red flag.

## Per-dimension scoring guide

### Business-Readable

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Reads as plain English. No HTTP verbs, no class names, no SQL. A product manager can validate it. |
| 7-8 | Mostly readable; occasional domain jargon (`workspace`, `run`, `project`) which is appropriate. |
| 5-6 | Mixes domain language with implementation terms (`API call`, `JSON response`). |
| 3-4 | References method names, status codes, internal symbols. |
| 0-2 | "Given the database row…" / "When the function returns…" |

**Test:** read a scenario aloud to someone who's never seen the code. Did they understand it without you stopping to explain?

### Intention-Revealing

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Every scenario carries the `As a / I want / So that` framing or its meaning. The *why* is visible. |
| 7-8 | The why is often visible; some scenarios assume context. |
| 5-6 | Scenario titles describe what the test does, not why the user wants it. |
| 3-4 | Titles like "Test scenario 1", "Empty input case", "Edge case 4". |
| 0-2 | Scenarios are anonymous behaviours, no user, no goal. |

**Test:** read only the `Feature` line and the `Scenario` titles. Could a stakeholder pick a scenario based on its title alone?

### Living

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Every scenario in the suite is executable today. Zero `@pending`, zero skipped, zero TODO scenarios. |
| 7-8 | A handful of `@pending` scenarios with explicit ticket references. |
| 5-6 | Several `@pending` or `@skip` scenarios; some have been pending for months. |
| 3-4 | The "documented but not executed" pile is larger than the executed pile. |
| 0-2 | Feature files are documentation that's never been run. |

**Test:** `grep -r '@pending\|@skip' tests/features/`. The result should be empty or trivially short.

**terrapyne current:** zero `@pending`/`@skip` tags. ✅ 9-10 today.

### Declarative

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Steps describe state and outcome. Never a click, never a keystroke, never an HTTP verb. |
| 7-8 | Mostly declarative; rare imperatives in `When` steps to set up complex state. |
| 5-6 | `When I click X, then I press Y, then I wait` patterns. |
| 3-4 | Scenarios read as Selenium scripts in Gherkin. |
| 0-2 | Implementation is so leaked that the scenario is locked to one UI. |

**Red flags:** `When I click`, `When I press`, `When I navigate to`, `When I send a POST request`, `When I select from dropdown`.

**terrapyne current:** zero UI-script patterns. ✅ 9-10 today.

### Focused

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Each scenario tests one rule. Given:Then ratio under 3:1. |
| 7-8 | Most scenarios focused; some "happy path" scenarios bundle related assertions. |
| 5-6 | Several scenarios test multiple behaviours. Hard to name them precisely. |
| 3-4 | "Full lifecycle" scenarios that bundle 5+ behaviours. |
| 0-2 | Scenarios are smoke tests pretending to be specifications. |

**Red flag:** scenario titles containing "and", multiple `Then` steps with unrelated assertions.

### Atomic

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Scenarios share no state. Run order is irrelevant. Every scenario sets up its own context. |
| 7-8 | `Background:` is used appropriately for shared setup; no hidden coupling. |
| 5-6 | Some scenarios depend on side effects of earlier scenarios. |
| 3-4 | Suite has a "must run in this order" property. |
| 0-2 | Scenario coupling is so deep that re-ordering breaks the suite. |

**Red flag:** scenarios that pass alone but fail together (or vice versa).

## Applying the index in this repo

### When Marge runs it

Before handing a feature brief to Lisa, Marge audits her own scenarios:

```bash
# Use the adzic-index skill, or:
grep -rn "click\|press\|navigate" tests/features/         # UI-script red flag
grep -rn "@pending\|@skip" tests/features/                # Living red flag
grep -rn "API\|HTTP\|status code" tests/features/         # Implementation leak
```

Marge focuses on Business-Readable and Intention-Revealing — those are her dimensions.

### When Ralph runs it

When writing step definitions, Ralph audits Declarative and Living: every Gherkin step must have a real implementation, and the implementation must verify the *outcome*, not the implementation path.

### When Bart runs it

During review, Bart spot-checks Focused (no scenario doing too much) and Atomic (no order coupling). If Bart finds a coupled scenario, that's a `MINOR` finding unless it actually causes flakes (then `BLOCKER`).

## Where this index currently lands

Based on the May 2026 audit (see solution review notes):

| Dimension | Score | Notes |
| --------- | ----- | ----- |
| Business-Readable | 8 | Domain language used appropriately; no HTTP/class jargon |
| Intention-Revealing | 8 | `As a / I want / So that` framing throughout |
| Living | 9 | Zero `@pending`, zero skipped scenarios |
| Declarative | 9 | No UI-script patterns anywhere |
| Focused | 7 | `workspace.feature` (266 lines) is too broad — split underway |
| Atomic | 7 | Mostly atomic; the order-dependence issue is at the Farley layer (console singleton), not at the BDD layer |
| **Index** | **8.0** | Strong overall; weakness is concentrated in Focused |

## Scoring traps

- **Don't grade Living high just because tests pass.** A passing test that's coupled to implementation can be both Living = 9 and Declarative = 3. Score them independently.
- **`Background:` does not lower Atomic.** Used appropriately, it's the canonical way to share setup. It only lowers Atomic when scenarios depend on it implicitly via global state.
- **Domain jargon is allowed.** "Workspace" and "run" are domain terms in TFC; they're Business-Readable for the right audience. "API request" and "POST" are not.

## References

- Gojko Adzic, *Specification by Example* (2011).
- Skill: `adzic-index` (in agent toolkit).
- Companion: `docs/reference/farley-index.md` (TDD-layer rubric).
- Internal: `docs/explanation/bdd-specifications.md` (how-to for writing scenarios).
