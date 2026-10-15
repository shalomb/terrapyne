"""terrapyne.local — local IaC binary wrappers.

Use this sub-namespace for operations against locally installed terraform/tofu CLIs:

    from terrapyne.local import Terraform, OpenTofu, detect_runner

    tf = Terraform(workspace_directory="/path/to/workspace")
    tofu = OpenTofu(workspace_directory="/path/to/workspace")
"""

from terrapyne.core.local_binary import LocalIACRunner, OpenTofu, Terraform
from terrapyne.core.runner_detection import (
    AmbiguousRunnerError,
    RunnerNotFoundError,
    create_runner,
    detect_runner,
)

__all__ = [
    "AmbiguousRunnerError",
    "LocalIACRunner",
    "OpenTofu",
    "RunnerNotFoundError",
    "Terraform",
    "create_runner",
    "detect_runner",
]
