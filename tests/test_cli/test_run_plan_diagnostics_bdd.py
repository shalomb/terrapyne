"""BDD steps for plan diagnostics and module health alerts in `tfc run show`."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

from terrapyne.api.runs import RunsAPI
from terrapyne.cli.main import app
from terrapyne.models.plan import Plan
from terrapyne.models.run import Run, RunStatus

scenarios("../features/run_plan_diagnostics.feature")

runner = CliRunner()

_SAMPLE_DEPRECATED_LOG = """
Terraform v1.14.6
{"@level":"warn","@message":"Module version 1.4.0 of app.terraform.io/Takeda/EC2/aws is deprecated","@module":"terraform.ui","@timestamp":"2026-10-15T07:40:05Z","diagnostic":{"severity":"warning","summary":"Module version 1.4.0 of app.terraform.io/Takeda/EC2/aws is deprecated","detail":"This version is deprecated. Please upgrade to the latest stable version.","extra":{"type":"module_version_deprecation","version":"1.4.0","source_name":"app.terraform.io/Takeda/EC2/aws","link":"","deprecation_message":"This version is deprecated. Please upgrade to the latest stable version."}},"type":"diagnostic"}
{"@level":"info","@message":"Plan: 0 to add, 0 to change, 0 to destroy.","type":"change_summary"}
"""

_SAMPLE_CLEAN_LOG = """
Terraform v1.14.6
{"@level":"info","@message":"Plan: 0 to add, 0 to change, 0 to destroy.","type":"change_summary"}
"""

_SAMPLE_ERROR_LOG = """
Terraform v1.14.6
{"@level":"error","@message":"Error: Missing required argument","@module":"terraform.ui","diagnostic":{"severity":"error","summary":"Missing required argument","detail":"The argument \\"vpc_id\\" is required."},"type":"diagnostic"}
"""


@pytest.fixture
def api():
    mock_client = MagicMock()
    runs_api = RunsAPI(mock_client)
    runs_api.get = MagicMock()
    runs_api.get_plan = MagicMock()
    runs_api.get_plan_logs = MagicMock()
    mock_client.runs = runs_api
    return mock_client


@given("a terraform cloud organization is accessible")
def _org_accessible():
    pass


@given(parsers.parse('a finished run "{run_id}" with deprecated module alerts in its plan log'))
def _run_with_deprecated_modules(api, run_id):
    plan_id = f"plan-{run_id}"
    run = Run(
        id=run_id,
        status=RunStatus.PLANNED_AND_FINISHED,
        plan_id=plan_id,
        message="Test run with deprecations",
    )
    plan = Plan(
        id=plan_id,
        status="finished",
        log_read_url="https://archivist.terraform.io/v1/object/mock-dep",
    )
    api.runs.get.return_value = run
    api.runs.get_plan.return_value = plan
    api.runs.get_plan_logs.return_value = _SAMPLE_DEPRECATED_LOG


@given(parsers.parse('a finished run "{run_id}" with no diagnostics in its plan log'))
def _run_clean(api, run_id):
    plan_id = f"plan-{run_id}"
    run = Run(
        id=run_id,
        status=RunStatus.PLANNED_AND_FINISHED,
        plan_id=plan_id,
        message="Test clean run",
    )
    plan = Plan(
        id=plan_id,
        status="finished",
        log_read_url="https://archivist.terraform.io/v1/object/mock-clean",
    )
    api.runs.get.return_value = run
    api.runs.get_plan.return_value = plan
    api.runs.get_plan_logs.return_value = _SAMPLE_CLEAN_LOG


@given(parsers.parse('an errored run "{run_id}" with an error diagnostic in its plan log'))
def _run_error(api, run_id):
    plan_id = f"plan-{run_id}"
    run = Run(
        id=run_id,
        status=RunStatus.ERRORED,
        plan_id=plan_id,
        message="Test errored run",
    )
    plan = Plan(
        id=plan_id,
        status="errored",
        log_read_url="https://archivist.terraform.io/v1/object/mock-err",
    )
    api.runs.get.return_value = run
    api.runs.get_plan.return_value = plan
    api.runs.get_plan_logs.return_value = _SAMPLE_ERROR_LOG


@when(parsers.parse('I run "{command}"'), target_fixture="result")
def _run_command(api, command):
    argv = command.split()[1:]
    with (
        patch("terrapyne.cli.run_cmd.get_client") as get_client,
        patch("terrapyne.cli.run_cmd.validate_context", return_value=("test-org", None)),
    ):
        get_client.return_value.__enter__.return_value = api
        return runner.invoke(app, [*argv, "-o", "test-org"])


@then(parsers.parse('the output should display "{text}"'))
def _output_contains(result, text):
    assert text in result.output, f"Expected {text!r} in output:\n{result.output}"


@then(parsers.parse('the output should not display "{text}"'))
def _output_does_not_contain(result, text):
    assert text not in result.output, f"Did not expect {text!r} in output:\n{result.output}"


@then(
    parsers.parse('the output should list the deprecated module "{module}" and version "{version}"')
)
def _output_lists_module_version(result, module, version):
    assert module in result.output, f"Expected module {module!r} in output:\n{result.output}"
    assert version in result.output, f"Expected version {version!r} in output:\n{result.output}"


@then('the JSON output should contain a "diagnostics" list')
def _json_contains_diagnostics(result):
    data = json.loads(result.output)
    assert "diagnostics" in data, f"'diagnostics' missing from JSON:\n{result.output}"
    assert isinstance(data["diagnostics"], list)
    assert len(data["diagnostics"]) > 0


@then(parsers.parse('the diagnostics should include category "{category}"'))
def _diagnostics_include_category(result, category):
    data = json.loads(result.output)
    categories = [d.get("category") for d in data.get("diagnostics", [])]
    assert category in categories, f"Category {category!r} not in {categories}"


@then("no plan logs should be fetched")
def _no_logs_fetched(api):
    api.runs.get_plan_logs.assert_not_called()


@then(parsers.parse('the output should show the diagnostic error summary "{summary}"'))
def _output_shows_error_summary(result, summary):
    assert summary in result.output, (
        f"Expected error summary {summary!r} in output:\n{result.output}"
    )


@then(parsers.parse("exit code should be {code:d}"))
def _exit_code(result, code):
    assert result.exit_code == code, (
        f"Expected exit code {code}, got {result.exit_code}:\n{result.output}"
    )


@then("the output should be a JSON array with diagnostics")
def _output_json_array(result):
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "severity" in data[0]
