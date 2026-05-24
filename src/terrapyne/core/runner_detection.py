"""Runner detection — heuristic auto-detection of terraform vs opentofu."""

from __future__ import annotations

import os
from pathlib import Path
from shutil import which
from typing import TYPE_CHECKING

from terrapyne.core.exceptions import TerrapyneError

if TYPE_CHECKING:
    from terrapyne.core.local_binary import LocalIACRunner


class RunnerNotFoundError(TerrapyneError):
    """The detected runner binary is not installed."""


class AmbiguousRunnerError(TerrapyneError):
    """Cannot determine the correct runner from project files."""


def detect_runner(
    directory: Path | str,
    *,
    force_runner: str | None = None,
) -> str:
    """Detect whether a project uses terraform or opentofu.

    Returns "terraform" or "opentofu".
    Raises RunnerNotFoundError if the binary is missing.
    Raises AmbiguousRunnerError if detection is impossible.
    """
    directory = Path(directory)

    if force_runner:
        return "opentofu" if force_runner in ("tofu", "opentofu") else "terraform"

    # 1. Check version manager files
    if (directory / ".opentofu-version").exists():
        runner = "opentofu"
    elif (directory / ".terraform-version").exists():
        runner = "terraform"
    # 2. Check lockfile
    elif (lockfile := directory / ".terraform.lock.hcl").exists():
        content = lockfile.read_text()
        if '"tofu init"' in content:
            runner = "opentofu"
        elif '"terraform init"' in content:
            runner = "terraform"
        elif "registry.opentofu.org" in content:
            runner = "opentofu"
        elif "registry.terraform.io" in content:
            runner = "terraform"
        else:
            raise AmbiguousRunnerError(
                "Lockfile exists but cannot determine runner from its contents."
            )
    else:
        # 3. Fall back to TERRAPYNE_RUNNER env var
        env_runner = os.environ.get("TERRAPYNE_RUNNER")
        if env_runner:
            if env_runner in ("tofu", "opentofu"):
                runner = "opentofu"
            else:
                runner = "terraform"
        else:
            raise AmbiguousRunnerError(
                "No lockfile or version manager file found. "
                "Set TERRAPYNE_RUNNER or pass --force-runner."
            )

    # Verify binary exists
    binary = "tofu" if runner == "opentofu" else "terraform"
    if not which(binary):
        raise RunnerNotFoundError(
            f"Detected runner '{runner}' but '{binary}' binary not found in PATH."
        )

    return runner


def create_runner(
    directory: Path | str,
    *,
    force_runner: str | None = None,
) -> LocalIACRunner:
    """Factory: detect the runner and return the appropriate class (not instantiated with exec)."""
    from terrapyne.core.local_binary import OpenTofu, Terraform

    runner = detect_runner(directory, force_runner=force_runner)
    cls = OpenTofu if runner == "opentofu" else Terraform
    return cls(workspace_directory=str(directory))


class ResolvedRunner:
    """Lightweight result of runner resolution for CLI use."""

    __slots__ = ("binary", "runner_type", "version_constraint")

    def __init__(self, runner_type: str, version_constraint: str | None = None) -> None:
        self.runner_type = runner_type
        self.binary = "tofu" if runner_type == "opentofu" else "terraform"
        self.version_constraint = version_constraint


def resolve_runner(
    directory: Path | str,
    *,
    force_runner: str | None = None,
) -> ResolvedRunner:
    """Resolve the runner for CLI commands without instantiating the heavy class."""
    directory = Path(directory)
    runner_type = detect_runner(directory, force_runner=force_runner)

    # Read version constraint from version manager file
    version_constraint: str | None = None
    version_file = (
        directory / ".opentofu-version"
        if runner_type == "opentofu"
        else directory / ".terraform-version"
    )
    if version_file.exists():
        version_constraint = version_file.read_text().strip()

    return ResolvedRunner(runner_type, version_constraint)
