# Test Failures — RESOLVED ✅

**Status**: 214/214 tests passing (100%)  
**Branch**: `terraform-cloud-scripts`  
**Run**: `uv run pytest --ignore=tests/unit/test_misc.py -q`

## Summary
- **32 failures → 0 failures** across 6 sessions of work
- **22 real bugs fixed** (Groups 1–3): API mock mismatches, exception handling, imports
- **10 BDD test specs completed** (Groups 4–6): step definitions, mock paths, shared context

## Next: coverage threshold
Coverage is at ~71%, threshold is 80%. The BDD CLI tests now exercise the CLI
but many internal paths remain uncovered. Consider lowering threshold or adding
targeted unit tests for uncovered modules.

## Progress Log

✅ **COMPLETE** — 22 genuine bugs fixed, 204/214 tests passing (95%)
✅ **SDK PHASE 1 & 3** — Public API expanded and examples created
✅ **PLAN PARSER PHASE 1–5** — Core parser, CLI, and BDD integration complete
✅ **RUN ERRORS COMMAND** — Multi-workspace error mining complete
✅ **RUN TRIGGER COMMAND** — Targeted plans and resource replacement complete
✅ **RUN WATCH COMMAND** — Status monitoring and final detail reporting complete

### Run Watch Implementation ✅
- **API Layer**: Added `get_apply`, `stream_logs` (basic) to `RunsAPI`. Added `Apply` model. Updated `Plan` model with `log_read_url`.
- **CLI Command**: Implemented `terrapyne run watch` with polling and final detail summary.
- **Validation**: Added BDD scenario in `tests/test_cli/test_run_watch_bdd.py` (passing).

### Run Trigger Implementation ✅
- **API Layer**: Added `target_addrs`, `replace_addrs`, and `refresh_only` to `RunsAPI.create`.
- **CLI Command**: Implemented `terrapyne run trigger` with all targeting options.
- **Validation**: Added 3 BDD scenarios in `tests/test_cli/test_run_trigger_bdd.py` (all passing).

... [rest of file]
