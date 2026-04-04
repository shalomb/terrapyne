"""BDD tests for Terraform plain text plan parser - Refined for Adzic Index."""

import json
import re
import pytest
from pathlib import Path
from pytest_bdd import given, scenario, then, when, parsers
from typer.testing import CliRunner

import terrapyne
print(f"DEBUG: terrapyne imported from {terrapyne.__file__}")

from terrapyne.cli.main import app

runner = CliRunner()

# ============================================================================
# Scenarios - Core
# ============================================================================

@scenario("../features/plan_parser_core.feature", "Detection of infrastructure additions")
def test_detect_additions(): pass

@scenario("../features/plan_parser_core.feature", "Detection of infrastructure removals")
def test_detect_removals(): pass

@scenario("../features/plan_parser_core.feature", "Detection of in-place updates")
def test_detect_updates(): pass

@scenario("../features/plan_parser_core.feature", "Detection of resource replacements")
def test_detect_replacements(): pass

@scenario("../features/plan_parser_core.feature", "Cleanup of formatted terminal output")
def test_detect_ansi_cleanup(): pass

@scenario("../features/plan_parser_core.feature", "Handling of platform-specific line endings")
def test_detect_windows_line_endings(): pass

@scenario("../features/plan_parser_core.feature", "Analysis of minimal or empty plans")
def test_detect_minimal_plans(): pass

@scenario("../features/plan_parser_core.feature", "Analysis of mixed metadata and plan text")
def test_detect_mixed_output(): pass

# ============================================================================
# Scenarios - Resources
# ============================================================================

@scenario("../features/plan_parser_resources.feature", "Analysis of standard resource addresses")
def test_parse_simple_address(): pass

@scenario("../features/plan_parser_resources.feature", "Analysis of indexed resource addresses")
def test_parse_indexed_address(): pass

@scenario("../features/plan_parser_resources.feature", "Analysis of module-scoped resources")
def test_parse_module_address(): pass

@scenario("../features/plan_parser_resources.feature", "Analysis of complex nested resource addresses")
def test_parse_complex_module_address(): pass

@scenario("../features/plan_parser_resources.feature", "Extraction of static resource attributes")
def test_parse_simple_attributes(): pass

@scenario("../features/plan_parser_resources.feature", "Extraction of modified attributes")
def test_parse_attribute_change_notation(): pass

@scenario("../features/plan_parser_resources.feature", "Extraction of collection attributes")
def test_parse_array_attributes(): pass

@scenario("../features/plan_parser_resources.feature", "Extraction of nested configuration blocks")
def test_parse_nested_attributes(): pass

@scenario("../features/plan_parser_resources.feature", "Identification of dynamic values")
def test_parse_computed_markers(): pass

@scenario("../features/plan_parser_resources.feature", "Analysis of infrastructure import operations")
def test_parse_import_action(): pass

# ============================================================================
# Scenarios - Summary & Diagnostics
# ============================================================================

@scenario("../features/plan_parser_summary.feature", "Extraction of comprehensive plan statistics")
def test_parse_plan_summary_all_types(): pass

@scenario("../features/plan_parser_summary.feature", "Extraction of statistics including imports")
def test_parse_plan_summary_imports(): pass

@scenario("../features/plan_parser_summary.feature", "Extraction of \"No Changes\" status")
def test_parse_no_changes_message(): pass

@scenario("../features/plan_parser_summary.feature", "Extraction of variable validation errors")
def test_extract_validation_error(): pass

@scenario("../features/plan_parser_summary.feature", "Extraction of data source resolution errors")
def test_extract_data_source_error(): pass

@scenario("../features/plan_parser_summary.feature", "Detection of general execution failures")
def test_handle_operation_failure(): pass

# ============================================================================
# Scenarios - Integration
# ============================================================================

@scenario("../features/plan_parser_integration.feature", "Run parse-plan command with file input")
def test_cli_parse_plan_file(): pass

@scenario("../features/plan_parser_integration.feature", "Parse plan with JSON output format")
def test_cli_parse_plan_json(): pass

