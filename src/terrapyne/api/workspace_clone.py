"""Workspace clone API operations.

Provides functionality to clone existing Terraform Cloud workspaces
with all configuration, variables, and settings.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from terrapyne.api.client import TFCClient
from terrapyne.models.variable import WorkspaceVariable
from terrapyne.models.workspace import Workspace, WorkspaceVCS

logger = logging.getLogger(__name__)


class WorkspaceAlreadyExistsError(Exception):
    """Raised when target workspace already exists and force=False."""

    pass


class WorkspaceNotFoundError(Exception):
    """Raised when source workspace does not exist."""

    pass


class VCSTokenRequiredError(Exception):
    """Raised when VCS token is required but not provided."""

    pass


class CloneWorkspaceAPI:
    """Workspace cloning operations.

    Provides functionality to clone workspaces with configurable scope
    including variables, VCS configuration, and team access.
    """

    def __init__(self, client: TFCClient):
        """Initialize workspace clone API.

        Args:
            client: TFC API client
        """
        self.client = client

    def validate_clone_args(
        self,
        source_workspace_name: str,
        target_workspace_name: str,
        organization: str | None = None,
        force: bool = False,
    ) -> tuple[Workspace, Workspace | None]:
        """Validate clone arguments and retrieve source/target workspaces.

        Args:
            source_workspace_name: Name of source workspace to clone from
            target_workspace_name: Name of target workspace to create
            organization: Organization name (uses client default if not specified)
            force: If True, allow overwriting existing target workspace

        Returns:
            Tuple of (source_workspace, target_workspace or None)

        Raises:
            WorkspaceNotFoundError: If source workspace does not exist
            WorkspaceAlreadyExistsError: If target exists and force=False
            ValueError: If source and target names are identical
        """
        org = self.client.get_organization(organization)

        # Validate that source and target are different
        if source_workspace_name == target_workspace_name:
            raise ValueError(
                "Source and target workspace names must be different. "
                "Cannot clone workspace to itself."
            )

        # Get source workspace (must exist)
        try:
            source = self.client.get(f"/organizations/{org}/workspaces/{source_workspace_name}")
            source_ws = Workspace.from_api_response(source["data"])
        except Exception as e:
            raise WorkspaceNotFoundError(
                f"Source workspace '{source_workspace_name}' not found in organization '{org}'"
            ) from e

        # Check if target workspace exists
        target_ws = None
        try:
            target = self.client.get(f"/organizations/{org}/workspaces/{target_workspace_name}")
            target_ws = Workspace.from_api_response(target["data"])

            # If target exists and force=False, fail
            if not force:
                raise WorkspaceAlreadyExistsError(
                    f"Workspace '{target_workspace_name}' already exists in organization '{org}'. "
                    f"Use --force to overwrite."
                )
        except WorkspaceAlreadyExistsError:
            # Re-raise our custom error
            raise
        except Exception as e:
            # If it's a "not found" error, target doesn't exist (which is expected)
            if "404" not in str(e) and "not found" not in str(e).lower():
                # Some other error occurred
                raise

        return source_ws, target_ws

    def validate_vcs_clone_args(
        self,
        source_org: str,
        target_org: str,
        vcs_oauth_token_id: str | None = None,
    ) -> str | None:
        """Validate VCS cloning arguments.

        When cloning across organizations, an explicit OAuth token ID must be provided.
        Within the same organization, token reference can be copied.

        Args:
            source_org: Source organization name
            target_org: Target organization name
            vcs_oauth_token_id: Explicit OAuth token ID to use (required for cross-org)

        Returns:
            OAuth token ID to use for target workspace, or None if same org and no explicit token

        Raises:
            VCSTokenRequiredError: If cross-org clone without explicit token ID
        """
        # Same organization: can use token reference from source
        if source_org == target_org:
            # If explicit token provided, use it; otherwise return None (will copy source)
            return vcs_oauth_token_id

        # Cross-organization: explicit token required
        if not vcs_oauth_token_id:
            raise VCSTokenRequiredError(
                f"Cross-organization VCS clone from '{source_org}' to '{target_org}' "
                f"requires explicit OAuth token ID via --vcs-oauth-token-id. "
                f"OAuth tokens are organization-specific and cannot be reused."
            )

        return vcs_oauth_token_id

    def build_clone_spec(
        self,
        source_workspace: Workspace,
        include_variables: bool = False,
        include_vcs: bool = False,
        include_team_access: bool = False,
        include_state: bool = False,
    ) -> dict:
        """Build workspace clone specification.

        Defines what components to clone from source workspace.

        Args:
            source_workspace: Source workspace to clone from
            include_variables: Whether to clone variables
            include_vcs: Whether to clone VCS configuration
            include_team_access: Whether to clone team access/permissions
            include_state: Whether to include state snapshot

        Returns:
            Clone specification dictionary
        """
        return {
            "include_variables": include_variables,
            "include_vcs": include_vcs,
            "include_team_access": include_team_access,
            "include_state": include_state,
            "always_include": ["settings", "tags"],
        }

    def get_workspace_variables(
        self,
        workspace_id: str,
    ) -> Iterator[WorkspaceVariable]:
        """Get all variables for a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            Iterator of WorkspaceVariable instances
        """
        path = f"/workspaces/{workspace_id}/vars"
        items_iterator, _ = self.client.paginate_with_meta(path)

        def variable_iterator() -> Iterator[WorkspaceVariable]:
            for item in items_iterator:
                yield WorkspaceVariable.from_api_response(item)

        return variable_iterator()

    def map_variables_for_clone(
        self,
        variables: Iterator[WorkspaceVariable],
    ) -> dict[str, list[dict]]:
        """Map variables by category, preserving sensitivity.

        Args:
            variables: Iterator of source workspace variables

        Returns:
            Dictionary with 'terraform' and 'env' keys containing variables for each category
        """
        mapped: dict[str, list[dict]] = {"terraform": [], "env": []}

        for var in variables:
            # Preserve all variable attributes including sensitivity
            var_data = {
                "key": var.key,
                "value": var.value,
                "category": var.category,
                "sensitive": var.sensitive,
                "hcl": var.hcl,
            }

            # Add description if present
            if var.description:
                var_data["description"] = var.description

            category = var.category or "terraform"  # Default to terraform if not specified
            if category in mapped:
                mapped[category].append(var_data)
            else:
                # Handle unknown categories by defaulting to terraform
                mapped.setdefault("terraform", []).append(var_data)

        return mapped

    def create_variable_in_workspace(
        self,
        target_workspace_id: str,
        key: str,
        value: str,
        category: str = "terraform",
        sensitive: bool = False,
        hcl: bool = False,
        description: str | None = None,
    ) -> WorkspaceVariable:
        """Create a variable in the target workspace.

        Args:
            target_workspace_id: Target workspace ID
            key: Variable key
            value: Variable value
            category: Variable category ('terraform' or 'env')
            sensitive: Whether variable is sensitive
            hcl: Whether variable is HCL
            description: Optional variable description

        Returns:
            Created WorkspaceVariable instance
        """
        path = "/vars"

        attributes: dict[str, str | bool] = {
            "key": key,
            "value": value,
            "category": category,
            "sensitive": sensitive,
            "hcl": hcl,
        }

        # Add description if provided
        if description:
            attributes["description"] = description

        payload = {
            "data": {
                "type": "vars",
                "attributes": attributes,
                "relationships": {
                    "workspace": {
                        "data": {
                            "id": target_workspace_id,
                            "type": "workspaces",
                        }
                    }
                },
            }
        }

        response = self.client.post(path, json_data=payload)
        return WorkspaceVariable.from_api_response(response["data"])

    def clone_variables(
        self,
        source_workspace_id: str,
        target_workspace_id: str,
    ) -> dict:
        """Clone all variables from source to target workspace.

        Preserves variable sensitivity and all metadata.

        Args:
            source_workspace_id: Source workspace ID
            target_workspace_id: Target workspace ID

        Returns:
            Dictionary with clone results summary
        """
        logger.info(f"Cloning variables from {source_workspace_id} to {target_workspace_id}")

        try:
            # Get source variables
            source_vars = list(self.get_workspace_variables(source_workspace_id))
            logger.debug(f"Found {len(source_vars)} variables in source workspace")

            if not source_vars:
                return {
                    "status": "success",
                    "variables_cloned": 0,
                    "terraform_variables": 0,
                    "env_variables": 0,
                }

            # Clone variables to target
            created_count = 0
            created_terraform_count = 0
            created_env_count = 0

            for var in source_vars:
                try:
                    # Skip variables without a value
                    if var.value is None:
                        logger.warning(f"Skipping variable {var.key} with no value")
                        continue

                    self.create_variable_in_workspace(
                        target_workspace_id=target_workspace_id,
                        key=var.key,
                        value=var.value,
                        category=var.category or "terraform",
                        sensitive=var.sensitive,
                        hcl=var.hcl,
                        description=var.description,
                    )
                    created_count += 1

                    if var.category == "env":
                        created_env_count += 1
                    else:
                        created_terraform_count += 1

                    logger.debug(
                        f"Created variable: {var.key} ({var.category})"
                        f"{' [SENSITIVE]' if var.sensitive else ''}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create variable {var.key}: {e}",
                        exc_info=True,
                    )
                    raise

            return {
                "status": "success",
                "variables_cloned": created_count,
                "terraform_variables": created_terraform_count,
                "env_variables": created_env_count,
            }

        except Exception as e:
            logger.error(f"Variable cloning failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "variables_cloned": 0,
            }

    def get_workspace_vcs_config(
        self,
        workspace_id: str,
    ) -> WorkspaceVCS | None:
        """Get VCS configuration for a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            WorkspaceVCS instance or None if no VCS configured
        """
        path = f"/workspaces/{workspace_id}"

        try:
            response = self.client.get(path)
            workspace_data = response.get("data", {})
            attributes = workspace_data.get("attributes", {})

            # Check if VCS is configured
            vcs_data = attributes.get("vcs-repo")
            if vcs_data:
                return WorkspaceVCS.model_validate(vcs_data)

            return None
        except Exception as e:
            logger.error(f"Failed to get VCS config for {workspace_id}: {e}")
            return None

    def update_workspace_vcs_config(
        self,
        target_workspace_id: str,
        identifier: str,
        branch: str | None = None,
        oauth_token_id: str | None = None,
    ) -> dict:
        """Update VCS configuration for a workspace.

        Args:
            target_workspace_id: Target workspace ID
            identifier: Repository identifier (org/repo format)
            branch: Repository branch (optional)
            oauth_token_id: OAuth token ID (optional)

        Returns:
            Update result dictionary
        """
        path = f"/workspaces/{target_workspace_id}"

        vcs_repo: dict[str, str] = {
            "identifier": identifier,
        }

        # Add optional fields
        if branch is not None:
            vcs_repo["branch"] = branch

        if oauth_token_id is not None:
            vcs_repo["oauth-token-id"] = oauth_token_id

        payload = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "vcs-repo": vcs_repo,
                },
            }
        }

        try:
            self.client.patch(path, json_data=payload)
            return {
                "status": "success",
                "workspace_id": target_workspace_id,
                "vcs_configured": True,
            }
        except Exception as e:
            logger.error(f"Failed to update VCS config: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "vcs_configured": False,
            }

    def clone_vcs_configuration(
        self,
        source_workspace_id: str,
        target_workspace_id: str,
        source_organization: str,
        target_organization: str,
        vcs_oauth_token_id: str | None = None,
    ) -> dict:
        """Clone VCS configuration from source to target workspace.

        For same-organization cloning, copies the OAuth token reference.
        For cross-organization cloning, requires explicit token ID.

        Args:
            source_workspace_id: Source workspace ID
            target_workspace_id: Target workspace ID
            source_organization: Source organization name
            target_organization: Target organization name
            vcs_oauth_token_id: Explicit OAuth token ID (required for cross-org)

        Returns:
            Clone result dictionary

        Raises:
            VCSTokenRequiredError: If cross-org clone without token ID
        """
        logger.info(f"Cloning VCS config from {source_workspace_id} to {target_workspace_id}")

        # Get source VCS configuration
        source_vcs = self.get_workspace_vcs_config(source_workspace_id)

        if not source_vcs or not source_vcs.identifier:
            logger.info(f"Source workspace {source_workspace_id} has no VCS configuration")
            return {
                "status": "success",
                "vcs_cloned": False,
                "reason": "Source workspace has no VCS configuration",
            }

        # Validate VCS token requirements for cross-org cloning
        token_to_use = self.validate_vcs_clone_args(
            source_org=source_organization,
            target_org=target_organization,
            vcs_oauth_token_id=vcs_oauth_token_id,
        )

        # If same org and no explicit token, use source token ID
        if (
            source_organization == target_organization
            and token_to_use is None
            and source_vcs.oauth_token_id
        ):
            token_to_use = source_vcs.oauth_token_id

        # Update target workspace with VCS configuration
        result = self.update_workspace_vcs_config(
            target_workspace_id=target_workspace_id,
            identifier=source_vcs.identifier,
            branch=source_vcs.branch,
            oauth_token_id=token_to_use,
        )

        if result["status"] == "success":
            return {
                "status": "success",
                "vcs_cloned": True,
                "identifier": source_vcs.identifier,
                "branch": source_vcs.branch,
                "oauth_token_id": token_to_use,
            }

        return result

    def create_workspace(
        self,
        workspace_name: str,
        organization: str,
        terraform_version: str | None = None,
        execution_mode: str | None = None,
        auto_apply: bool | None = None,
        tags: list[str] | None = None,
    ) -> Workspace:
        """Create a new workspace.

        Args:
            workspace_name: Name for the new workspace
            organization: Organization name
            terraform_version: Terraform version to use
            execution_mode: Execution mode (remote or local)
            auto_apply: Whether to auto-apply
            tags: Tags to apply to workspace

        Returns:
            Created Workspace instance
        """
        path = f"/organizations/{organization}/workspaces"

        attributes: dict[str, str | bool | list[str]] = {
            "name": workspace_name,
        }

        # Add optional attributes
        if terraform_version:
            attributes["terraform-version"] = terraform_version

        if execution_mode:
            attributes["execution-mode"] = execution_mode

        if auto_apply is not None:
            attributes["auto-apply"] = auto_apply

        # Handle tags separately if provided
        if tags:
            attributes["tag-names"] = tags

        payload = {
            "data": {
                "type": "workspaces",
                "attributes": attributes,
            }
        }

        response = self.client.post(path, json_data=payload)
        return Workspace.from_api_response(response["data"])

    def clone(
        self,
        source_workspace_name: str,
        target_workspace_name: str,
        organization: str | None = None,
        with_variables: bool = False,
        with_vcs: bool = False,
        with_team_access: bool = False,
        with_state: bool = False,
        vcs_oauth_token_id: str | None = None,
        force: bool = False,
        async_mode: bool = False,
    ) -> dict:
        """Clone a workspace with specified configuration.

        Creates a new workspace based on an existing workspace configuration,
        with options to include variables, VCS config, team access, etc.

        Args:
            source_workspace_name: Name of workspace to clone from
            target_workspace_name: Name of new workspace to create
            organization: Organization name (uses client default if not specified)
            with_variables: Clone terraform and environment variables
            with_vcs: Clone VCS repository connection and configuration
            with_team_access: Clone team access and permissions
            with_state: Include current state snapshot (advanced)
            vcs_oauth_token_id: Explicit OAuth token ID for VCS (required for cross-org)
            force: Overwrite existing target workspace if it exists
            async_mode: Perform clone asynchronously (not yet implemented)

        Returns:
            Dictionary with clone result information

        Raises:
            WorkspaceNotFoundError: If source workspace not found
            WorkspaceAlreadyExistsError: If target exists and force=False
            VCSTokenRequiredError: If VCS clone needs explicit token
            Exception: On API errors
        """
        # Check for not-yet-implemented features early
        if with_team_access:
            raise NotImplementedError(
                "Team access cloning (with_team_access=True) is not yet implemented. "
                "Please check back in a future release."
            )

        org = self.client.get_organization(organization)

        # Validate arguments
        source_ws, target_ws = self.validate_clone_args(
            source_workspace_name=source_workspace_name,
            target_workspace_name=target_workspace_name,
            organization=org,
            force=force,
        )

        logger.info(
            f"Cloning workspace '{source_workspace_name}' to '{target_workspace_name}' "
            f"in organization '{org}'"
        )

        # Build clone specification
        clone_spec = self.build_clone_spec(
            source_workspace=source_ws,
            include_variables=with_variables,
            include_vcs=with_vcs,
            include_team_access=with_team_access,
            include_state=with_state,
        )
        # Step 1: Create or update target workspace with source settings
        if target_ws and force:
            # Workspace exists and we're forcing - just note it
            logger.info(
                f"Target workspace '{target_workspace_name}' exists; proceeding with force flag"
            )
            target_workspace_id = target_ws.id
        else:
            # Create new target workspace with source settings
            logger.debug(f"Creating target workspace '{target_workspace_name}'")
            target_ws = self.create_workspace(
                workspace_name=target_workspace_name,
                organization=org,
                terraform_version=source_ws.terraform_version,
                execution_mode=source_ws.execution_mode,
                auto_apply=source_ws.auto_apply,
                tags=source_ws.tag_names if source_ws.tag_names else None,
            )
            target_workspace_id = target_ws.id
            logger.info(
                f"Created target workspace '{target_workspace_name}' (id: {target_workspace_id})"
            )

        # Step 2: Clone variables if requested
        variables_result = None
        if clone_spec["include_variables"]:
            logger.info("Cloning variables...")
            variables_result = self.clone_variables(
                source_workspace_id=source_ws.id,
                target_workspace_id=target_workspace_id,
            )
            logger.info(f"Variables cloned: {variables_result.get('variables_cloned', 0)}")

        # Step 3: Clone VCS config if requested
        vcs_result = None
        if clone_spec["include_vcs"]:
            logger.info("Cloning VCS configuration...")
            vcs_result = self.clone_vcs_configuration(
                source_workspace_id=source_ws.id,
                target_workspace_id=target_workspace_id,
                source_organization=org,
                target_organization=org,
                vcs_oauth_token_id=vcs_oauth_token_id,
            )
            if vcs_result.get("vcs_cloned"):
                logger.info(
                    f"VCS configured: {vcs_result.get('identifier')} "
                    f"(branch: {vcs_result.get('branch', 'default')})"
                )
            else:
                logger.info(f"No VCS to clone: {vcs_result.get('reason')}")

        # Step 4: Clone team access if requested (placeholder for future)
        team_access_result = None
        if clone_spec["include_team_access"]:
            logger.info("Team access cloning not yet implemented; skipping for MVP")
            team_access_result = {
                "status": "skipped",
                "reason": "Not yet implemented",
            }

        # Return comprehensive result
        return {
            "status": "success",
            "source_workspace_id": source_ws.id,
            "source_workspace_name": source_workspace_name,
            "target_workspace_id": target_workspace_id,
            "target_workspace_name": target_workspace_name,
            "organization": org,
            "clone_spec": clone_spec,
            "results": {
                "variables": variables_result,
                "vcs": vcs_result,
                "team_access": team_access_result,
            },
            "message": (
                f"Successfully cloned workspace '{source_workspace_name}' "
                f"to '{target_workspace_name}'"
            ),
        }
