"""Tests for Terraform plain text plan parser."""

from pathlib import Path

import pytest

from terrapyne.core.plan_parser import TerraformPlainTextPlanParser


@pytest.fixture
def sample_plan_create():
    """Sample plan with resource creation."""
    return """
Terraform will perform the following actions:

  # aws_instance.web will be created
  + resource "aws_instance" "web" {
      + ami           = "ami-12345"
      + instance_type = "t2.micro"
    }

Plan: 1 to add, 0 to change, 0 to destroy.
    """


@pytest.fixture
def sample_plan_with_errors():
    """Sample plan with validation errors."""
    return """
╷
│ Error: Invalid value for variable
│
│   on main.tf line 25, in variable "engine":
│   25:   default = "oracle-ee"
│
│ The engine must be one of: postgres, mysql, mariadb
│
╵

No changes. Infrastructure is up-to-date.
    """


@pytest.fixture
def sample_plan_with_ansi():
    """Sample plan with ANSI escape codes."""
    return """
Terraform will perform the following actions:

\x1b[1m  # aws_instance.web\x1b[0m will be \x1b[1m\x1b[31mcreated\x1b[0m
  + resource "aws_instance" "web" {
      + ami = "ami-12345"
    }

Plan: 1 to add, 0 to change, 0 to destroy.
    """


class TestPlanParser:
    """Test plan parser integration."""

    def test_parse_basic_plan(self, sample_plan_create):
        """Test parsing basic create plan."""
        parser = TerraformPlainTextPlanParser
        result = parser(sample_plan_create).parse()

        assert "resource_changes" in result
        assert len(result["resource_changes"]) == 1

        rc = result["resource_changes"][0]
        assert rc["address"] == "aws_instance.web"
        assert rc["type"] == "aws_instance"
        assert rc["change"]["actions"] == ["create"]

    def test_parse_plan_with_errors(self, sample_plan_with_errors):
        """Test parsing plan with validation errors."""
        parser = TerraformPlainTextPlanParser
        result = parser(sample_plan_with_errors).parse()

        assert "diagnostics" in result
        assert len(result["diagnostics"]) > 0
        assert result.get("plan_status") == "failed"

    def test_strip_ansi_codes(self, sample_plan_with_ansi):
        """Test ANSI code stripping."""
        parser = TerraformPlainTextPlanParser
        result = parser(sample_plan_with_ansi).parse()

        # Should parse successfully despite ANSI codes
        assert len(result["resource_changes"]) == 1
        assert result["resource_changes"][0]["address"] == "aws_instance.web"

    def test_parse_plan_summary(self, sample_plan_create):
        """Test plan summary extraction."""
        parser = TerraformPlainTextPlanParser
        result = parser(sample_plan_create).parse()

        assert "plan_summary" in result
        summary = result["plan_summary"]
        assert summary["add"] == 1
        assert summary["change"] == 0
        assert summary["destroy"] == 0