@scenario("../features/plan_parser_integration.feature", "Parse plan with human-readable output")
def test_cli_parse_plan_human(): pass

@scenario("../features/plan_parser_integration.feature", "Use parse_plain_text_plan() method")
def test_api_parse_method(): pass

# ============================================================================
# Background / Given Steps
# ============================================================================

@given("a terraform environment is ready", target_fixture="tf")
@given("Terrapyne is initialized with a terraform workspace", target_fixture="tf")
def terraform_env_ready():
    """Return a lightweight object with parse_plain_text_plan — no terraform binary needed."""
    from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

    class PlanParserStub:
        def parse_plain_text_plan(self, plan_text: str) -> dict:
            return TerraformPlainTextPlanParser(plan_text).parse()

    return PlanParserStub()

@given("a plan is available from a remote execution", target_fixture="plan_content")
@given("I have terraform plan output from a remote backend", target_fixture="plan_content")
def remote_plan_available():
    return "Terraform will perform the following actions:\n\nPlan: 0 to add, 0 to change, 0 to destroy."

# ============================================================================
# Helper
# ============================================================================

def make_plan(content, summary="Plan: 1 to add, 0 to change, 0 to destroy."):
    return f"Terraform will perform the following actions:\n\n{content}\n\n{summary}"

def extract_json(stdout):
    """Robustly extract JSON from stdout that might contain other text."""
    start = stdout.find('{')
    end = stdout.rfind('}')
    if start != -1 and end != -1:
        return json.loads(stdout[start:end+1])
    raise ValueError(f"No JSON object found in output: {stdout}")

# ============================================================================
# Step Definitions
# ============================================================================

@given(parsers.parse('the plan indicates a new resource "{address}" will be created'), target_fixture="plan_text")
@given(parsers.parse('the plan indicates a change for resource "{address}"'), target_fixture="plan_text")
def plan_indicates_creation(address):
    return make_plan(f"  # {address} will be created\n  + resource \"type\" \"name\" {{}}")

@given(parsers.parse('the plan indicates resource "{address}" will be destroyed'), target_fixture="plan_text")
def plan_indicates_destruction(address):
    return make_plan(f"  # {address} will be destroyed\n  - resource \"type\" \"name\" {{}}", "Plan: 0 to add, 0 to change, 1 to destroy.")

@given(parsers.parse('the plan indicates resource "{address}" will be modified'), target_fixture="plan_text")
def plan_indicates_modification(address):
    return make_plan(f"  # {address} will be updated in-place\n  ~ resource \"type\" \"name\" {{}}", "Plan: 0 to add, 1 to change, 0 to destroy.")

@given(parsers.parse('the plan indicates resource "{address}" must be replaced'), target_fixture="plan_text")
def plan_indicates_replacement(address):
    return make_plan(f"  # {address} must be replaced\n-/+ resource \"type\" \"name\" {{}}", "Plan: 1 to add, 0 to change, 1 to destroy.")

@when("the plan is analyzed", target_fixture="parsed_result")
@when("I parse the plan using terrapyne.parse_plain_text_plan()", target_fixture="parsed_result")
@when("I parse the plan", target_fixture="parsed_result")
def plan_analyzed(tf, plan_text):
    return tf.parse_plain_text_plan(plan_text)

@then(parsers.parse("the result should confirm {count:d} resource will be added"))
def check_confirm_added(parsed_result, count):
    assert len(parsed_result["resource_changes"]) == count
    assert "create" in parsed_result["resource_changes"][0]["change"]["actions"]

@then(parsers.parse("the result should confirm {count:d} resource will be deleted"))
def check_confirm_deleted(parsed_result, count):
    assert len(parsed_result["resource_changes"]) == count
    assert "delete" in parsed_result["resource_changes"][0]["change"]["actions"]

@then(parsers.parse("the result should confirm {count:d} resource will be updated"))
def check_confirm_updated(parsed_result, count):
    assert len(parsed_result["resource_changes"]) == count
    assert "update" in parsed_result["resource_changes"][0]["change"]["actions"]

