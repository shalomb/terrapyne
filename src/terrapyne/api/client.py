"""Terraform Cloud API client."""

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from terrapyne.core.credentials import TerraformCredentials

if TYPE_CHECKING:
    from terrapyne.api.projects import ProjectAPI
    from terrapyne.api.runs import RunsAPI
    from terrapyne.api.teams import TeamsAPI
    from terrapyne.api.workspaces import WorkspaceAPI


class TFCClient:
    """Terraform Cloud API client with retry logic and pagination support."""

    def __init__(
        self,
        host: str = "app.terraform.io",
        organization: str | None = None,
        credentials: TerraformCredentials | None = None,
    ):
        """Initialize TFC client.

        Args:
            host: TFC hostname (default: app.terraform.io)
            organization: TFC organization name
            credentials: Optional pre-loaded credentials (otherwise loaded from tfrc.json)
        """
        self.host = host
        self.organization = organization
        self.creds = credentials or TerraformCredentials.load(host=host)
        self.base_url = f"https://{host}/api/v2"
        self.client = httpx.Client(
            headers=self.creds.get_headers(),
            timeout=30.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "TFCClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    @property
    def workspaces(self) -> "WorkspaceAPI":
        """Get workspace API instance."""
        from terrapyne.api.workspaces import WorkspaceAPI

        return WorkspaceAPI(self)

    @property
    def runs(self) -> "RunsAPI":
        """Get runs API instance."""
        from terrapyne.api.runs import RunsAPI

        return RunsAPI(self)

    @property
    def projects(self) -> "ProjectAPI":
        """Get project API instance."""
        from terrapyne.api.projects import ProjectAPI

        return ProjectAPI(self)

    @property
    def teams(self) -> "TeamsAPI":
        """Get teams API instance."""
        from terrapyne.api.teams import TeamsAPI

        return TeamsAPI(self)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET request with retry logic.

        Args:
            path: API path (e.g., "/organizations/my-org/workspaces")
            params: Query parameters

        Returns:
            JSON response dict

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retries
        """
        url = f"{self.base_url}{path}"
        response = self.client.get(url, params=params or {})
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def post(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST request with retry logic.

        Args:
            path: API path
            json_data: JSON payload

        Returns:
            JSON response dict

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retries
        """
        url = f"{self.base_url}{path}"
        response = self.client.post(url, json=json_data or {})
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def patch(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """PATCH request with retry logic.

        Args:
            path: API path
            json_data: JSON payload

        Returns:
            JSON response dict

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retries
        """
        url = f"{self.base_url}{path}"
        response = self.client.patch(url, json=json_data or {})
        response.raise_for_status()
        return response.json()

    def paginate(
        self, path: str, params: dict[str, Any] | None = None, page_size: int = 100
    ) -> Iterator[dict[str, Any]]:
        """Paginate through API results.

        Args:
            path: API path
            params: Query parameters
            page_size: Items per page (max 100)

        Yields:
            Individual items from paginated results
        """
        params = (params or {}).copy()
        page = 1

        while True:
            params.update({"page[number]": page, "page[size]": min(page_size, 100)})
            response_data = self.get(path, params=params)

            # Yield items from current page
            data = response_data.get("data", [])
            if not data:
                break

            yield from data

            # Check if there are more pages
            links = response_data.get("links", {})
            if not links.get("next"):
                break

            page += 1

    def paginate_with_meta(
        self, path: str, params: dict[str, Any] | None = None, page_size: int = 100
    ) -> tuple[Iterator[dict[str, Any]], int | None]:
        """Paginate through API results with metadata.

        Args:
            path: API path
            params: Query parameters
            page_size: Items per page (max 100)

        Returns:
            Tuple of (iterator of items, total count from meta or None)
        """
        params = (params or {}).copy()
        params.update({"page[number]": 1, "page[size]": min(page_size, 100)})

        # Get first page to extract total count
        first_response = self.get(path, params=params)

        # Extract total count from meta
        total_count = None
        meta = first_response.get("meta", {})
        pagination = meta.get("pagination", {})
        total_count = pagination.get("total-count")

        # Generator to yield items from all pages
        def item_iterator() -> Iterator[dict[str, Any]]:
            # Yield items from first page
            data = first_response.get("data", [])
            yield from data

            # Continue with remaining pages if there are any
            links = first_response.get("links", {})
            if links.get("next"):
                page = 2
                while True:
                    params["page[number]"] = page
                    response_data = self.get(path, params=params)

                    data = response_data.get("data", [])
                    if not data:
                        break

                    yield from data

                    links = response_data.get("links", {})
                    if not links.get("next"):
                        break

                    page += 1

        return item_iterator(), total_count

    def get_organization(self, org: str | None = None) -> str:
        """Get organization name (from param, instance, or raise error).

        Args:
            org: Optional organization name

        Returns:
            Organization name

        Raises:
            ValueError: If no organization specified
        """
        organization = org or self.organization
        if not organization:
            raise ValueError(
                "Organization not specified. "
                "Pass --organization or set it in client initialization."
            )
        return organization
