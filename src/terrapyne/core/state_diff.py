"""State resource extraction and diffing."""

from __future__ import annotations

import difflib
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StateResourceInstance:
    """A single instance of a resource in terraform state."""

    resource_type: str
    resource_name: str
    module: str | None
    index_key: int | str | None
    attributes: dict[str, Any]

    @property
    def address(self) -> str:
        base = f"{self.resource_type}.{self.resource_name}"
        if self.module:
            base = f"{self.module}.{base}"
        if self.index_key is not None:
            base = f"{base}[{self.index_key}]"
        return base

    def get_field(self, dotted_path: str) -> Any:
        """Get a value from attributes using a dotted path like 'tags.Name'."""
        obj: Any = self.attributes
        for key in dotted_path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return None
            if obj is None:
                return None
        return obj


def parse_state_resources(
    state_json: dict[str, Any],
    types: set[str] | None = None,
    mode: str = "managed",
    module_pattern: str | None = None,
) -> list[StateResourceInstance]:
    """Extract resource instances from a terraform state JSON.

    Args:
        state_json: Parsed terraform state (from state version download)
        types: Filter to these resource types (None = all)
        mode: Filter by mode ('managed', 'data', or None for all)
        module_pattern: Filter to resources in modules matching this substring

    Returns:
        List of StateResourceInstance
    """
    instances = []
    for resource in state_json.get("resources", []):
        if mode and resource.get("mode") != mode:
            continue
        rtype = resource.get("type", "")
        if types and rtype not in types:
            continue
        rmodule = resource.get("module")
        if module_pattern and (not rmodule or module_pattern not in rmodule):
            continue

        rname = resource.get("name", "")
        for inst in resource.get("instances", []):
            instances.append(
                StateResourceInstance(
                    resource_type=rtype,
                    resource_name=rname,
                    module=rmodule,
                    index_key=inst.get("index_key"),
                    attributes=inst.get("attributes", {}),
                )
            )
    return instances


DEFAULT_FIELDS = ["type", "name", "id", "arn", "region"]

# Fallback key search per logical field (like orc.py but configurable)
FIELD_ALIASES: dict[str, list[str]] = {
    "type": [],  # special — uses resource_type
    "name": ["tags.Name", "name", "identifier", "id"],
    "id": ["id", "arn"],
    "arn": ["arn", "certificate_arn"],
    "region": ["region", "availability_zone"],
    "endpoint": ["private_ip", "endpoint", "arn", "uri"],
}


def resolve_field(instance: StateResourceInstance, field_name: str) -> str:
    """Resolve a field name to a value, using aliases for well-known fields."""
    if field_name == "type":
        return instance.resource_type
    if field_name == "address":
        return instance.address
    if field_name == "module":
        return instance.module or "(root)"

    # Try direct dotted path first
    val = instance.get_field(field_name)
    if val is not None:
        return str(val)

    # Try aliases for well-known field names
    for alias in FIELD_ALIASES.get(field_name, []):
        val = instance.get_field(alias)
        if val is not None:
            return str(val)

    return ""


def extract_rows(
    instances: list[StateResourceInstance],
    fields: list[str],
) -> list[dict[str, str]]:
    """Extract field values from instances into row dicts."""
    return [{f: resolve_field(inst, f) for f in fields} for inst in instances]


@dataclass
class StateDiff:
    """Result of diffing two state snapshots."""

    added: list[StateResourceInstance] = field(default_factory=list)
    removed: list[StateResourceInstance] = field(default_factory=list)


def diff_state_resources(
    old_instances: list[StateResourceInstance],
    new_instances: list[StateResourceInstance],
) -> StateDiff:
    """Compute resource delta between two state snapshots.

    Uses resource address as the identity key.
    """
    old_by_addr = {i.address: i for i in old_instances}
    new_by_addr = {i.address: i for i in new_instances}

    old_addrs = set(old_by_addr.keys())
    new_addrs = set(new_by_addr.keys())

    return StateDiff(
        added=sorted(
            [new_by_addr[a] for a in new_addrs - old_addrs],
            key=lambda i: i.address,
        ),
        removed=sorted(
            [old_by_addr[a] for a in old_addrs - new_addrs],
            key=lambda i: i.address,
        ),
    )


def format_diff_unified(
    old_instances: list[StateResourceInstance],
    new_instances: list[StateResourceInstance],
    fields: list[str],
    diff_cmd: str | None = None,
) -> str:
    """Produce a unified diff of two state snapshots.

    If diff_cmd is provided, writes temp files and shells out to that program.
    Otherwise uses difflib with ANSI colouring when stdout is a TTY.
    """
    old_rows = extract_rows(old_instances, fields)
    new_rows = extract_rows(new_instances, fields)

    old_text = json.dumps(old_rows, indent=2, sort_keys=True).splitlines(keepends=True)
    new_text = json.dumps(new_rows, indent=2, sort_keys=True).splitlines(keepends=True)

    if diff_cmd:
        return _external_diff(old_text, new_text, diff_cmd)

    diff_lines = list(
        difflib.unified_diff(old_text, new_text, fromfile="old-state", tofile="new-state")
    )

    if not diff_lines:
        return "No differences.\n"

    if sys.stdout.isatty():
        return _colorize_diff(diff_lines)

    return "".join(diff_lines)


_ANSI_RED = "\033[31m"
_ANSI_GREEN = "\033[32m"
_ANSI_CYAN = "\033[36m"
_ANSI_RESET = "\033[0m"


def _colorize_diff(lines: list[str]) -> str:
    out = []
    for line in lines:
        if line.startswith("+++") or line.startswith("---"):
            out.append(f"{_ANSI_CYAN}{line}{_ANSI_RESET}")
        elif line.startswith("+"):
            out.append(f"{_ANSI_GREEN}{line}{_ANSI_RESET}")
        elif line.startswith("-"):
            out.append(f"{_ANSI_RED}{line}{_ANSI_RESET}")
        else:
            out.append(line)
    return "".join(out)


def _external_diff(old_lines: list[str], new_lines: list[str], diff_cmd: str) -> str:
    """Write to temp files and run an external diff program."""
    import tempfile

    with (
        tempfile.NamedTemporaryFile(mode="w", suffix="-old-state.json", delete=False) as old_f,
        tempfile.NamedTemporaryFile(mode="w", suffix="-new-state.json", delete=False) as new_f,
    ):
        old_f.writelines(old_lines)
        new_f.writelines(new_lines)
        old_path, new_path = old_f.name, new_f.name

    try:
        # Support "git diff --no-index --color" style multi-word commands
        cmd_parts = [*shlex.split(diff_cmd), old_path, new_path]
        result = subprocess.run(cmd_parts, capture_output=True, text=True)
        # diff tools return exit code 1 when files differ — that's normal
        return result.stdout or result.stderr or "No differences.\n"
    finally:
        os.unlink(old_path)
        os.unlink(new_path)
