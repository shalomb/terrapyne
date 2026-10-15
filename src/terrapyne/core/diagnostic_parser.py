"""Parser for Terraform execution diagnostics across stream and plain-text formats."""

from __future__ import annotations

import json
import re

from terrapyne.models.diagnostic import (
    Diagnostic,
    DiagnosticSeverity,
)

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Plain text patterns
_BOX_START = re.compile(r"^\s*╷\s*$")
_BOX_END = re.compile(r"^\s*╵\s*$")
_MSG_LINE = re.compile(r"^\s*│\s*(Error|Warning):\s*(.+)$")
_WITH_LINE = re.compile(r"^\s*│\s*with\s+([^,\n]+)")
_LOCATION_LINE = re.compile(r"^\s*│\s*on\s+(\S+)\s+line\s+(\d+)(?:,\s*in\s+(.+))?:")


class DiagnosticParser:
    """Extract structured diagnostics from Terraform plan/apply log streams."""

    @classmethod
    def parse(cls, text: str) -> list[Diagnostic]:
        """Parse all diagnostics from log text (JSON-lines or plain text).

        Args:
            text: Raw log text from plan or apply execution

        Returns:
            List of parsed Diagnostic instances
        """
        if not text or not text.strip():
            return []

        clean_text = _ANSI_ESCAPE.sub("", text)
        lines = clean_text.splitlines()

        diagnostics: list[Diagnostic] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i].strip()

            # 1. Try JSON line
            if line.startswith("{") and ("diagnostic" in line or '"@level"' in line):
                diag = cls._parse_json_line(line)
                if diag:
                    diagnostics.append(diag)
                    i += 1
                    continue

            # 2. Try plain-text box start
            if _BOX_START.match(lines[i]):
                diag, end_idx = cls._parse_plain_text_box(lines, i)
                if diag:
                    diagnostics.append(diag)
                    i = end_idx
                    continue

            i += 1

        return diagnostics

    @classmethod
    def _parse_json_line(cls, line: str) -> Diagnostic | None:
        """Parse a single JSON stream line into a Diagnostic if applicable."""
        try:
            data = json.loads(line)
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        # Check if this is a diagnostic event
        if data.get("type") != "diagnostic" and "diagnostic" not in data:
            return None

        diag_obj = data.get("diagnostic", {})
        if not isinstance(diag_obj, dict):
            return None

        # Severity
        sev_raw = (diag_obj.get("severity") or data.get("@level") or "warning").lower()
        if "error" in sev_raw:
            severity = DiagnosticSeverity.ERROR
        elif "warn" in sev_raw:
            severity = DiagnosticSeverity.WARNING
        else:
            severity = DiagnosticSeverity.INFO

        # Summary
        summary = diag_obj.get("summary") or data.get("@message") or ""

        # Detail
        detail = diag_obj.get("detail")

        # Address
        address = diag_obj.get("address")

        # Range / Location
        range_data = diag_obj.get("range") or {}
        filename = range_data.get("filename")
        start = range_data.get("start") or {}
        line_num = start.get("line")

        # Extra
        extra = diag_obj.get("extra") or {}
        if not isinstance(extra, dict):
            extra = {}

        return Diagnostic(
            severity=severity,
            summary=summary,
            detail=detail,
            address=address,
            filename=filename,
            line=line_num,
            extra=extra,
        )

    @classmethod
    def _parse_plain_text_box(
        cls, lines: list[str], start_idx: int
    ) -> tuple[Diagnostic | None, int]:
        """Parse a unicode box-enclosed diagnostic block."""
        i = start_idx + 1
        n = len(lines)

        severity = DiagnosticSeverity.ERROR
        summary = ""
        detail_lines: list[str] = []
        address: str | None = None
        filename: str | None = None
        line_num: int | None = None

        while i < n:
            raw_line = lines[i]

            if _BOX_END.match(raw_line):
                i += 1
                break

            msg_match = _MSG_LINE.match(raw_line)
            if msg_match:
                sev_str, summary_str = msg_match.groups()
                severity = (
                    DiagnosticSeverity.ERROR
                    if sev_str.lower() == "error"
                    else DiagnosticSeverity.WARNING
                )
                summary = summary_str.strip()
                i += 1
                continue

            with_match = _WITH_LINE.match(raw_line)
            if with_match:
                address = with_match.group(1).strip()
                i += 1
                continue

            loc_match = _LOCATION_LINE.match(raw_line)
            if loc_match:
                filename = loc_match.group(1).strip()
                line_num = int(loc_match.group(2))
                ctx = loc_match.group(3)
                if ctx and not address:
                    address = ctx.strip()
                i += 1
                continue

            # Strip box border line and collect detail
            line_s = raw_line.strip()
            if line_s.startswith("│"):
                content = re.sub(r"^\s*│\s*", "", raw_line).strip()
                # Skip code snippet line numbering (e.g., " 12:   foo = bar") and separators
                if (
                    content
                    and not re.match(r"^\d+:\s+", content)
                    and content != "├────────────────"
                ):
                    detail_lines.append(content)

            i += 1

        if not summary:
            return None, i

        detail = "\n".join(detail_lines) if detail_lines else None

        return (
            Diagnostic(
                severity=severity,
                summary=summary,
                detail=detail,
                address=address,
                filename=filename,
                line=line_num,
            ),
            i,
        )