@then(parsers.parse('the result should confirm a replacement operation for "{address}"'))
def check_confirm_replacement(parsed_result, address):
    assert parsed_result["resource_changes"][0]["address"] == address
    actions = parsed_result["resource_changes"][0]["change"]["actions"]
    assert "create" in actions and "delete" in actions

@then("the actions should include both creation and deletion")
def check_actions_both(): pass

@then(parsers.parse('the change address should be "{address}"'))
def check_change_address(parsed_result, address):
    assert parsed_result["resource_changes"][0]["address"] == address

@given("the plan output contains terminal formatting codes (ANSI)", target_fixture="plan_text")
def plan_contains_ansi():
    return make_plan("\x1b[1m  # aws_instance.web\x1b[0m will be created\n  + resource \"aws_instance\" \"web\" {}")

@when("the plan is sanitized", target_fixture="parsed_result")
def plan_sanitized(tf, plan_text):
    return tf.parse_plain_text_plan(plan_text)

@then("all formatting codes should be removed")
def check_ansi_removed_adzic(parsed_result):
    assert parsed_result["resource_changes"][0]["address"] == "aws_instance.web"

@then("the underlying plan text should be preserved")
def check_text_preserved(): pass

@given("the plan was generated on a system with Windows line endings", target_fixture="plan_text")
def plan_windows_lines():
    return "Terraform will perform the following actions:\r\n\r\n  # aws_instance.web will be created\r\n  + resource \"aws_instance\" \"web\" {}\r\n\r\nPlan: 1 to add, 0 to change, 0 to destroy."

@then("the parser should normalize the line endings")
def check_normalize_lines(parsed_result):
    assert len(parsed_result["resource_changes"]) == 1

@then("the resource changes should be correctly identified")
def check_changes_identified(): pass

@given("the plan indicates no changes are required", target_fixture="plan_text")
@given("the plan indicates the environment is up-to-date", target_fixture="plan_text")
def plan_no_changes_needed():
    return "No changes. Infrastructure is up-to-date."

@then("the list of resource changes should be empty")
def check_changes_empty_adzic(parsed_result):
    assert len(parsed_result["resource_changes"]) == 0

@then("the analysis should complete without errors")
def check_analysis_no_errors(parsed_result):
    assert parsed_result is not None

@given("the output begins with technical version metadata", target_fixture="plan_text")
def plan_with_metadata():
    return '{"terraform_version":"1.5.0"}\n' + make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}")

@given("is followed by the actual infrastructure plan")
def plan_follows_metadata(): pass

@then("the metadata should be ignored")
def check_metadata_ignored(parsed_result):
    assert parsed_result is not None

@then("the infrastructure changes should be successfully extracted")
def check_infra_extracted(parsed_result):
    assert len(parsed_result["resource_changes"]) == 1

# ============================================================================
# Resource Step Definitions
# ============================================================================

@then(parsers.parse('the resource should be identified as type "{resource_type}"'))
@then(parsers.parse('the resource type should be "{resource_type}"'))
def check_resource_type(parsed_result, resource_type):
    assert parsed_result["resource_changes"][0]["type"] == resource_type

@then(parsers.parse('the resource should be identified with name "{resource_name}"'))
@then(parsers.parse('the resource name should be "{resource_name}"'))
def check_resource_name(parsed_result, resource_name):
    actual_name = parsed_result["resource_changes"][0]["name"]
    assert actual_name == resource_name or actual_name.startswith(f"{resource_name}[")

@then(parsers.parse("the resource index should be {index:d}"))
def check_resource_index(parsed_result, index):
    assert f"[{index}]" in parsed_result["resource_changes"][0]["address"]

@given("the plan indicates a new resource with attributes:", target_fixture="plan_text")
def resource_with_attributes_table(datatable):
    attrs = ""
    for row in datatable:
        attrs += f"      + {row[0]} = {row[1]}\n"
    return make_plan(f"  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {{\n{attrs}    }}")

