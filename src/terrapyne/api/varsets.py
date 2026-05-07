"""Variable Sets API methods."""

from __future__ import annotations

from collections.abc import Iterator

from terrapyne.api.client import TFCClient
from terrapyne.models.varset import VariableSet, VariableSetVariable


class VarSetAPI:
    """Variable Sets API operations."""

    def __init__(self, client: TFCClient):
        self.client = client

    def list(self, organization: str | None = None) -> tuple[Iterator[VariableSet], int | None]:
        """List variable sets in an organization.

        Args:
            organization: Organization name (uses client default if not specified)

        Returns:
            Tuple of (iterator of VariableSet instances, total count or None)
        """
        org = self.client.get_organization(organization)
        path = f"/organizations/{org}/varsets"
        items_iterator, total_count = self.client.paginate_with_meta(path)

        def varset_iterator() -> Iterator[VariableSet]:
            for item in items_iterator:
                yield VariableSet.from_api_response(item)

        return varset_iterator(), total_count

    def get_by_name(self, name: str, organization: str | None = None) -> VariableSet:
        """Get a variable set by name.

        Args:
            name: Variable set name
            organization: Organization name (uses client default if not specified)

        Returns:
            VariableSet instance

        Raises:
            ValueError: If variable set not found
        """
        varsets, _ = self.list(organization)
        for vs in varsets:
            if vs.name == name:
                return vs
        raise ValueError(f"Variable set '{name}' not found in organization.")

    def get_variables(self, varset_id: str) -> Iterator[VariableSetVariable]:
        """List variables in a variable set.

        Args:
            varset_id: Variable set ID

        Yields:
            VariableSetVariable instances
        """
        path = f"/varsets/{varset_id}/relationships/vars"
        items_iterator, _ = self.client.paginate_with_meta(path)
        for item in items_iterator:
            yield VariableSetVariable.from_api_response(item)

    def apply(self, varset_id: str, workspace_id: str) -> None:
        """Apply a variable set to a workspace.

        Args:
            varset_id: Variable set ID
            workspace_id: Workspace ID to apply to
        """
        path = f"/varsets/{varset_id}/relationships/workspaces"
        self.client.post(
            path,
            json_data={"data": [{"type": "workspaces", "id": workspace_id}]},
        )

    def remove(self, varset_id: str, workspace_id: str) -> None:
        """Remove a variable set from a workspace.

        Args:
            varset_id: Variable set ID
            workspace_id: Workspace ID to remove from
        """
        path = f"/varsets/{varset_id}/relationships/workspaces"
        self.client.delete(
            path,
            json_data={"data": [{"type": "workspaces", "id": workspace_id}]},
        )
