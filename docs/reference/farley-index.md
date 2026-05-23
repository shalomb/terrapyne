# Farley Index

Quantitative rubric for evaluating the test suite against Dave Farley's six properties of good tests. Cited from the Ralph and Bart agent personas.

This document is the in-repo reference for the index. The `farley-index` skill in your agent toolkit applies it; this file is what the skill scores against.

## The six properties

| Property | Question it answers |
| -------- | ------------------- |
| **Fast** | Does the suite give feedback in seconds, not minutes? |
| **Maintainable** | Can I refactor production code without rewriting half the tests? |
| **Repeatable** | Does the suite produce the same result every run, on every machine, in any order? |
| **Atomic** | Does each test verify exactly one behaviour? |
| **Necessary** | Is each test demanded by a real requirement? |
| **Understandable** | Can a new contributor read a failure and know what's broken? |

The properties are not independent. A test that's not Repeatable will eventually look not Maintainable (because of the workarounds). A test that's not Atomic is hard to make Understandable.

## Scoring rubric (0-10 per property)

Each property is scored 0-10. The Farley Index is the **arithmetic mean**, not the minimum — because real suites have known weak spots and we want to track movement over time, not pass/fail.

| Score | Meaning |
| ----- | ------- |
| 9-10 | Best in class. Worth holding up as an example. |
| 7-8 | Good. Trustworthy. The default target. |
| 5-6 | Workable but degrading. Plan a remediation epic. |
| 3-4 | Hurting velocity. Block major new work until improved. |
| 0-2 | Actively misleading. The signal is worse than no signal. |

**Target for terrapyne: every property ≥ 7.0.** Below 7.0 on any property is a red flag.

## Per-property scoring guide

### Fast

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Inner loop < 5s, full suite < 30s, no test > 100ms unless explicitly marked `@pytest.mark.slow` |
| 7-8 | Inner loop < 10s, full suite < 60s, occasional outliers documented |
| 5-6 | Full suite > 60s, several tests doing real I/O without justification |
| 3-4 | Full suite > 5 minutes, agents avoid running it locally |
| 0-2 | Full suite is "the CI-only suite" |

**Red flags:** real `httpx.Client` calls in unit tests, `time.sleep()` without `patch("time.sleep")`, `subprocess.run(["terraform", ...])` without `pytest.mark.slow`.

**Tools:** `pytest --durations=10` shows the slowest tests.

### Maintainable

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Tests assert on observable behaviour through public APIs. Renaming an internal symbol breaks zero tests. |
| 7-8 | Most tests behaviour-focused. A handful poke at internals but they're flagged. |
| 5-6 | A non-trivial fraction of tests reference private symbols or specific log lines. |
| 3-4 | Refactoring routinely requires updating dozens of tests with no behaviour change. |
| 0-2 | Mock Tautology — tests verify the mock was called with what the test set up; no real coverage. |

**Red flags:** tests that fail when a private method is renamed, tests that assert on log strings, tests that mock the same module they're testing.

**The Mock Tautology check:** read the test. If you can answer "what bug would this catch?" with "none — it just verifies the mock returns what I told it to", the test is mock-tautological.

### Repeatable

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Suite passes in any order, any seed, on any machine, every time. Verified by CI running shuffled orderings. |
| 7-8 | Order-independent in practice; no known flakies. |
| 5-6 | Occasional flakes blamed on "the network" or "CI being slow". |
| 3-4 | Subset runs produce different results from full runs. (← terrapyne is currently here.) |
| 0-2 | The suite has private knowledge of execution order. Cannot be parallelised. |

**Red flags:** module-level state mutated by tests but not reset (singletons, environment variables, log handlers, monkey-patches), `os.environ` mutations, file system writes without `tmp_path`, current-time dependencies without `freezegun` or equivalent.

**Verification:** run subsets and full suite and compare results. CI should do this on every PR.

### Atomic

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Each test verifies one behaviour. Setup-to-assertion ratio < 3:1. A failure name tells you the bug. |
| 7-8 | Most tests atomic. A few "happy path + smoke check" tests acknowledged. |
| 5-6 | Several tests verify multiple behaviours. Failures require re-reading the test to understand which assertion fired. |
| 3-4 | Common pattern: 50-line setup, 10 unrelated assertions, "test_workspace_full_lifecycle". |
| 0-2 | One test class per file, one method per class, hundreds of lines of mixed concerns. |