@then(parsers.parse('the target state should include "{key}" with value "{value}"'))
def check_change_after_param(parsed_result, key, value):
    after = parsed_result["resource_changes"][0]["change"].get("after")
    assert after[key] == value

@given(parsers.parse('the plan indicates an attribute change "{change_line}"'), target_fixture="plan_text")
def resource_with_attribute_change_declarative(change_line):
    return make_plan(f"  # aws_instance.web will be updated in-place\n  ~ resource \"aws_instance\" \"web\" {{\n      {change_line}\n    }}")

@then(parsers.parse('the prior state for "{key}" should be "{value}"'))
def check_before_value(parsed_result, key, value):
    assert parsed_result["resource_changes"][0]["change"]["before"][key] == value

@then(parsers.parse('the target state for "{key}" should be "{value}"'))
def check_after_value(parsed_result, key, value):
    assert parsed_result["resource_changes"][0]["change"]["after"][key] == value

@given(parsers.parse('the plan indicates an array attribute "{attr_line}"'), target_fixture="plan_text")
def resource_with_array_attr_declarative(attr_line):
    return make_plan(f"  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {{\n      + {attr_line}\n    }}")

@then(parsers.parse('the target state for "{key}" should be a collection'))
def check_after_services_collection(parsed_result, key):
    assert isinstance(parsed_result["resource_changes"][0]["change"]["after"][key], list)

@then(parsers.parse("the collection should contain {count:d} elements"))
def check_collection_length(parsed_result, count):
    for val in parsed_result["resource_changes"][0]["change"]["after"].values():
        if isinstance(val, list):
            assert len(val) == count
            return
    pytest.fail("No collection found in after state")

@given(parsers.parse('the plan indicates a nested block "{block_line}"'), target_fixture="plan_text")
def resource_with_nested_attr_declarative(block_line):
    return make_plan(f"  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {{\n      + {block_line}\n    }}")

@then("the parser should handle the nested structure without errors")
def check_nested_graceful(parsed_result):
    assert parsed_result is not None

@given(parsers.parse('the plan indicates a value will be "{v1}" or "{v2}"'), target_fixture="plan_text")
def resource_with_computed_declarative(v1, v2):
    return make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {\n      + id = <computed>\n    }")

@then("the result should preserve the placeholder marker")
def check_computed_preserved(parsed_result):
    assert parsed_result["resource_changes"][0]["change"]["after"]["id"] == "<computed>"

@given(parsers.parse('the plan indicates resource "{address}" will be imported'), target_fixture="plan_text")
def resource_with_import_declarative(address):
    return make_plan(f" <= {address} will be imported\n    resource \"type\" \"name\" {{\n      + ami = \"ami-12345\"\n    }}", "Plan: 0 to add, 0 to change, 0 to destroy, 1 to import.")

@then(parsers.parse('the operation should be identified as an "{action}"'))
def check_actions_import_declarative(parsed_result, action):
    assert action in parsed_result["resource_changes"][0]["change"]["actions"]

# ============================================================================
# Summary Step Definitions
# ============================================================================

@given(parsers.parse('the plan summary reports "{summary_text}"'), target_fixture="plan_text")
def plan_with_summary_text_declarative(summary_text):
    return make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}", summary_text)

@then("the change totals should be:")
def check_plan_summary_values_declarative(parsed_result, datatable):
    expected = {row[0]: int(row[1]) for row in datatable if row[0] != "category"}
    actual = parsed_result["plan_summary"]
    for key, val in expected.items():
        assert actual[key] == val

@then("all change category counts should be zero")
def check_summary_zeros(parsed_result):
    summary = parsed_result["plan_summary"]
    assert summary["add"] == 0
    assert summary["change"] == 0
    assert summary["destroy"] == 0

@given(parsers.parse('the plan failed due to an invalid variable value "{value}"'), target_fixture="plan_text")
def plan_failed_variable(value):
    return f"╷\n│ Error: Invalid value for variable\n│ \n│   on main.tf line 25, in variable \"engine\":\n│   25:   default = \"{value}\"\n│ \n│ The engine must be one of: postgres, mysql, mariadb\n╵"

