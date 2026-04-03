# Fix TODO — fix/cli-parser-bugs

Bugs identified in FEEDBACK.md, implemented via red-green TDD + ACP.

## Tasks

- [x] **T1** `fix(parser): json stdout via console.print corrupts embedded newlines`
  Use `print()` instead of `console.print()` for JSON output in `run_parse_plan`.
  Acceptance: `tfc run parse-plan fixture --format json` pipes cleanly through `json.loads`.

- [x] **T2** `fix(parser): add stdin support — accept `-` as plan file argument`
  When `PLAN_FILE` is `-`, read from `sys.stdin`.
  Acceptance: `echo "$plan" | tfc run parse-plan -` works end-to-end.

- [x] **T3** `fix(parser): detect TFC 1.12+ structured JSON log and warn`
  When input is all-JSON structured log (no plain-text section), emit a clear
  warning rather than silently returning empty resource_changes.
  Acceptance: structured-log input produces `plan_status: "structured_log"` and a
  warning message; resource_changes is empty but a diagnostic is present.

- [x] **T4** `fix(workspace): context auto-detection — resolved ws discarded in 4 commands`
  `workspace show`, `variables`, `vcs`, `health` all do `org, _ = validate_context()`
  then pass `workspace or ""` downstream. Fix: capture resolved name and use it.
  Acceptance: `tfc workspace show` (no args) from inside a terraform dir returns the
  workspace detail without crashing.

- [x] **T5** `fix(runs): run ID column truncated in table output`
  Rich table truncates run IDs with `…`. Fix: `no_wrap=True` + `min_width=22` on
  the Run ID column in `render_runs`.
  Acceptance: `tfc run list` output contains full run IDs passable directly to
  `tfc run show`.

- [x] **T6** `test(parser): expand fixture-based test suite from 4 → 30 cases`
  Import the 30 sanitized fixtures into `tests/fixtures/plan_outputs/` and add a
  parametrized test covering every fixture file.
  Acceptance: `pytest tests/unit/test_plan_parser.py` runs 30+ cases, all green.

- [x] **T7** `fix(models): Pydantic V2 deprecation — StateVersion class Config`
  Replace `class Config` with `model_config = ConfigDict(...)`.
  Acceptance: `pytest` produces 0 PydanticDeprecatedSince20 warnings.
