"""Terraform plan and execution diagnostic models."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DiagnosticSeverity(StrEnum):
    """Severity of a diagnostic message."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagnosticCategory(StrEnum):
    """Categorized nature of a diagnostic."""

    MODULE_HEALTH = "module_health"
    DEPRECATION = "deprecation"
    RUNTIME = "runtime"
    SYNTAX_OR_SCHEMA = "syntax_or_schema"
    GENERAL = "general"


class Diagnostic(BaseModel):
    """Represents a diagnostic emitted during Terraform execution."""

    severity: DiagnosticSeverity
    summary: str
    detail: str | None = None
    address: str | None = None
    filename: str | None = None
    line: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_module_deprecation(self) -> bool:
        """Check whether this diagnostic represents a deprecated module version."""
        if self.extra.get("type") == "module_version_deprecation":
            return True
        summary_lower = self.summary.lower()
        return "module version" in summary_lower and "deprecated" in summary_lower

    @property
    def category(self) -> DiagnosticCategory:
        """Infer the category of this diagnostic."""
        if self.is_module_deprecation:
            return DiagnosticCategory.MODULE_HEALTH
        if "deprecat" in self.summary.lower():
            return DiagnosticCategory.DEPRECATION
        if self.severity == DiagnosticSeverity.ERROR:
            return DiagnosticCategory.RUNTIME
        return DiagnosticCategory.GENERAL

    @property
    def module_source(self) -> str | None:
        """Module registry address if applicable."""
        return self.extra.get("source_name")

    @property
    def module_version(self) -> str | None:
        """Module version if applicable."""
        return self.extra.get("version")

    def to_dict(self) -> dict[str, Any]:
        """Convert diagnostic to dictionary representation."""
        return {
            "severity": self.severity.value,
            "summary": self.summary,
            "detail": self.detail,
            "address": self.address,
            "filename": self.filename,
            "line": self.line,
            "category": self.category.value,
            "is_module_deprecation": self.is_module_deprecation,
            "module_source": self.module_source,
            "module_version": self.module_version,
            "extra": self.extra,
        }