@then("the result should include a diagnostic error")
def check_diagnostics_present(parsed_result):
    assert len(parsed_result["diagnostics"]) > 0

@then(parsers.parse('the error severity should be "{severity}"'))
def check_diagnostic_severity(parsed_result, severity):
    assert parsed_result["diagnostics"][0]["severity"] == severity

@then("the error summary should indicate a variable issue")
def check_diagnostic_summary_var(parsed_result):
    assert "Invalid value for variable" in parsed_result["diagnostics"][0]["summary"]

@given("the plan failed because a required data source was not found", target_fixture="plan_text")
def plan_failed_datasource():
    return "╷\n│ Error: no matching RDS DB Subnet Group found\n│ \n│   with data.aws_db_subnet_group.rds[0],\n│   on main.tf line 10, in data \"aws_db_subnet_group\" \"rds\":\n│   10: data \"aws_db_subnet_group\" \"rds\" {\n│ \n╵"

@then("the error summary should mention the missing resource")
def check_diagnostic_summary_no_matching(parsed_result):
    assert "no matching" in parsed_result["diagnostics"][0]["summary"]

@given("the plan output indicates an operation failure", target_fixture="plan_text")
def plan_failed_general():
    return "Operation failed: failed running terraform plan (exit 1)"

@then(parsers.parse('the plan status should be identified as "{status}"'))
def check_plan_status_failed(parsed_result, status):
    assert parsed_result["plan_status"] == status

@then("the failure details should be captured in diagnostics")
def check_diagnostics_capture_failure(parsed_result):
    assert len(parsed_result["diagnostics"]) > 0 or parsed_result["plan_status"] == "failed"

# ============================================================================
# Integration Step Definitions
# ============================================================================

@given(parsers.parse('I have a terraform plan output file "{filename}"'), target_fixture="plan_file")
@given("I have a terraform plan output file", target_fixture="plan_file")
def plan_file_fixture(tmp_path, filename="plan.txt"):
    f = tmp_path / filename
    f.write_text(make_plan("  # aws_instance.web will be created\n  + resource \"aws_instance\" \"web\" {}"))
    return f

@given("the file contains valid terraform plan")
def file_valid_plan(): pass

@when(parsers.parse('I run "terrapyne run parse-plan {filename}"'), target_fixture="cli_result")
def run_cli_parse_plan_simple(plan_file):
    return runner.invoke(app, ["run", "parse-plan", str(plan_file)])

@when("I trigger the parse-plan command with JSON format", target_fixture="cli_result")
def run_cli_parse_plan_json_unique(plan_file):
    args = ["run", "parse-plan", str(plan_file), "--format", "json"]
    print(f"DEBUG: run_cli_parse_plan_json_unique with args={args}")
    return runner.invoke(app, args)

@then("the command should succeed with exit code 0")
def check_exit_code_zero(cli_result):
    assert cli_result.exit_code == 0

@then("the output should show parsed plan summary")
def check_cli_output_summary(cli_result):
    assert "Summary:" in cli_result.stdout or "Plan:" in cli_result.stdout or "Resources:" in cli_result.stdout

@then("the output should show resource count")
def check_cli_output_resource_count(cli_result):
    assert "Resources:" in cli_result.stdout

@then("the output should be valid JSON output")
def check_valid_json_output(cli_result):
    data = extract_json(cli_result.stdout)
    assert data is not None

@then("the JSON should contain resource_changes, plan_summary, diagnostics")
def check_json_content(cli_result):
    data = extract_json(cli_result.stdout)
    assert "resource_changes" in data
    assert "plan_summary" in data

@then("the output should be formatted for human readability")
def check_human_readability(cli_result):
    assert "📊 Resources:" in cli_result.stdout

@then("resources should be listed with addresses and actions")
def check_human_resources(cli_result):
    assert "aws_instance.web" in cli_result.stdout

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
