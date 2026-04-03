"""Tests that run IDs are never truncated in table output."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from rich.console import Console
from io import StringIO


def _make_run(run_id: str = "run-JJpgJdhM5G8CTAWs"):
    from terrapyne.models.run import Run, RunStatus
    run = MagicMock(spec=Run)
    run.id = run_id
    run.status = RunStatus.PLANNED_AND_FINISHED
    run.created_at = datetime(2026, 4, 1, 8, 55, 0, tzinfo=timezone.utc)
    run.resource_additions = 0
    run.resource_changes = 0
    run.resource_destructions = 0
    run.message = "test run"
    return run


class TestRunIdNotTruncated:

    def _render_to_string(self, runs) -> str:
        from terrapyne.utils.table_renderer import RunTableRenderer
        buf = StringIO()
        con = Console(file=buf, width=120, highlight=False)
        renderer = RunTableRenderer()
        renderer.render(runs, console_instance=con)
        return buf.getvalue()

    def test_full_run_id_appears_in_narrow_terminal(self):
        """Full 22-char run ID must not be truncated even on an 80-col terminal."""
        run_id = "run-JJpgJdhM5G8CTAWs"
        buf = StringIO()
        # 80 columns is a common default terminal width
        con = Console(file=buf, width=80, highlight=False)
        from terrapyne.utils.table_renderer import RunTableRenderer
        RunTableRenderer().render([_make_run(run_id)], console_instance=con)
        output = buf.getvalue()
        assert run_id in output, (
            f"Run ID '{run_id}' was truncated on 80-col terminal.\n"
            f"Got: {output}"
        )

    def test_multiple_run_ids_not_truncated_narrow_terminal(self):
        """All run IDs must appear fully on a narrow terminal."""
        ids = [
            "run-JJpgJdhM5G8CTAWs",
            "run-FyuHSEAGiG8pMSrR",
            "run-qsy3mLdjxe4w4K6d",
        ]
        buf = StringIO()
        con = Console(file=buf, width=80, highlight=False)
        from terrapyne.utils.table_renderer import RunTableRenderer
        RunTableRenderer().render([_make_run(rid) for rid in ids], console_instance=con)
        output = buf.getvalue()
        for rid in ids:
            assert rid in output, f"Run ID '{rid}' truncated on 80-col.\nGot: {output}"
