"""Tests for Terraform plain text plan parser."""

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

    def _run_cli(self, args: list, tmp_path=None, stdin=None) -> "subprocess.CompletedProcess":
        """Run terrapyne CLI from the worktree source via subprocess."""
        import os
        import subprocess
        import sys
        from pathlib import Path

        src_root = str(Path(__file__).parent.parent.parent / "src")
        env = {**os.environ, "PYTHONPATH": src_root}
        return subprocess.run(
            [sys.executable, "-m", "terrapyne"] + args,
            capture_output=True, text=True, env=env,
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