**Red flag:** tests with multiple `assert` statements covering unrelated behaviours.

**The "what failed?" check:** read a test name. If it doesn't tell you what bug a failure represents, it's not atomic.

### Necessary

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Every test demanded by a real requirement (BDD scenario, bug regression, public API contract). Removing any test creates a real coverage gap. |
| 7-8 | Most tests necessary. A few coverage-chasers acknowledged. |
| 5-6 | A noticeable number of tests duplicate other tests with different inputs but same behaviour. |
| 3-4 | Coverage-game tests. Lots of `def test_init_works():` style. |
| 0-2 | The suite exists to satisfy `--cov-fail-under`, not to verify correctness. |

**Red flag:** tests that exist only to push coverage; tests for getter/setter behaviour on Pydantic models; tests that re-test the framework rather than the code.

**The bug-regression check:** if a test failed, would there be a real user-visible bug? If not, the test is decorative.

### Understandable

| Score | What it looks like |
| ----- | ------------------ |
| 9-10 | Test names describe behaviour. Arrange/Act/Assert is visually obvious. Magic literals are named. A new contributor can read any test cold. |
| 7-8 | Most tests clear. A few helper-heavy tests need a second read. |
| 5-6 | Tests pass but you have to re-read them to understand what they do. |
| 3-4 | Test names like `test_function_one`, magic numbers, helpers stacked five deep. |
| 0-2 | Failures are mysteries. Debugging a flake takes longer than fixing the bug. |

**Red flag:** test names that describe mechanics (`test_calculate_returns_value`) instead of behaviour (`user_cannot_checkout_with_empty_basket`).

**The "name tells the story" check:** read only the test name. Can you predict what it asserts? If not, rename it.

## Applying the index in this repo

### When Ralph runs it

Before raising a PR (the pre-PR self-audit in the Ralph persona):

```bash
# Use the farley-index skill, or:
pytest --durations=10                       # Fast check
pytest tests/                                # Full pass
pytest tests/ --shuffle  # if pytest-randomly installed
```

Score each property, focus on `Fast` and `Necessary` (Ralph's primary concerns), file MINOR findings on others as observations.

### When Bart runs it

During adversarial review:

```bash
# Same commands, but Bart focuses on Maintainable and Repeatable
# because those are the properties that catch problems CI misses.
```

### When Lisa reads it

Lisa consumes Bart's Retrospective Signal, which includes a Farley score breakdown. Lisa uses it to decide whether the next epic should include test-debt remediation as a foundational task.

## Where this index currently lands

Based on the May 2026 audit (see `PLAN.md` EPIC-001):

| Property | Score | Notes |
| -------- | ----- | ----- |
| Fast | 9 | `make test-fast` ~5s, full suite ~28s |
| Maintainable | 7 | Heavy MagicMock use is appropriate for an HTTP wrapper; some BDD steps assert on output strings (mild Maintainable risk) |
| Repeatable | 4 | Order-dependent failures via console singleton; broken `patch()` site |
| Atomic | 7 | Most tests atomic; some BDD scenarios share fixtures across When/Then in ways that couple steps |
| Necessary | 8 | 84% coverage with 815 tests; clearly calibrated to real behaviour |
| Understandable | 8 | Test names describe behaviour; BDD scenarios read as specs |
| **Index** | **7.2** | Held back almost entirely by Repeatable |

EPIC-001 is the remediation. Once landed, Repeatable should rise to 8-9 and the Index to ~7.8.

## Scoring traps

- **Don't average down rare extreme scores.** A single 2 in Repeatable matters more than three 8s. Note it explicitly.
- **Don't rely on coverage as a Necessary proxy.** 95% coverage of trivial getters has Necessary = 3. 70% coverage of behaviour has Necessary = 9.
- **Don't conflate Fast with cheap.** A 50ms test that hits real S3 is fast — but not Repeatable.

## References

- Dave Farley, *Modern Software Engineering* (2021), Chapters 8-10.
- Skill: `farley-index` (in agent toolkit).
- Companion: `docs/reference/adzic-index.md` (BDD-layer rubric).
