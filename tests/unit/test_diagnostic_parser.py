"""Unit tests for Diagnostic model and DiagnosticParser."""

from terrapyne.core.diagnostic_parser import DiagnosticParser
from terrapyne.models.diagnostic import (
    Diagnostic,
    DiagnosticCategory,
    DiagnosticSeverity,
)

# Sample JSON lines from real HCP Terraform runs
SAMPLE_MODULE_DEPRECATION_JSON = (
    '{"@level":"warn","@message":"Module version 1.4.0 of app.terraform.io/Takeda/EC2/aws is deprecated",'
    '"@module":"terraform.ui","@timestamp":"2026-10-15T07:40:05Z",'
    '"diagnostic":{"severity":"warning","summary":"Module version 1.4.0 of app.terraform.io/Takeda/EC2/aws is deprecated",'
    '"detail":"This version is deprecated. Please upgrade to the latest stable version.",'
    '"extra":{"type":"module_version_deprecation","version":"1.4.0","source_name":"app.terraform.io/Takeda/EC2/aws",'
    '"link":"","deprecation_message":"This version is deprecated. Please upgrade to the latest stable version."}},'
    '"type":"diagnostic"}'
)

SAMPLE_ERROR_JSON = (
    '{"@level":"error","@message":"Error: Missing required argument",'
    '"@module":"terraform.ui","@timestamp":"2026-10-15T07:40:05Z",'
    '"diagnostic":{"severity":"error","summary":"Missing required argument",'
    '"detail":"The argument \\"vpc_id\\" is required, but no definition was found.",'
    '"address":"module.ec2.aws_instance.this",'
    '"range":{"filename":"main.tf","start":{"line":15,"column":3},"end":{"line":15,"column":12}}},'
    '"type":"diagnostic"}'
)

SAMPLE_PLAIN_TEXT_WARNING = """
╷
│ Warning: Argument is deprecated
│ 
│   with aws_instance.web,
│   on main.tf line 25, in resource "aws_instance" "web":
│   25:   monitoring = true
│ 
│ Use standard_monitoring instead.
╵
"""

SAMPLE_PLAIN_TEXT_ERROR = """
╷
│ Error: Invalid value for variable
│ 
│   on variables.tf line 5:
│    5: variable "instance_type" {
│ 
│ Expected a valid AWS instance type.
╵
"""


class TestDiagnosticModel:
    def test_module_deprecation_diagnostic(self):
        diag = Diagnostic(
            severity=DiagnosticSeverity.WARNING,
            summary="Module version 1.4.0 of app.terraform.io/Takeda/EC2/aws is deprecated",
            detail="This version is deprecated. Please upgrade to the latest stable version.",
            extra={
                "type": "module_version_deprecation",
                "version": "1.4.0",
                "source_name": "app.terraform.io/Takeda/EC2/aws",
            },
        )
        assert diag.severity == DiagnosticSeverity.WARNING
        assert diag.category == DiagnosticCategory.MODULE_HEALTH
        assert diag.is_module_deprecation is True
        assert diag.module_source == "app.terraform.io/Takeda/EC2/aws"
        assert diag.module_version == "1.4.0"

    def test_error_diagnostic(self):
        diag = Diagnostic(
            severity=DiagnosticSeverity.ERROR,
            summary="Missing required argument",
            detail='The argument "vpc_id" is required.',
            address="module.ec2.aws_instance.this",
            filename="main.tf",
            line=15,
        )
        assert diag.severity == DiagnosticSeverity.ERROR
        assert diag.category == DiagnosticCategory.RUNTIME
        assert diag.is_module_deprecation is False
        assert diag.address == "module.ec2.aws_instance.this"
        assert diag.filename == "main.tf"
        assert diag.line == 15

    def test_to_dict_serialization(self):
        diag = Diagnostic(
            severity=DiagnosticSeverity.WARNING,
            summary="Warning test",
            detail="detail info",
            extra={
                "type": "module_version_deprecation",
                "version": "2.0.0",
                "source_name": "mod/aws",
            },
        )
        data = diag.to_dict()
        assert data["severity"] == "warning"
        assert data["summary"] == "Warning test"
        assert data["category"] == "module_health"
        assert data["module_source"] == "mod/aws"
        assert data["module_version"] == "2.0.0"


class TestDiagnosticParser:
    def test_parse_empty_or_non_diagnostic_log(self):
        assert DiagnosticParser.parse("") == []
        log = "Terraform v1.14.6\nRefreshing state...\nPlan: 0 to add."
        assert DiagnosticParser.parse(log) == []

    def test_parse_json_lines_stream(self):
        log = f"""
Terraform v1.14.6
on linux_amd64
Initializing plugins and modules...
{SAMPLE_MODULE_DEPRECATION_JSON}
{"{"}"@level":"info","@message":"Refreshing state...","type":"refresh_start"{"}"}
{SAMPLE_ERROR_JSON}
"""
        diags = DiagnosticParser.parse(log)
        assert len(diags) == 2

        # 1. Module deprecation warning
        assert diags[0].severity == DiagnosticSeverity.WARNING
        assert diags[0].category == DiagnosticCategory.MODULE_HEALTH
        assert diags[0].module_source == "app.terraform.io/Takeda/EC2/aws"
        assert diags[0].module_version == "1.4.0"
        assert "deprecated" in diags[0].summary

        # 2. Error diagnostic
        assert diags[1].severity == DiagnosticSeverity.ERROR
        assert diags[1].category == DiagnosticCategory.RUNTIME
        assert diags[1].summary == "Missing required argument"
        assert diags[1].address == "module.ec2.aws_instance.this"
        assert diags[1].filename == "main.tf"
        assert diags[1].line == 15

    def test_parse_plain_text_warning(self):
        diags = DiagnosticParser.parse(SAMPLE_PLAIN_TEXT_WARNING)
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.WARNING
        assert diags[0].summary == "Argument is deprecated"
        assert diags[0].address == "aws_instance.web"
        assert diags[0].filename == "main.tf"
        assert diags[0].line == 25
        assert "standard_monitoring" in (diags[0].detail or "")

    def test_parse_plain_text_error(self):
        diags = DiagnosticParser.parse(SAMPLE_PLAIN_TEXT_ERROR)
        assert len(diags) == 1
        assert diags[0].severity == DiagnosticSeverity.ERROR
        assert diags[0].summary == "Invalid value for variable"
        assert diags[0].filename == "variables.tf"
        assert diags[0].line == 5

    def test_parse_mixed_formats(self):
        mixed = f"{SAMPLE_MODULE_DEPRECATION_JSON}\n{SAMPLE_PLAIN_TEXT_WARNING}"
        diags = DiagnosticParser.parse(mixed)
        assert len(diags) == 2
        assert diags[0].category == DiagnosticCategory.MODULE_HEALTH
        assert diags[1].severity == DiagnosticSeverity.WARNING
