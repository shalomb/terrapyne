# ruff: noqa
"""Terraform plain text plan parser.

This module provides TerraformPlainTextPlanParser, which parses plain text
terraform plan output and converts it to PlanInspector-compatible JSON format.

This parser is specifically designed to work around Terraform Cloud (TFC) remote
backend limitations, which don't support `terraform plan -json` JSON output or
`terraform plan -out=` plan saving.

The parser:
- Strips ANSI escape codes (TFC and GitLab formats)
- Extracts resource changes from plain text
- Parses complex attributes (arrays, maps, nested structures)
- Handles errors gracefully
- Outputs PlanInspector-compatible JSON format
"""

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


# Intermediate Representation (IR) Classes
@dataclass
class Change:
    """Represents a resource change (before/after state and actions)."""

    actions: list[str]
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format (PlanInspector-compatible).

        Includes before/after even if None, as PlanInspector expects them.
        """
        result: dict[str, Any] = {
            "actions": self.actions,
        }
        # Include before/after even if None (PlanInspector format)
        result["before"] = self.before
        result["after"] = self.after
        return result


@dataclass
class ResourceChange:
    """Represents a single resource change in the plan."""

    address: str
    type: str
    name: str
    change: Change

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "address": self.address,
            "type": self.type,
            "name": self.name,
            "change": self.change.to_dict(),
        }


@dataclass
class PlanIR:
    """Intermediate representation of a Terraform plan."""

    resource_changes: list[ResourceChange] = field(default_factory=list)
    format_version: str = "1.0"
    plan_summary: dict[str, int] | None = None
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    plan_status: str | None = None

    def to_plan_inspector_format(self) -> dict[str, Any]:
        """Convert IR to PlanInspector-compatible JSON format.

        Returns:
            Dictionary compatible with terraform show -json plan.tfplan format
        """
        result: dict[str, Any] = {
            "resource_changes": [rc.to_dict() for rc in self.resource_changes],
            "format_version": self.format_version,
            "plan_summary": self.plan_summary
            if self.plan_summary is not None
            else {"add": 0, "change": 0, "destroy": 0},
            "diagnostics": self.diagnostics if self.diagnostics else [],
        }

        if self.plan_status:
            result["plan_status"] = self.plan_status

        return result


class AttributeParser(ABC):
    """Base class for attribute parsing strategies.

    Each concrete strategy handles a specific attribute type (simple, array, map, etc.)
    """

    @abstractmethod
    def can_parse(self, line: str, lines: list[str], idx: int) -> bool:
        """Check if this parser can handle the given line.

        Args:
            line: Current line to parse
            lines: All lines (for context)
            idx: Current index in lines

        Returns:
            True if this parser can handle the line
        """
        pass

    @abstractmethod
    def parse(self, key: str, value_str: str, lines: list[str], idx: int) -> tuple[Any, int]:
        """Parse the attribute value.

        Args:
            key: Attribute key
            value_str: Value string from the line
            lines: All lines (for multi-line parsing)
            idx: Current index in lines

        Returns:
            Tuple of (parsed_value, next_index)
        """
        pass


class SimpleAttributeParser(AttributeParser):
    """Parser for simple key=value attributes."""

    def can_parse(self, line: str, lines: list[str], idx: int) -> bool:
        """Simple attributes are single-line key=value or key: value."""
        # This is the fallback parser - it handles everything that other parsers don't
        # Check if it's NOT an array, map, or computed value
        stripped = line.strip()
        # Check if value part ends with '[' or '{' (array/map start)
        if "=" in stripped or ":" in stripped:
            value_part = stripped.split("=", 1)[-1].split(":", 1)[-1].strip()
            if value_part.endswith("[") or value_part.endswith("{"):
                return False
        # Check for computed markers
        if (
            "<computed>" in stripped
            or "(sensitive value)" in stripped
            or "(known after apply)" in stripped
        ):
            return False
        # Everything else is a simple attribute
        return True

    def parse(self, key: str, value_str: str, lines: list[str], idx: int) -> tuple[Any, int]:
        """Parse simple attribute value."""
        # Check for change notation (old -> new)
        if " -> " in value_str:
            parts = value_str.split(" -> ", 1)
            before_str = parts[0].strip()
            after_str = parts[1].strip()
            # Use a helper to parse values (will be moved to parser instance)
            # For now, return structure that will be processed
            return {"before": before_str, "after": after_str}, idx
        else:
            # Simple value - return as-is for now (will be parsed by _parse_value)
            return value_str, idx


class ComputedAttributeParser(AttributeParser):
    """Parser for computed, sensitive, or known-after-apply values."""

    COMPUTED_MARKERS: ClassVar[list[str]] = [
        "<computed>",
        "(sensitive value)",
        "(known after apply)",
    ]

    def can_parse(self, line: str, lines: list[str], idx: int) -> bool:
        """Check if line contains computed value markers."""
        return any(marker in line for marker in self.COMPUTED_MARKERS)

    def parse(self, key: str, value_str: str, lines: list[str], idx: int) -> tuple[Any, int]:
        """Parse computed value - return the marker as-is."""
        # Extract the computed marker
        for marker in self.COMPUTED_MARKERS:
            if marker in value_str:
                return marker, idx
        return value_str, idx


class ArrayAttributeParser(AttributeParser):
    """Parser for array attributes."""

    def can_parse(self, line: str, lines: list[str], idx: int) -> bool:
        """Check if line starts an array (ends with '[')."""
        stripped = line.strip()
        # Check if value part ends with '['
        if "=" in stripped or ":" in stripped:
            value_part = stripped.split("=", 1)[-1].split(":", 1)[-1].strip()
            return value_part.endswith("[")
        return False

    def parse(self, key: str, value_str: str, lines: list[str], idx: int) -> tuple[Any, int]:
        """Parse array attribute (multi-line)."""
        array_lines = []
        i = idx
        bracket_count = 0

        # Start with the current line (which contains the opening bracket)
        line = lines[i]
        bracket_count += line.count("[")
        bracket_count -= line.count("]")

        # Extract initial content after [
        initial_content = line.split("[", 1)[-1].strip()
        if initial_content:
            if initial_content.endswith("]"):
                initial_content = initial_content[:-1].strip()
            if initial_content:
                array_lines.extend(
                    [v.strip().strip('"') for v in initial_content.split(",") if v.strip()]
                )

        # Continue parsing until brackets are balanced
        if bracket_count > 0:
            i += 1
            while i < len(lines) and bracket_count > 0:
                line = lines[i]
                bracket_count += line.count("[")
                bracket_count -= line.count("]")

                # Extract content from line
                content = line.strip()
                if content.endswith("]"):
                    content = content[:-1].strip()
                if content.endswith(","):
                    content = content[:-1].strip()

                if content:
                    array_lines.append(content.strip('"'))
                i += 1
        else:
            i += 1

        return array_lines, i


class MapAttributeParser(AttributeParser):
    """Parser for map attributes."""

    def can_parse(self, line: str, lines: list[str], idx: int) -> bool:
        """Check if line starts a map (ends with '{')."""
        stripped = line.strip()
        # Check if value part ends with '{'
        if "=" in stripped or ":" in stripped:
            value_part = stripped.split("=", 1)[-1].split(":", 1)[-1].strip()
            return value_part.endswith("{")
        return False

    def parse(self, key: str, value_str: str, lines: list[str], idx: int) -> tuple[Any, int]:
        """Parse map attribute (multi-line)."""
        # Maps are currently parsed as strings (known limitation)
        # This is a placeholder for future enhancement
        map_lines = []
        i = idx
        brace_count = 0

        # Start with the current line (which contains the opening brace)
        line = lines[i]
        brace_count += line.count("{")
        brace_count -= line.count("}")
        map_lines.append(line)

        # Continue parsing until braces are balanced
        i += 1
        while i < len(lines) and brace_count > 0:
            line = lines[i]
            brace_count += line.count("{")
            brace_count -= line.count("}")
            map_lines.append(line)
            i += 1

        # Return the map as a string (known limitation)
        return "\n".join(map_lines), i


class AttributeParserDispatcher:
    """Dispatches attribute parsing to appropriate strategy."""

    def __init__(self, parse_value_func: Callable[[str], Any]) -> None:
        """Initialize dispatcher with value parsing function.

        Args:
            parse_value_func: Function to parse simple values (from parser instance)
        """
        self._parse_value = parse_value_func
        # Order matters - more specific parsers first
        self._parsers = [
            ComputedAttributeParser(),
            ArrayAttributeParser(),
            MapAttributeParser(),
            SimpleAttributeParser(),  # Most general, comes last
        ]

    def parse_attribute(
        self, key: str, value_str: str, line: str, lines: list[str], idx: int
    ) -> tuple[Any, int]:
        """Parse attribute using appropriate strategy.

        Args:
            key: Attribute key
            value_str: Value string from line
            line: Full line
            lines: All lines
            idx: Current index

        Returns:
            Tuple of (parsed_value, next_index)
        """
        # Find first parser that can handle this line
        for parser in self._parsers:
            if parser.can_parse(line, lines, idx):
                parsed_value, next_idx = parser.parse(key, value_str, lines, idx)
                # If it's a simple value string, parse it with _parse_value
                if isinstance(parsed_value, str):
                    # Check if it's a change notation
                    if " -> " in parsed_value:
                        parts = parsed_value.split(" -> ", 1)
                        before_str = parts[0].strip()
                        after_str = parts[1].strip()
                        return {
                            "before": self._parse_value(before_str),
                            "after": self._parse_value(after_str),
                        }, next_idx
                    else:
                        return self._parse_value(parsed_value), next_idx

                # If it's already a complex type (like list from ArrayAttributeParser),
                # just return it. The InAttributesStateHandler will handle wrapping
                # it in after_attrs if it's not a before/after dict.
                if (
                    isinstance(parsed_value, dict)
                    and "before" in parsed_value
                    and "after" in parsed_value
                ):
                    # Already a change dict, but values might be strings
                    if isinstance(parsed_value["before"], str):
                        parsed_value["before"] = self._parse_value(parsed_value["before"])
                    if isinstance(parsed_value["after"], str):
                        parsed_value["after"] = self._parse_value(parsed_value["after"])
                    return parsed_value, next_idx
                else:
                    return parsed_value, next_idx

        # Fallback to simple parsing
        return self._parse_value(value_str), idx


class ParserState(Enum):
    """States for the parser state machine."""

    SEARCHING = "searching"  # Looking for a resource
    IN_RESOURCE_HEADER = "in_resource_header"  # Found resource, extracting header info
    IN_ATTRIBUTES = "in_attributes"  # Parsing resource attributes
    DONE = "done"  # Finished parsing a resource


class StateHandler(ABC):
    """Base class for state handlers in the parser state machine."""

    @abstractmethod
    def handle(
        self, lines: list[str], idx: int, context: dict[str, Any]
    ) -> tuple[ParserState, int, ResourceChange | None]:
        """Handle the current state.

        Args:
            lines: All lines to parse
            idx: Current index in lines
            context: Shared context dictionary (stores resource data, etc.)

        Returns:
            Tuple of (next_state, next_index, ResourceChange IR object or None)
        """
        pass


class SearchingStateHandler(StateHandler):
    """Handler for SEARCHING state - looks for resource comments or action symbols."""

    def __init__(self, parser_instance: Any) -> None:
        """Initialize with parser instance for access to patterns and methods."""
        self.parser = parser_instance

    def handle(
        self, lines: list[str], idx: int, context: dict[str, Any]
    ) -> tuple[ParserState, int, ResourceChange | None]:
        """Search for resource indicators."""
        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()

            if not stripped:
                idx += 1
                continue

            # Check for resource comment
            comment_match = self.parser.RESOURCE_COMMENT_PATTERN.match(stripped)
            if comment_match:
                # Extract resource info and transition to IN_RESOURCE_HEADER
                if comment_match.group(1):  # "is tainted, so must be replaced"
                    address = comment_match.group(1)
                    action_text = "replaced"
                elif comment_match.group(2):  # "(tainted) must be replaced"
                    address = comment_match.group(2)
                    action_text = "replaced"
                elif comment_match.group(3):  # "must be replaced"
                    address = comment_match.group(3)
                    action_text = "replaced"
                else:  # "will be ..."
                    address = comment_match.group(4)
                    action_text = comment_match.group(5) or "update"

                if address:
                    context["address"] = address
                    context["action_text"] = action_text
                    context["resource_start_idx"] = idx
                    return ParserState.IN_RESOURCE_HEADER, idx, None

            # Check for action symbol with resource/data
            symbol_match = self.parser.ACTION_SYMBOL_PATTERN.match(stripped)
            if symbol_match:
                rest = symbol_match.group(2).strip()
                # Check if it's a resource declaration
                if "resource" in rest.lower() or "data" in rest.lower():
                    # Extract address from resource declaration
                    resource_match = re.match(r'(?:resource|data)\s+"([^"]+)"\s+"([^"]+)"', rest)
                    if resource_match:
                        resource_type = resource_match.group(1)
                        resource_name = resource_match.group(2)
                        address = f"{resource_type}.{resource_name}"
                        symbol = symbol_match.group(1)
                        actions = self.parser._symbol_to_actions(symbol)

                        context["address"] = address
                        context["actions"] = actions
                        context["resource_type"] = resource_type
                        context["resource_name"] = resource_name
                        context["resource_start_idx"] = idx
                        # Skip directly to attributes (no header processing needed)
                        return ParserState.IN_ATTRIBUTES, idx + 1, None
                elif (
                    "." in rest and "=" not in rest and ":" not in rest.split()[0]
                    if rest.split()
                    else False
                ):
                    # Short format: "~ aws_instance.web"
                    address = rest.split()[0] if rest.split() else rest
                    if " (new resource required)" in address:
                        address = address.replace(" (new resource required)", "")
                    symbol = symbol_match.group(1)
                    actions = self.parser._symbol_to_actions(symbol)
                    resource_type, resource_name = self.parser._extract_resource_type_name(address)

                    context["address"] = address
                    context["actions"] = actions
                    context["resource_type"] = resource_type
                    context["resource_name"] = resource_name
                    context["resource_start_idx"] = idx
                    return ParserState.IN_ATTRIBUTES, idx + 1, None

            idx += 1

        return ParserState.DONE, idx, None


class InResourceHeaderStateHandler(StateHandler):
    """Handler for IN_RESOURCE_HEADER state - extracts resource info from comment."""

    def __init__(self, parser_instance: Any) -> None:
        """Initialize with parser instance."""
        self.parser = parser_instance

    def handle(
        self, lines: list[str], idx: int, context: dict[str, Any]
    ) -> tuple[ParserState, int, ResourceChange | None]:
        """Extract resource header information."""
        address = context.get("address")
        action_text = context.get("action_text")

        if not address:
            return ParserState.SEARCHING, idx + 1, None

        actions = self.parser._action_text_to_actions(action_text)
        resource_type, resource_name = self.parser._extract_resource_type_name(address)

        context["actions"] = actions
        context["resource_type"] = resource_type
        context["resource_name"] = resource_name

        # Skip the action symbol line that typically follows (e.g., "+ resource ...")
        attr_start = idx + 1
        if attr_start < len(lines):
            next_line = lines[attr_start].strip()
            symbol_match = self.parser.ACTION_SYMBOL_PATTERN.match(next_line)
            if symbol_match and (
                "resource" in symbol_match.group(2).lower()
                or "data" in symbol_match.group(2).lower()
            ):
                attr_start = idx + 2

        # Transition to parsing attributes
        return ParserState.IN_ATTRIBUTES, attr_start, None


class InAttributesStateHandler(StateHandler):
    """Handler for IN_ATTRIBUTES state - parses resource attributes."""

    def __init__(self, parser_instance: Any) -> None:
        """Initialize with parser instance."""
        self.parser = parser_instance

    def handle(
        self, lines: list[str], idx: int, context: dict[str, Any]
    ) -> tuple[ParserState, int, ResourceChange | None]:
        """Parse resource attributes."""
        # Parse attributes using existing method
        attributes, attr_next_idx = self.parser._parse_attributes(lines, idx)

        # Process attributes into before/after
        actions = context.get("actions", [])
        before_attrs = {}
        after_attrs = {}

        for key, value in attributes.items():
            if isinstance(value, dict) and "before" in value and "after" in value:
                # Attribute change
                if value["before"] is not None:
                    before_attrs[key] = value["before"]
                if value["after"] is not None:
                    after_attrs[key] = value["after"]
            else:
                # Simple attribute (no change)
                if "create" not in actions and "import" not in actions:
                    # For updates/deletes, existing attributes go in before
                    before_attrs[key] = value
                if "delete" not in actions:
                    # For creates/updates, attributes go in after
                    after_attrs[key] = value

        # Build ResourceChange IR object
        address = context.get("address")
        resource_type = context.get("resource_type")
        resource_name = context.get("resource_name")

        # Ensure required fields are strings (mypy type safety)
        if not address or not resource_type or not resource_name:
            # If critical fields are missing, return None (shouldn't happen in practice)
            return ParserState.DONE, attr_next_idx, None

        change = Change(
            actions=actions,
            before=before_attrs
            if before_attrs
            else (None if "create" in actions or "import" in actions else {}),
            after=after_attrs if after_attrs else (None if "delete" in actions else {}),
        )

        resource = ResourceChange(
            address=str(address), type=str(resource_type), name=str(resource_name), change=change
        )

        # Transition to DONE, then back to SEARCHING
        return ParserState.DONE, attr_next_idx, resource


class ParserStateMachine:
    """State machine for parsing Terraform plan resources."""

    def __init__(self, parser_instance: Any) -> None:
        """Initialize state machine with parser instance."""
        self.parser = parser_instance
        self.state = ParserState.SEARCHING
        self.handlers = {
            ParserState.SEARCHING: SearchingStateHandler(parser_instance),
            ParserState.IN_RESOURCE_HEADER: InResourceHeaderStateHandler(parser_instance),
            ParserState.IN_ATTRIBUTES: InAttributesStateHandler(parser_instance),
        }
        self.context: dict[str, Any] = {}

    def reset(self) -> None:
        """Reset state machine for new parsing session."""
        self.state = ParserState.SEARCHING
        self.context = {}

    def parse_resources(self, lines: list[str]) -> list[ResourceChange]:
        """Parse all resources using state machine.

        Args:
            lines: List of lines to parse

        Returns:
            List of ResourceChange IR objects
        """
        resources = []
        idx = 0
        self.reset()

        while idx < len(lines) and self.state != ParserState.DONE:
            handler = self.handlers.get(self.state)
            if not handler:
                break

            next_state, next_idx, resource = handler.handle(lines, idx, self.context)

            if resource:
                resources.append(resource)
                # Reset context for next resource
                self.context = {}

            # Handle state transitions
            if next_state == ParserState.DONE:
                # After DONE, go back to SEARCHING for next resource
                self.state = ParserState.SEARCHING
            else:
                self.state = next_state

            idx = next_idx

        return resources


class TerraformPlainTextPlanParser:
    """
    Parses plain text terraform plan output and converts to PlanInspector-compatible JSON.

    LIMITATION: This parser exists because Terraform Cloud (TFC) remote backend
    does not support:
    - terraform plan -json (only outputs version message, then plain text)
    - terraform plan -out=plan.tfplan (fails with "not supported" error)

    This parser extracts plan data from plain text output, handling:
    - ANSI escape codes (TFC and GitLab formats)
    - Resource comment lines (# resource will be created/destroyed/updated)
    - Action symbol lines (+ - ~ -/+ <=)
    - Attribute changes (simple, arrays, maps, nested)
    - Plan summary (Plan: X to add, Y to change, Z to destroy)

    Output format matches terraform show -json plan.tfplan structure:
    {
      "resource_changes": [
        {
          "address": "module.rds[...].aws_db_instance.rds",
          "type": "aws_db_instance",
          "change": {
            "actions": ["import"],
            "before": {...},
            "after": {...}
          }
        }
      ],
      "format_version": "1.0"
    }
    """

    # ANSI escape sequence pattern
    # Handles:
    # - Real ANSI codes (\x1b[1m)
    # - Bracket notation ([1m) used in tests
    # - Literal escape sequences (\033[1m) used in GitLab CI
    ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m|\\033\[[0-9;]*m|\[[0-9;]*m")

    # Resource comment patterns
    # Order matters: more specific patterns first
    RESOURCE_COMMENT_PATTERN = re.compile(
        r"^\s*#\s+(.+?)\s+is tainted, so must be replaced"
        r"|^\s*#\s+(.+?)\s+\(tainted\)\s+must be replaced"
        r"|^\s*#\s+(.+?)\s+must be replaced"
        r"|^\s*#\s+(.+?)\s+will be (created|destroyed|updated in-place|imported|replaced)"
    )

    # Action symbol patterns
    ACTION_SYMBOL_PATTERN = re.compile(r"^[\s]*([+\-~]|-\+|\+\-|<=)\s+(.+)$")

    # Plan summary pattern
    # Handles both orders: "X to add, Y to change, Z to destroy, W to import"
    # and "W to import, X to add, Y to change, Z to destroy"
    PLAN_SUMMARY_PATTERN = re.compile(
        r"Plan:\s*(?:(\d+)\s+to import,\s+)?(\d+)\s+to add,\s*(\d+)\s+to change,\s*(\d+)\s+to destroy"
        r"(?:,\s*(\d+)\s+to import)?\."
    )

    # Start marker for parseable content
    START_MARKER = "Terraform will perform the following actions:"

    # Error box pattern - Terraform uses box-drawing characters for errors
    # Pattern matches: ╷ (top), │ (sides), ╵ (bottom)
    ERROR_BOX_START = re.compile(r"^[╷┌]")  # Start of error box
    ERROR_BOX_END = re.compile(r"^[╵└]")  # End of error box
    ERROR_LINE_PATTERN = re.compile(r"^\s*│\s*Error:\s*(.+)$")  # Error: <message>

    # Error location pattern: "on <file> line <line>, in <context>:"
    ERROR_LOCATION_PATTERN = re.compile(
        r"^\s*│\s+on\s+([^\s]+)\s+line\s+(\d+)(?:,\s+in\s+(.+?))?:\s*$"
    )

    # Error "with" pattern: "with <address>,"
    ERROR_WITH_PATTERN = re.compile(r"^\s*│\s+with\s+(.+?)(?:,\s*)?$")

    # Error code line pattern: "<line>:   <code>"
    ERROR_CODE_LINE_PATTERN = re.compile(r"^\s*│\s+(\d+):\s+(.+)$")

    # Error variable/value pattern: "│ <variable> is <value>"
    ERROR_VARIABLE_PATTERN = re.compile(r"^\s*│\s+([^\s]+)\s+is\s+(.+)$")

    # Operation failed pattern
    OPERATION_FAILED_PATTERN = re.compile(r"Operation failed:.*\(exit\s+(\d+)\)", re.IGNORECASE)

    def __init__(self, plan_text: str):
        """Initialize parser with plain text plan output.

        Args:
            plan_text: Plain text terraform plan output (may contain ANSI codes)
        """
        self.plan_text = plan_text
        self._resource_changes: list[dict[str, Any]] | None = None
        self._plan_summary: dict[str, int] | None = None
        self._diagnostics: list[dict[str, Any]] | None = None
        # Initialize attribute parser dispatcher with value parsing function
        self._attr_dispatcher = AttributeParserDispatcher(self._parse_value)
        # Initialize state machine for resource parsing
        self._state_machine = ParserStateMachine(self)

    @staticmethod
    def strip_ansi_codes(text: str) -> str:
        """Strip ANSI escape codes from text.

        Handles both TFC and GitLab CI format ANSI codes.
        Aligned with patterns from Pacobart, drlau, and lifeomic parsers.

        Args:
            text: Text potentially containing ANSI escape codes

        Returns:
            Text with all ANSI escape codes removed

        Examples:
            >>> TerraformPlainTextPlanParser.strip_ansi_codes("[1m  # resource[0m")
            '  # resource'
            >>> TerraformPlainTextPlanParser.strip_ansi_codes("[1m[31mError:[0m[0m")
            'Error:'
        """
        return TerraformPlainTextPlanParser.ANSI_ESCAPE_PATTERN.sub("", text)

    def parse(self) -> dict[str, Any]:
        """Parse plain text and return PlanInspector-compatible JSON.

        Internally uses PlanIR (Intermediate Representation) and converts
        to PlanInspector format at the end.

        Returns:
            Dictionary with structure:
            {
                "resource_changes": [...],
                "format_version": "1.0"
            }

        Raises:
            ValueError: If plan text is empty or invalid
        """
        # Parse to IR, then convert to PlanInspector format
        plan_ir = self.parse_to_ir()
        return plan_ir.to_plan_inspector_format()

    def parse_to_ir(self) -> PlanIR:
        """Parse plain text and return PlanIR (Intermediate Representation).

        This method returns the IR directly without converting to PlanInspector format.
        Useful for consumers that want to work with the IR directly.

        Returns:
            PlanIR object containing parsed plan data

        Raises:
            ValueError: If plan text is empty or invalid
        """
        if not self.plan_text or not self.plan_text.strip():
            return PlanIR()

        # Strip ANSI codes from entire plan text
        cleaned_text = self.strip_ansi_codes(self.plan_text)

        # Detect TFC 1.12+ structured JSON log format early — every non-empty,
        # non-header line starts with '{'.  These logs have no plain-text plan
        # section so resource-level parsing is not possible.
        if self._is_structured_json_log(cleaned_text):
            plan_summary = self._parse_plan_summary_from_json_log(cleaned_text)
            diagnostic = {
                "severity": "warning",
                "summary": "Structured JSON log format detected",
                "detail": (
                    "This input is a TFC structured JSON log (Terraform 1.12+). "
                    "Resource-level parsing is not available for this format — "
                    "only the plan summary counts are extracted. "
                    "Use terraform plan -json (outside TFC) for full resource details."
                ),
            }
            return PlanIR(
                resource_changes=[],
                format_version="1.0",
                plan_summary=plan_summary,
                diagnostics=[diagnostic],
                plan_status="structured_log",
            )

        # Extract plain text portion (skip JSON version messages from TFC)
        plain_text = self._extract_plain_text(cleaned_text)

        # Parse diagnostics first (errors, warnings) - needed even if no parseable section
        diagnostics = self._parse_diagnostics(plain_text)

        # Find parseable section
        start_idx, end_idx = self._find_parseable_section(plain_text)

        # Parse resources from the parseable section (if found) - returns IR objects
        if start_idx == -1:
            resource_changes_ir = []
        else:
            lines = plain_text[start_idx:end_idx].splitlines()
            resource_changes_ir = self._parse_resources(lines)

        # Parse plan summary
        plan_summary = self._parse_plan_summary(plain_text)

        # Determine plan status
        plan_status = self._determine_plan_status(plain_text, resource_changes_ir, diagnostics)

        # Build and return PlanIR object
        return PlanIR(
            resource_changes=resource_changes_ir,
            format_version="1.0",
            plan_summary=plan_summary,
            diagnostics=diagnostics,
            plan_status=plan_status,
        )

    def _extract_plain_text(self, text: str) -> str:
        """Extract plain text portion from mixed content (JSON + plain text).

        TFC outputs JSON version message followed by plain text.
        This method extracts only the plain text portion.

        Args:
            text: Text that may contain JSON messages at the start

        Returns:
            Plain text portion (JSON messages removed)
        """
        # Look for first non-JSON line (doesn't start with { or [)
        lines = text.splitlines()
        plain_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip JSON lines (start with { or [) and empty lines
            if stripped and not (stripped.startswith("{") or stripped.startswith("[")):
                plain_start = i
                break

        return "\n".join(lines[plain_start:])

    def _find_parseable_section(self, text: str) -> tuple[int, int]:
        """Find start/end markers for parseable content.

        Looks for:
        - Start: "Terraform will perform the following actions:"
        - End: "Plan: X to add, Y to change, Z to destroy"

        Args:
            text: Plain text plan output

        Returns:
            Tuple of (start_index, end_index) or (-1, -1) if not found
        """
        start_idx = text.find(self.START_MARKER)
        if start_idx == -1:
            return (-1, -1)

        # Start after the marker line
        start_idx = text.find("\n", start_idx) + 1
        if start_idx == 0:
            start_idx = len(text)

        # Find end marker (Plan: summary)
        end_match = self.PLAN_SUMMARY_PATTERN.search(text, start_idx)
        if end_match:
            end_idx = end_match.start()
        else:
            # No end marker, use end of text
            end_idx = len(text)

        return (start_idx, end_idx)

    def _parse_resources(self, lines: list[str]) -> list[ResourceChange]:
        """Parse all resources from lines using state machine.

        Args:
            lines: List of lines from parseable section

        Returns:
            List of ResourceChange IR objects
        """
        # Use state machine for parsing (returns IR objects)
        return self._state_machine.parse_resources(lines)

    def _parse_resource_comment(self, comment_line: str) -> dict[str, Any] | None:
        """Parse a resource comment line to extract address and action.

        Args:
            comment_line: Comment line like "# aws_instance.web will be created"

        Returns:
            Dictionary with "address" and "action" keys, or None if not a resource comment
        """
        comment_match = self.RESOURCE_COMMENT_PATTERN.match(comment_line.strip())
        if comment_match:
            # Groups: (tainted_is_address, tainted_paren_address, must_replace_address, will_be_address, action_text)
            # Check groups in order of specificity
            if comment_match.group(1):  # "is tainted, so must be replaced"
                address = comment_match.group(1)
                action_text = "replaced"
            elif comment_match.group(2):  # "(tainted) must be replaced"
                address = comment_match.group(2)
                action_text = "replaced"
            elif comment_match.group(3):  # "must be replaced"
                address = comment_match.group(3)
                action_text = "replaced"
            else:  # "will be ..."
                address = comment_match.group(4)
                action_text = comment_match.group(5) or "update"

            actions = self._action_text_to_actions(action_text)
            # Return first action as string for test compatibility
            action = actions[0] if actions else "update"
            return {"address": address, "action": action}
        return None

    def _parse_value(self, value_str: str) -> Any:
        """Parse a single value string into Python value.

        Args:
            value_str: Value string from terraform plan

        Returns:
            Parsed value (str, int, float, None, or special markers)
        """
        value_str = value_str.strip()

        # Try to parse as JSON-like list/dict (for arrays/maps) first
        # Remove any trailing comments like "# forces replacement"
        clean_value = value_str.split(" #", 1)[0].strip()

        if (clean_value.startswith("[") and clean_value.endswith("]")) or (
            clean_value.startswith("{") and clean_value.endswith("}")
        ):
            # Try to fix non-standard JSON (no quotes around strings)
            # This is common in terraform plain text output
            potential_json = clean_value.replace('\\"', '"')
            try:
                return json.loads(potential_json)
            except json.JSONDecodeError:
                # Fallback: simple manual split for [a, b, c]
                if clean_value.startswith("[") and clean_value.endswith("]"):
                    content = clean_value[1:-1].strip()
                    if not content:
                        return []
                    return [v.strip().strip('"') for v in content.split(",") if v.strip()]
                pass

        # Strip metadata suffixes like "(forces new resource)" or "(new resource required)"
        if " (forces new resource)" in value_str:
            value_str = value_str.replace(" (forces new resource)", "").strip()
        if " (new resource required)" in value_str:
            value_str = value_str.replace(" (new resource required)", "").strip()

        # Handle other types
        if value_str in ["<computed>", "(sensitive value)", "(known after apply)"]:
            return value_str
        elif value_str == "null":
            return None
        elif (value_str.startswith('"') and value_str.endswith('"')) or (
            value_str.startswith("'") and value_str.endswith("'")
        ):
            return value_str[1:-1]  # Remove quotes
        # Handle escaped quotes (e.g., \"ami-old\")
        elif value_str.startswith('\\"') and value_str.endswith('\\"'):
            return value_str[2:-2]  # Remove escaped quotes
        # Handle mixed escaped quotes (e.g., "\\"ami-old\\"")
        elif '\\"' in value_str:
            # Remove all escaped quotes
            return value_str.replace('\\"', "").replace('"', "")
        else:
            # Try to parse as number or boolean
            try:
                if "." in value_str:
                    return float(value_str)
                else:
                    return int(value_str)
            except ValueError:
                return value_str

    def _action_text_to_actions(self, action_text: str) -> list[str]:
        """Convert action text to actions list.

        Args:
            action_text: Text like "created", "destroyed", "updated in-place", "replaced"

        Returns:
            List of action strings like ["create"], ["delete"], ["update"], ["create", "delete"]
        """
        action_map = {
            "created": ["create"],
            "destroyed": ["delete"],
            "updated in-place": ["update"],
            "replaced": ["create", "delete"],
            "imported": ["import"],
        }
        return action_map.get(action_text, ["update"])

    def _symbol_to_actions(self, symbol: str) -> list[str]:
        """Convert action symbol to actions list.

        Args:
            symbol: Symbol like "+", "-", "~", "-/+", "<="

        Returns:
            List of action strings
        """
        symbol_map = {
            "+": ["create"],
            "-": ["delete"],
            "~": ["update"],
            "-/+": ["create", "delete"],
            "+/-": ["create", "delete"],
            "<=": ["import"],
        }
        return symbol_map.get(symbol, ["update"])

    def _extract_resource_type_name(self, address: str) -> tuple[str, str]:
        """Extract resource type and name from address.

        Args:
            address: Resource address like "aws_instance.web" or "module.rds[...].aws_db_instance.rds"

        Returns:
            Tuple of (resource_type, resource_name)
        """
        # Split by dots and find the last two parts that look like resource type and name
        parts = address.split(".")
        if len(parts) >= 2:
            # Look for pattern like "aws_*" or "data.*"
            for i in range(len(parts) - 1, 0, -1):
                if parts[i - 1].startswith("aws_") or parts[i - 1] == "data":
                    return parts[i - 1], parts[i]

        # Fallback: return last two parts
        if len(parts) >= 2:
            return parts[-2], parts[-1]

        return address, address

    def _parse_attributes(self, lines: list[str], start_idx: int) -> tuple[dict[str, Any], int]:
        """Parse resource attributes from lines.

        This is a simplified version - full implementation will handle
        nested structures, arrays, maps, etc.

        Args:
            lines: List of lines
            start_idx: Starting index

        Returns:
            Tuple of (attributes_dict, next_index)
        """
        attributes = {}
        i = start_idx
        indent_level = None

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Empty line - continue (but check if next line is a resource comment)
            if not stripped:
                # Check if next line is a resource comment
                if i + 1 < len(lines):
                    next_stripped = lines[i + 1].strip()
                    if next_stripped.startswith("#") and self.RESOURCE_COMMENT_PATTERN.match(
                        next_stripped
                    ):
                        i += 1  # Skip empty line and break at resource comment
                        break
                i += 1
                continue

            # Check if we've moved to next resource
            # Resource comments always indicate a new resource
            if stripped.startswith("#"):
                # Check if it's a resource comment (not just any comment)
                if self.RESOURCE_COMMENT_PATTERN.match(stripped):
                    break
            # Action symbol lines only indicate new resource if they contain "resource" or "data"
            symbol_match = self.ACTION_SYMBOL_PATTERN.match(stripped)
            if symbol_match and (
                "resource" in symbol_match.group(2).lower()
                or "data" in symbol_match.group(2).lower()
            ):
                break

            # Calculate current indent
            current_indent = len(line) - len(line.lstrip())
            if indent_level is None:
                indent_level = current_indent

            # If indent decreased significantly (more than 2 spaces), we're done
            # This handles closing braces and next resources
            # But allow some variation for attribute changes (which may have different indentation)
            if current_indent < indent_level - 2:
                break

            # Parse attribute (key = value or key: value)
            # Support keys like "tags.%", "tags_all", etc. (allow . and % in key names)
            attr_match = re.match(
                r"^\s*([+\-~]?\s*)?([a-zA-Z_][a-zA-Z0-9_.%]*)\s*[:=]\s*(.+)$", line
            )
            if attr_match:
                key = attr_match.group(2)
                value_str = attr_match.group(3).strip()

                # Use dispatcher to parse attribute with appropriate strategy
                parsed_value, next_idx = self._attr_dispatcher.parse_attribute(
                    key, value_str, line, lines, i
                )
                attributes[key] = parsed_value

                # Also store under base key for compatibility if desired
                if "." in key:
                    base_key = key.split(".")[0]
                    if base_key not in attributes:
                        attributes[base_key] = parsed_value

                # Update index if dispatcher advanced it (for multi-line attributes)
                if next_idx > i:
                    i = next_idx
                    continue

            i += 1

        return attributes, i

    def _parse_plan_summary(self, text: str) -> dict[str, int] | None:
        """Extract plan summary counts.

        Args:
            text: Plain text plan output

        Returns:
            Dictionary with add, change, destroy, import counts or None if not found
        """
        match = self.PLAN_SUMMARY_PATTERN.search(text)
        if match:
            # Groups: (import_first, add, change, destroy, import_last)
            import_count = 0
            if match.group(1):  # Import at start
                import_count = int(match.group(1))
            elif match.group(5):  # Import at end
                import_count = int(match.group(5))

            return {
                "add": int(match.group(2)),
                "change": int(match.group(3)),
                "destroy": int(match.group(4)),
                "import": import_count,
            }
        return None

    def _parse_diagnostics(self, text: str) -> list[dict[str, Any]]:
        """Parse diagnostics (errors, warnings) from plan text.

        Args:
            text: Plain text plan output

        Returns:
            List of diagnostic dictionaries with severity, summary, detail, etc.
        """
        diagnostics = []
        lines = text.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for error box start
            if self.ERROR_BOX_START.match(line):
                error_diag, end_idx = self._parse_error_box(lines, i)
                if error_diag:
                    diagnostics.append(error_diag)
                    # Skip to end of error box
                    i = end_idx
                    continue

            i += 1

        return diagnostics

    def _parse_error_box(
        self, lines: list[str], start_idx: int
    ) -> tuple[dict[str, Any] | None, int]:
        """Parse a single error box from lines.

        Terraform error format:
        ╷
        │ Error: <message>
        │
        │   on <file> line <line>, in <context>:
        │   <line>:   <code>
        │     ├────────────────
        │     │ <variable> is <value>
        │
        │ <error_detail>
        │
        │ <additional_context>
        ╵

        Args:
            lines: List of lines
            start_idx: Starting index of error box

        Returns:
            Tuple of (diagnostic_dict, end_index) or (None, start_idx + 1) if not a valid error box
        """
        if start_idx >= len(lines):
            return None, start_idx + 1

        # Must start with error box character
        if not self.ERROR_BOX_START.match(lines[start_idx]):
            return None, start_idx + 1

        diagnostic: dict[str, Any] = {
            "severity": "error",
            "summary": "",
            "detail": "",
            "address": None,
            "range": {
                "filename": None,
                "start": {"line": None, "column": None},
                "end": {"line": None, "column": None},
            },
        }

        i = start_idx
        error_message = None
        error_detail_lines = []
        in_error_detail = False
        code_line = None
        variable_info = None
        address = None

        while i < len(lines):
            line = lines[i]

            # Check for error box end
            if self.ERROR_BOX_END.match(line):
                end_idx = i + 1
                break

            # Extract error message: "│ Error: <message>"
            error_match = self.ERROR_LINE_PATTERN.match(line)
            if error_match:
                error_message = error_match.group(1).strip()
                diagnostic["summary"] = error_message
                in_error_detail = False
                i += 1
                continue

            # Extract "with" address: "│   with <address>,"
            # This should come before "on" location and takes precedence
            with_match = self.ERROR_WITH_PATTERN.match(line)
            if with_match:
                address = with_match.group(1).strip()
                diagnostic["address"] = address
                i += 1
                continue

            # Extract location: "│   on <file> line <line>, in <context>:"
            location_match = self.ERROR_LOCATION_PATTERN.match(line)
            if location_match:
                filename = location_match.group(1)
                line_num = int(location_match.group(2))
                context = location_match.group(3) if location_match.group(3) else None

                diagnostic["range"]["filename"] = filename
                diagnostic["range"]["start"]["line"] = line_num
                diagnostic["range"]["end"]["line"] = line_num

                # Only set address from context if we don't already have one from "with"
                if context and not diagnostic.get("address"):
                    diagnostic["address"] = context
                    address = context

                i += 1
                continue

            # Extract code line: "│   <line>:   <code>"
            code_match = self.ERROR_CODE_LINE_PATTERN.match(line)
            if code_match:
                code_line = code_match.group(2).strip()
                i += 1
                continue

            # Extract variable info: "│     │ <variable> is <value>"
            var_match = self.ERROR_VARIABLE_PATTERN.match(line)
            if var_match:
                variable_info = f"{var_match.group(1)} is {var_match.group(2).strip()}"
                i += 1
                continue

            # Collect error detail lines (everything else between error message and end)
            # Skip if we've already processed this line as a special pattern
            if error_message and line.strip():
                # Check if this is a detail line (starts with │ but not a special pattern)
                if line.strip().startswith("│"):
                    # Check if it's not an error box end
                    if not self.ERROR_BOX_END.match(line):
                        # Check if it's not a special pattern we've already handled
                        if (
                            not self.ERROR_LOCATION_PATTERN.match(line)
                            and not self.ERROR_WITH_PATTERN.match(line)
                            and not self.ERROR_CODE_LINE_PATTERN.match(line)
                            and not self.ERROR_VARIABLE_PATTERN.match(line)
                        ):
                            # Strip leading │ and whitespace
                            detail_line = re.sub(r"^\s*│\s*", "", line).strip()
                            if detail_line and detail_line != "├────────────────":
                                error_detail_lines.append(detail_line)
                                in_error_detail = True

            i += 1

        # Build detail message
        detail_parts = []
        if variable_info:
            detail_parts.append(variable_info)
        if code_line:
            detail_parts.append(f"Code: {code_line}")
        if error_detail_lines:
            detail_parts.extend(error_detail_lines)

        diagnostic["detail"] = "\n".join(detail_parts) if detail_parts else error_message or ""

        # If we didn't find an end, set end_index to current position
        if "end_idx" not in locals():
            end_idx = i

        # Only return if we found an error message
        if error_message:
            return diagnostic, end_idx

        return None, start_idx + 1

    def _determine_plan_status(
        self, text: str, resource_changes: list[ResourceChange], diagnostics: list[dict[str, Any]]
    ) -> str:
        """Determine plan status based on content.

        Args:
            text: Plain text plan output
            resource_changes: Parsed resource changes
            diagnostics: Parsed diagnostics

        Returns:
            Plan status: "success", "failed", or "incomplete"
        """
        # Check for operation failed message
        if self.OPERATION_FAILED_PATTERN.search(text):
            return "failed"

        # Check for errors in diagnostics
        error_diagnostics = [d for d in diagnostics if d.get("severity") == "error"]
        if error_diagnostics:
            # If we have errors but no parseable section, plan failed before completion
            if self.START_MARKER not in text:
                return "failed"
            # If we have errors but also have resources, plan is incomplete
            if resource_changes:
                return "incomplete"
            return "failed"

        # Check for parseable section
        if self.START_MARKER in text:
            # Check for plan summary
            if self.PLAN_SUMMARY_PATTERN.search(text):
                return "success"
            # Has parseable section but no summary - might be incomplete
            if resource_changes:
                return "incomplete"
            return "success"

        # No parseable section and no errors - might be "no changes" or empty
        if "No changes" in text or "Infrastructure is up-to-date" in text:
            return "success"

        # Default to incomplete if we can't determine
        return "incomplete"

    def _is_structured_json_log(self, text: str) -> bool:
        """Detect TFC 1.12+ structured JSON log format.

        In this format every content line (after the header) is a JSON object
        with '@level', '@message', and 'type' keys.  Plain-text plan output
        always contains lines that do NOT start with '{'.
        """
        import json

        non_empty = [l for l in text.splitlines() if l.strip()]
        if not non_empty:
            return False
        json_lines = 0
        for line in non_empty:
            stripped = line.strip()
            if not stripped.startswith("{"):
                return False  # Found a non-JSON line — not structured log
            try:
                obj = json.loads(stripped)
                if "@level" in obj or "@message" in obj or "type" in obj:
                    json_lines += 1
            except (json.JSONDecodeError, ValueError):
                return False
        return json_lines > 0

    def _parse_plan_summary_from_json_log(self, text: str) -> dict[str, int] | None:
        """Extract plan summary counts from TFC structured JSON log.

        Looks for a line with type='change_summary' or a message matching
        the Plan: N to add... pattern embedded in @message fields.
        """
        import json

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("{"):
                continue
            try:
                obj = json.loads(stripped)
            except (json.JSONDecodeError, ValueError):
                continue
            # Prefer the structured change_summary type
            if obj.get("type") == "change_summary" and "changes" in obj:
                ch = obj["changes"]
                return {
                    "add": ch.get("add", 0),
                    "change": ch.get("change", 0),
                    "destroy": ch.get("remove", 0),
                    "import": ch.get("import", 0),
                }
            # Fallback: parse Plan: N to add... from @message
            msg = obj.get("@message", "")
            match = self.PLAN_SUMMARY_PATTERN.search(msg)
            if match:
                return {
                    "add": int(match.group(2) or 0),
                    "change": int(match.group(3) or 0),
                    "destroy": int(match.group(4) or 0),
                    "import": int(match.group(1) or match.group(5) or 0),
                }
        return None