@pytest.mark.integration
class TestParsePlanCLIOutput:
    """Tests for parse-plan CLI JSON output correctness."""

    BASIC_CREATE = """\
Terraform will perform the following actions:

  # aws_instance.web will be created
  + resource "aws_instance" "web" {
      + ami           = "ami-12345678"
      + instance_type = "t2.micro"
      + tags          = {
          + "Name" = "web-server"
        }
    }

Plan: 1 to add, 0 to change, 0 to destroy.
"""

    def _run_cli(self, args: list, tmp_path=None, stdin=None):
        """Run terrapyne CLI using the current venv's Python."""
        import subprocess
        import sys

        return subprocess.run(
            [sys.executable, "-m", "terrapyne", *args],
            capture_output=True,
            text=True,
            input=stdin,
        )

    def test_json_stdout_is_valid_json(self, tmp_path):
        """JSON output via CLI stdout must be valid JSON (no Rich control chars)."""
        import json

        plan_file = tmp_path / "plan.txt"
        plan_file.write_text(self.BASIC_CREATE)

        result = self._run_cli(["run", "parse-plan", str(plan_file), "--format", "json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Must parse cleanly — this is the regression
        parsed = json.loads(result.stdout)
        assert len(parsed["resource_changes"]) == 1
        assert parsed["resource_changes"][0]["address"] == "aws_instance.web"

    def test_json_stdout_multiline_values_survive(self, tmp_path):
        """Multi-line attribute values (tags) must not corrupt JSON stdout."""
        import json

        plan_file = tmp_path / "plan.txt"
        plan_file.write_text(self.BASIC_CREATE)

        result = self._run_cli(["run", "parse-plan", str(plan_file), "--format", "json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        parsed = json.loads(result.stdout)
        # tags value contains embedded newlines — must survive round-trip
        after = parsed["resource_changes"][0]["change"]["after"]
        assert "tags" in after

    def test_stdin_dash_reads_from_stdin(self):
        """Passing `-` as plan file reads plan from stdin."""
        import json

        result = self._run_cli(
            ["run", "parse-plan", "-", "--format", "json"],
            stdin=self.BASIC_CREATE,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        parsed = json.loads(result.stdout)
        assert len(parsed["resource_changes"]) == 1
        assert parsed["resource_changes"][0]["change"]["actions"] == ["create"]

    def test_stdin_dash_human_format(self):
        """Stdin with human format produces readable summary."""
        result = self._run_cli(
            ["run", "parse-plan", "-"],
            stdin=self.BASIC_CREATE,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "aws_instance.web" in result.stdout


class TestStructuredLogDetection:
    """Parser warns clearly on TFC 1.12+ JSON structured log input."""

    # Minimal TFC 1.12+ structured log (no plain-text plan section)
    STRUCTURED_LOG = """\
{"@level":"info","@message":"Terraform 1.12.2","type":"version","terraform":"1.12.2"}
{"@level":"info","@message":"data.vault_aws_access_credentials.creds: Refreshing...","type":"apply_start"}
{"@level":"info","@message":"Plan: 2 to add, 0 to change, 0 to destroy.","type":"change_summary","changes":{"add":2,"change":0,"remove":0}}
{"@level":"info","@message":"Apply complete! Resources: 2 added, 0 changed, 0 destroyed.","type":"apply_complete"}
"""

    def test_structured_log_plan_status_is_structured_log(self):
        """Structured log input yields plan_status='structured_log', not 'success'."""
        from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

        result = TerraformPlainTextPlanParser(self.STRUCTURED_LOG).parse()
        assert result["plan_status"] == "structured_log"

    def test_structured_log_has_diagnostic_warning(self):
        """Structured log input includes a diagnostic explaining the limitation."""
        from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

        result = TerraformPlainTextPlanParser(self.STRUCTURED_LOG).parse()
        diagnostics = result.get("diagnostics", [])
        assert any(
            "structured" in str(d).lower() or "json" in str(d).lower() for d in diagnostics
        ), f"No structured-log diagnostic in: {diagnostics}"

    def test_structured_log_resource_changes_empty(self):
        """Structured log input cannot yield resource_changes — must be empty list."""
        from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

        result = TerraformPlainTextPlanParser(self.STRUCTURED_LOG).parse()
        assert result["resource_changes"] == []

    def test_structured_log_plan_summary_extracted(self):
        """Plan summary counts are still extracted from the JSON change_summary line."""
        from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

        result = TerraformPlainTextPlanParser(self.STRUCTURED_LOG).parse()
        summary = result.get("plan_summary", {})
        assert summary.get("add") == 2

    def test_plain_text_plan_unaffected(self):
        """Normal plain-text plan is not mis-detected as structured log."""
        from terrapyne.core.plan_parser import TerraformPlainTextPlanParser

        plain = """\
Terraform will perform the following actions:

  # aws_instance.web will be created
  + resource "aws_instance" "web" {
      + ami = "ami-12345678"
    }

Plan: 1 to add, 0 to change, 0 to destroy.
"""
        result = TerraformPlainTextPlanParser(plain).parse()
        assert result["plan_status"] != "structured_log"
        assert len(result["resource_changes"]) == 1


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "plan_outputs"
FIXTURE_FILES = sorted(FIXTURE_DIR.glob("*.txt")) if FIXTURE_DIR.exists() else []
FIXTURE_STEMS = [f.stem for f in FIXTURE_FILES]


@pytest.mark.parametrize("fixture_file", FIXTURE_FILES, ids=[f.stem for f in FIXTURE_FILES])
def test_fixture_parses_to_valid_structure(fixture_file):
    """Every fixture must parse without raising and return a valid plan structure."""
    text = fixture_file.read_text()
    result = TerraformPlainTextPlanParser(text).parse()

    # Must always return these keys
    assert "resource_changes" in result
    assert "format_version" in result
    assert isinstance(result["resource_changes"], list)
    assert result["format_version"] == "1.0"

    # Each resource change must have required fields
    for rc in result["resource_changes"]:
        assert "address" in rc, f"Missing 'address' in {rc}"
        assert "change" in rc, f"Missing 'change' in {rc}"
        assert "actions" in rc["change"], f"Missing 'actions' in change: {rc}"
        assert isinstance(rc["change"]["actions"], list)


@pytest.mark.parametrize("fixture_stem", FIXTURE_STEMS)
def test_fixture_json_output_is_valid(fixture_stem, plan_parser_fixtures):
    """Every fixture's JSON output must be valid JSON (no control chars)."""
    import json

    text = plan_parser_fixtures[fixture_stem]
    parsed = TerraformPlainTextPlanParser(text).parse()

    # Verify it's valid JSON-serializable
    json_str = json.dumps(parsed)  # raises on invalid JSON
    assert "resource_changes" in json.loads(json_str)
