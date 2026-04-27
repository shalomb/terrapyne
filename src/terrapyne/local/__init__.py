"""terrapyne.local — local Terraform binary wrapper.

Use this sub-namespace for operations against a locally installed terraform CLI:

    from terrapyne.local import Terraform

    tf = Terraform(workspace_directory="/path/to/workspace")
"""

from terrapyne.core.local_binary import Terraform

__all__ = ["Terraform"]
