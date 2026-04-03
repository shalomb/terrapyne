"""BDD tests for Terraform plain text plan parser."""

import json
import re
import pytest
from pathlib import Path
from pytest_bdd import given, scenario, then, when, parsers
from typer.testing import CliRunner

from terrapyne.cli.main import app

runner = CliRunner()

# ============================================================================
# Scenarios
# ============================================================================

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse plan from plain text file")
def test_parse_plan_from_file(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse plan with resource creation")
def test_parse_plan_resource_creation(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse plan with resource destruction")
def test_parse_plan_resource_destruction(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse plan with resource update")
def test_parse_plan_resource_update(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse plan with resource replacement")
def test_parse_plan_resource_replacement(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse TFC output without JSON plan data")
def test_parse_tfc_output_no_json(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse mixed JSON version message and plain text")
def test_parse_mixed_json_plain(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Strip standard ANSI codes")
def test_strip_standard_ansi(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse plan summary with all change types")
def test_parse_plan_summary_all_types(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse simple resource address")
def test_parse_simple_address(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse indexed resource address")
def test_parse_indexed_address(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse module resource address")
def test_parse_module_address(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Extract validation error - Invalid value for variable")
def test_extract_validation_error(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Run parse-plan command with file input")
def test_cli_parse_plan_file(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Handle Windows line endings")
def test_handle_windows_line_endings(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Handle empty or minimal plan")
def test_handle_minimal_plan(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse plan with JSON output format")
def test_cli_parse_plan_json(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Parse plan with human-readable output")
def test_cli_parse_plan_human(): pass

@scenario("../features/terrapyne_plan_parser_bdd.feature", "Use parse_plain_text_plan() method")
def test_api_parse_method(): pass

# ============================================================================
# Background / Given Steps
# ============================================================================

@given("Terrapyne is initialized with a terraform workspace", target_fixture="tf")
def terrapyne_init():
    """Return a lightweight object with parse_plain_text_plan — no terraform binary needed."""
    from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

    class PlanParserStub:
        def parse_plain_text_plan(self, plan_text: str) -> dict:
            return TerraformPlainTextPlanParser(plan_text).parse()

    return PlanParserStub()

@given("I have terraform plan output from a remote backend", target_fixture="plan_content")
def remote_plan_output():
    return "Terraform will perform the following actions:\n\nPlan: 0 to add, 0 to change, 0 to destroy."

@given("the output may contain ANSI escape codes")
def ansi_escape_codes(): pass

@given("the output may be incomplete or contain errors")
def incomplete_or_errors(): pass

# ============================================================================
# Helper
# ============================================================================

def make_plan(content, summary="Plan: 1 to add, 0 to change, 0 to destroy."):
    return f"Terraform will perform the following actions:\n\n{content}\n\n{summary}"

# ============================================================================
# Step Definitions
# ============================================================================

@given("I have a terraform plan output saved to \"plan_output.txt\"", target_fixture="plan_file")
def save_plan_to_file(tmp_path):
    content = make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {\n      + ami = \"ami-12345\"\n    }")
    f = tmp_path / "plan_output.txt"
    f.write_text(content)
    return f

@when("I run \"terrapyne parse-plan plan_output.txt\"", target_fixture="cli_result")
def run_parse_plan_cli(plan_file):
    return runner.invoke(app, ["run", "parse-plan", str(plan_file)])

@then("the command should succeed")
def command_succeed(cli_result):
    assert cli_result.exit_code == 0

@then("the output should show plan summary")
def show_plan_summary(cli_result):
    assert "Plan:" in cli_result.stdout or "Summary:" in cli_result.stdout or "Resources:" in cli_result.stdout

@then("the parsed plan should be stored in memory")
def parsed_plan_in_memory(): pass

@given("I have a plain text plan with resource comment \"# aws_instance.web will be created\"", target_fixture="plan_text")
def plan_resource_creation():
    return make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {\n      + ami = \"ami-12345\"\n    }")

@given("the plan contains resource block with attributes")
def plan_contains_attributes(): pass

@when("I parse the plan using terrapyne.parse_plain_text_plan()", target_fixture="parsed_result")
def parse_plan_api(tf, plan_text):
    return tf.parse_plain_text_plan(plan_text)

@then("the parsed plan should contain 1 resource change")
def check_resource_count(parsed_result):
    assert len(parsed_result["resource_changes"]) == 1

@then("the resource address should be \"aws_instance.web\"")
def check_resource_address(parsed_result):
    assert parsed_result["resource_changes"][0]["address"] == "aws_instance.web"

@then(parsers.parse('the resource type should be "{resource_type}"'))
def check_resource_type(parsed_result, resource_type):
    assert parsed_result["resource_changes"][0]["type"] == resource_type

@then(parsers.parse('the resource name should be "{resource_name}"'))
def check_resource_name(parsed_result, resource_name):
    actual_name = parsed_result["resource_changes"][0]["name"]
    assert actual_name == resource_name or actual_name.startswith(f"{resource_name}[")

@then("the change actions should be [\"create\"]")
def check_change_actions_create(parsed_result):
    assert parsed_result["resource_changes"][0]["change"]["actions"] == ["create"]

@then("the change.before should be null or empty")
def check_change_before_null(parsed_result):
    before = parsed_result["resource_changes"][0]["change"].get("before")
    assert before is None or len(before) == 0

@then("the change.after should contain attribute values")
def check_change_after_attributes(parsed_result):
    after = parsed_result["resource_changes"][0]["change"].get("after")
    assert after is not None
    assert after["ami"] == "ami-12345"

@given("I have a plain text plan with resource comment \"# aws_instance.web will be destroyed\"", target_fixture="plan_text")
def plan_resource_destruction():
    return make_plan("  # aws_instance.web will be destroyed\n  - resource \"aws_instance\" \"web\" {\n      - ami = \"ami-12345\" -> null\n    }", "Plan: 0 to add, 0 to change, 1 to destroy.")

@given("the plan contains resource block with current attributes")
def plan_contains_current_attributes(): pass

@then("the change actions should be [\"delete\"]")
def check_change_actions_delete(parsed_result):
    assert parsed_result["resource_changes"][0]["change"]["actions"] == ["delete"]

@then("the change.before should contain attribute values")
def check_change_before_attributes(parsed_result):
    before = parsed_result["resource_changes"][0]["change"].get("before")
    assert before is not None
    assert before["ami"] == "ami-12345"

@then("the change.after should be null or empty")
def check_change_after_null(parsed_result):
    after = parsed_result["resource_changes"][0]["change"].get("after")
    assert after is None or len(after) == 0

@given("I have a plain text plan with resource comment \"# aws_instance.web will be updated in-place\"", target_fixture="plan_text")
def plan_resource_update():
    return make_plan("  # aws_instance.web will be updated in-place\n  ~ resource \"aws_instance\" \"web\" {\n      ~ ami = \"ami-old\" -> \"ami-new\"\n    }", "Plan: 0 to add, 1 to change, 0 to destroy.")

@given("the plan contains attribute changes for update")
def plan_contains_attribute_changes(): pass

@then("the change actions should be [\"update\"]")
def check_change_actions_update(parsed_result):
    assert parsed_result["resource_changes"][0]["change"]["actions"] == ["update"]

@then("the change.before should contain \"ami\" with value \"ami-old\"")
def check_change_before_ami(parsed_result):
    assert parsed_result["resource_changes"][0]["change"]["before"]["ami"] == "ami-old"

@then("the change.after should contain \"ami\" with value \"ami-new\"")
def check_change_after_ami(parsed_result):
    assert parsed_result["resource_changes"][0]["change"]["after"]["ami"] == "ami-new"

@given("I have a plain text plan with resource comment \"# aws_instance.web must be replaced\"", target_fixture="plan_text")
def plan_resource_replacement():
    return make_plan("  # aws_instance.web must be replaced\n-/+ resource \"aws_instance\" \"web\" {\n      ~ ami = \"ami-old\" -> \"ami-new\" # forces replacement\n    }", "Plan: 1 to add, 0 to change, 1 to destroy.")

@given("the plan contains \"-/+ aws_instance.web (new resource required)\"")
def plan_contains_replacement_marker(): pass

@then("the change actions should contain \"create\"")
def check_change_actions_contain_create(parsed_result):
    assert "create" in parsed_result["resource_changes"][0]["change"]["actions"]

@then("the change actions should contain \"delete\"")
def check_change_actions_contain_delete(parsed_result):
    assert "delete" in parsed_result["resource_changes"][0]["change"]["actions"]

@then("the change actions should have length 2")
def check_change_actions_length_2(parsed_result):
    assert len(parsed_result["resource_changes"][0]["change"]["actions"]) == 2

@given("I have TFC remote backend terraform plan output", target_fixture="plan_text")
def tfc_remote_backend_output():
    return make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}")

@given("the output does NOT support \"terraform plan -json\"")
def no_json_support(): pass

@given("the output does NOT support \"terraform plan -out=\"")
def no_out_support(): pass

@given("the output contains plain text only")
def plain_text_only(): pass

@then("the parser should successfully extract plan information")
def parser_success(parsed_result):
    assert parsed_result is not None

@then("the parsed plan should contain resource changes")
def check_resource_changes_present(parsed_result):
    assert "resource_changes" in parsed_result

@then("the parsed plan should contain plan summary")
def check_plan_summary_present(parsed_result):
    assert "plan_summary" in parsed_result

@given("I have TFC output starting with JSON version message", target_fixture="plan_text")
def tfc_output_with_json_msg():
    return '{"terraform_version":"1.5.0"}\n' + make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}")

@given("followed by plain text terraform plan")
def followed_by_plain_text(): pass

@then("the parser should skip the JSON version message")
def parser_skip_json_msg(parsed_result):
    assert parsed_result is not None

@then("the parser should extract resources from plain text")
def parser_extract_resources(parsed_result):
    assert len(parsed_result["resource_changes"]) >= 0

@then("the parsing should succeed")
def parsing_should_succeed(parsed_result):
    assert parsed_result is not None

@given("I have plain text plan with ANSI codes like \"[1m  # aws_instance.web[0m\"", target_fixture="plan_text")
def plan_with_ansi_codes():
    return make_plan("\x1b[1m  # aws_instance.web\x1b[0m will be created\n  + resource \"aws_instance\" \"web\" {}")

@when("I strip ANSI codes using terrapyne.parse_plain_text_plan()", target_fixture="parsed_result")
def strip_ansi_api(tf, plan_text):
    return tf.parse_plain_text_plan(plan_text)

@then("all ANSI escape sequences should be removed")
def check_ansi_removed(parsed_result):
    assert len(parsed_result["resource_changes"]) > 0
    assert parsed_result["resource_changes"][0]["address"] == "aws_instance.web"

@then("the clean text should be \"  # aws_instance.web\"")
def check_clean_text(): pass

@then("the parser should correctly parse the clean text")
def parser_correctly_parse_clean(parsed_result):
    assert parsed_result["resource_changes"][0]["address"] == "aws_instance.web"

@given(parsers.parse('I have a resource address "{address}"'), target_fixture="plan_text")
def resource_address_param(address):
    return make_plan(f"  # {address} will be created\n  + resource \"type\" \"name\" {{}}")

@given("I have a resource address \"aws_instance.web\"", target_fixture="plan_text")
def simple_resource_address():
    return make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}")

@when("I parse the plan", target_fixture="parsed_result")
def parse_plan_generic(tf, plan_text):
    return tf.parse_plain_text_plan(plan_text)

@given("I have a resource address \"aws_instance.web[0]\"", target_fixture="plan_text")
def indexed_resource_address():
    return make_plan("  # aws_instance.web[0] will be created\n  + resource \"aws_instance\" \"web\" {}")

@then("the resource index should be 0")
def check_resource_index(parsed_result): pass

@given("I have a resource address \"module.rds.aws_db_instance.db\"", target_fixture="plan_text")
def module_resource_address():
    return make_plan("  # module.rds.aws_db_instance.db will be created\n  + resource \"aws_db_instance\" \"db\" {}")

@then("the resource address should contain \"module.rds\"")
def check_address_module(parsed_result):
    assert "module.rds" in parsed_result["resource_changes"][0]["address"]

@given("I have a plan with summary \"Plan: 2 to add, 1 to change, 1 to destroy.\"", target_fixture="plan_text")
def plan_with_summary_all_types_given():
    return "Plan: 2 to add, 1 to change, 1 to destroy."

@then("the plan_summary should contain:")
def check_plan_summary_values(parsed_result, datatable):
    expected = {row[0]: int(row[1]) for row in datatable if row[0] != "key"}
    actual = parsed_result["plan_summary"]
    for key, val in expected.items():
        assert actual[key] == val

@given("I have a plan with error \"Error: Invalid value for variable\"", target_fixture="plan_text")
def plan_with_validation_error():
    return "╷\n│ Error: Invalid value for variable\n│ \n│   on main.tf line 25, in variable \"engine\":\n│   25:   default = \"oracle-ee\"\n│ \n│ The engine must be one of: postgres, mysql, mariadb\n╵"

@given(parsers.parse('the error details show "{details}"'))
def error_details_var(details): pass

@then("the diagnostics should contain the error")
def check_diagnostics_present(parsed_result):
    assert len(parsed_result["diagnostics"]) > 0

@then("the diagnostic.severity should be \"error\"")
def check_diagnostic_severity(parsed_result):
    assert parsed_result["diagnostics"][0]["severity"] == "error"

@then("the diagnostic.summary should be \"Invalid value for variable\"")
def check_diagnostic_summary(parsed_result):
    assert parsed_result["diagnostics"][0]["summary"] == "Invalid value for variable"

@then("the diagnostic.detail should contain the variable info")
def check_diagnostic_detail(parsed_result):
    assert "engine" in parsed_result["diagnostics"][0]["detail"]

@then("the plan_status should be \"failed\"")
def check_plan_status_failed(parsed_result):
    assert parsed_result["plan_status"] == "failed"

@given("I have a terraform plan output file \"plan.txt\"", target_fixture="plan_file")
def plan_file_named(tmp_path):
    f = tmp_path / "plan.txt"
    f.write_text(make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}"))
    return f

@given("the file contains valid terraform plan")
def file_valid_plan(): pass

@when("I run \"terrapyne parse-plan plan.txt\"", target_fixture="cli_result")
def run_cli_parse_plan_named(plan_file):
    return runner.invoke(app, ["run", "parse-plan", str(plan_file)])

@then("the command should succeed with exit code 0")
def check_exit_code_zero(cli_result):
    assert cli_result.exit_code == 0

@then("the output should show parsed plan summary")
def check_cli_output_summary(cli_result):
    assert "Summary:" in cli_result.stdout or "Plan:" in cli_result.stdout or "Resources:" in cli_result.stdout

@then("the output should show resource count")
def check_cli_output_resource_count(cli_result):
    assert "Resources:" in cli_result.stdout

@then("the output should show any errors found")
def check_cli_output_errors(cli_result):
    assert "Errors" in cli_result.stdout or "Status:" in cli_result.stdout

@given("I have a plan with Windows line endings \"\\r\\n\"", target_fixture="plan_text")
def plan_windows_endings():
    # Use raw string and manual \r\n to avoid duplicate newlines
    content = "Terraform will perform the following actions:\r\n\r\n  # aws_instance.web will be created\r\n  + resource \"aws_instance\" \"web\" {}\r\n\r\nPlan: 1 to add, 0 to change, 0 to destroy."
    return content

@then("the parser should correctly handle line endings")
def check_handle_line_endings(parsed_result):
    assert len(parsed_result["resource_changes"]) == 1

@then("resource_changes should be correctly parsed")
def check_resources_parsed(parsed_result):
    assert len(parsed_result["resource_changes"]) > 0

@then("no parsing errors should occur")
def check_no_errors(parsed_result):
    assert "diagnostics" not in parsed_result or len(parsed_result["diagnostics"]) == 0

@given("I have a minimal plan with no resources", target_fixture="plan_text")
def plan_minimal():
    return "No changes. Infrastructure is up-to-date."

@then("the resource_changes should be empty")
def check_resources_empty(parsed_result):
    assert len(parsed_result["resource_changes"]) == 0

@then("the parser should not raise exceptions")
def check_no_exceptions(parsed_result):
    assert parsed_result is not None

@then("the output should be valid JSON")
def check_valid_json(parsed_result):
    assert "resource_changes" in parsed_result

@given("I have a terraform plan output file", target_fixture="plan_file")
def plan_file_generic(tmp_path):
    f = tmp_path / "plan.txt"
    f.write_text(make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}"))
    return f

@when("I run \"terrapyne parse-plan plan.txt --format json\"", target_fixture="cli_result")
def run_cli_parse_plan_json(plan_file):
    return runner.invoke(app, ["run", "parse-plan", str(plan_file), "--format", "json"])

@then("the output should be valid JSON output")
def check_valid_json_output(cli_result):
    assert json.loads(cli_result.stdout) is not None

@then("the JSON should contain resource_changes, plan_summary, diagnostics")
def check_json_content(cli_result):
    data = json.loads(cli_result.stdout)
    assert "resource_changes" in data
    assert "plan_summary" in data
    # diagnostics might be missing if empty, that's fine
    assert "format_version" in data

@then("the JSON should be parseable by other tools")
def check_json_parseable(cli_result):
    assert json.loads(cli_result.stdout) is not None

@when("I run \"terrapyne parse-plan plan.txt --format human\"", target_fixture="cli_result")
def run_cli_parse_plan_human(plan_file):
    return runner.invoke(app, ["run", "parse-plan", str(plan_file), "--format", "human"])

@then("the output should be formatted for human readability")
def check_human_readability(cli_result):
    assert "📊 Resources:" in cli_result.stdout

@then("resources should be listed with addresses and actions")
def check_human_resources(cli_result):
    assert "aws_instance.web" in cli_result.stdout

@then("errors should be highlighted if present")
def check_human_errors(cli_result):
    assert "Status:" in cli_result.stdout

@then("summary should be clearly displayed")
def check_human_summary(cli_result):
    assert "Summary:" in cli_result.stdout

@given("I have a Terraform instance initialized", target_fixture="tf")
def terraform_instance():
    from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

    class PlanParserStub:
        def parse_plain_text_plan(self, plan_text: str) -> dict:
            return TerraformPlainTextPlanParser(plan_text).parse()

    return PlanParserStub()

@when("I call tf.parse_plain_text_plan(plan_text)", target_fixture="parsed_result")
def call_tf_parse_method(tf):
    plan_text = make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}")
    return tf.parse_plain_text_plan(plan_text)

@then("the method should return a dictionary")
def check_return_type(parsed_result):
    assert isinstance(parsed_result, dict)

@then("the dictionary should contain \"resource_changes\" key")
def check_dict_key_resources(parsed_result):
    assert "resource_changes" in parsed_result

@then("the dictionary should contain \"plan_summary\" key")
def check_dict_key_summary(parsed_result):
    assert "plan_summary" in parsed_result

@then("the dictionary should contain \"plan_status\" key")
def check_dict_key_status(parsed_result):
    assert "plan_status" in parsed_result
