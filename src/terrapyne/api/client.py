"""Terraform Cloud API client."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections.abc import Iterator
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from terrapyne.core.credentials import TerraformCredentials
from terrapyne.core.exceptions import (
    TFCAPIError,
    TFCAuthenticationError,
    TFCConflictError,
    TFCNotFoundError,
    TFCRateLimitError,
    TFCServerError,
)

if TYPE_CHECKING:
    from terrapyne.api.projects import ProjectAPI
    from terrapyne.api.runs import RunsAPI
    from terrapyne.api.state_versions import StateVersionsAPI
    from terrapyne.api.teams import TeamsAPI
    from terrapyne.api.vcs import VCSAPI
    from terrapyne.api.workspaces import WorkspaceAPI

logger = logging.getLogger("terrapyne.api")


class TFCClient:
    """Terraform Cloud API client with retry logic and pagination support."""

    def __init__(
        self,
        host: str = "app.terraform.io",
        organization: str | None = None,
        credentials: TerraformCredentials | None = None,
        debug: bool = False,
        cache_ttl: int = 0,
    ):
        """Initialize TFC client.

        Args:
            host: TFC hostname (default: app.terraform.io)
            organization: TFC organization name
            credentials: Optional pre-loaded credentials (otherwise loaded from tfrc.json)
            debug: Enable API call tracing
            cache_ttl: Cache TTL in seconds (0 to disable)
        """
        self.host = host
        self.organization = organization
        self.creds = credentials or TerraformCredentials.load(host=host)
        self.base_url = f"https://{host}/api/v2"
        self.debug = debug or os.getenv("TERRAPYNE_DEBUG") == "1"
        self.cache_ttl = cache_ttl or int(os.getenv("TERRAPYNE_CACHE_TTL", "0"))
        self.client = httpx.Client(
            headers=self.creds.get_headers(),
            timeout=30.0,
            follow_redirects=True,
        )

    def __enter__(self) -> "TFCClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    @cached_property
    def workspaces(self) -> "WorkspaceAPI":
        """Get workspace API instance."""
        from terrapyne.api.workspaces import WorkspaceAPI

        return WorkspaceAPI(self)

    @cached_property
    def runs(self) -> "RunsAPI":
        """Get runs API instance."""
        from terrapyne.api.runs import RunsAPI

        return RunsAPI(self)

    @cached_property
    def projects(self) -> "ProjectAPI":
        """Get project API instance."""
        from terrapyne.api.projects import ProjectAPI

        return ProjectAPI(self)

    @cached_property
    def teams(self) -> "TeamsAPI":
        """Get teams API instance."""
        from terrapyne.api.teams import TeamsAPI

        return TeamsAPI(self)

    @cached_property
    def state_versions(self) -> "StateVersionsAPI":
        """Get state versions API instance."""
        from terrapyne.api.state_versions import StateVersionsAPI

        return StateVersionsAPI(self)

    @cached_property
    def vcs(self) -> "VCSAPI":
        """Get VCS API instance."""
        from terrapyne.api.vcs import VCSAPI

        return VCSAPI(self)

    def _log_request(self, method: str, url: str, params: Any = None) -> float:
        if self.debug:
            logger.info(f"API Request: {method} {url}")
            if params:
                logger.info(f"  Params: {params}")
        return time.time()

    def _log_response(
        self, method: str, url: str, response: httpx.Response, start_time: float
    ) -> None:
        duration = time.time() - start_time
        if self.debug:
            logger.info(f"API Response: {method} {url} -> {response.status_code} ({duration:.3f}s)")
            if response.status_code >= 400:
                logger.info(f"  Error Body: {response.text}")

    def _handle_response_error(self, response: httpx.Response) -> None:
        """Handle HTTP response errors and raise domain-specific exceptions."""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status_code = response.status_code
            message = f"TFC API Error: {status_code} - {response.text}"

            if status_code in (401, 403):
                raise TFCAuthenticationError(
                    message, status_code=status_code, response=response
                ) from e
            if status_code == 404:
                raise TFCNotFoundError(message, status_code=status_code, response=response) from e
            if status_code == 409:
                raise TFCConflictError(message, status_code=status_code, response=response) from e
            if status_code == 429:
                raise TFCRateLimitError(message, status_code=status_code, response=response) from e
            if status_code >= 500:
                raise TFCServerError(message, status_code=status_code, response=response) from e

            raise TFCAPIError(message, status_code=status_code, response=response) from e

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Internal generic request handler with error handling."""
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        start_time = self._log_request(method, url, params or json_data)
        response = self.client.request(
            method,
            url,
            params=params or {},
            json=json_data or {} if json_data is not None else None,
        )
        self._log_response(method, url, response, start_time)
        self._handle_response_error(response)
        return response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TFCAPIError, TFCServerError)),
        reraise=True,
    )
    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET request with retry logic and optional caching.

        Args:
            path: API path (e.g., "/organizations/my-org/workspaces")
            params: Query parameters

        Returns:
            JSON response dict

        Raises:
            TFCAPIError: On TFC API errors
        """
        # Cache check
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        cache_path = None
        if self.cache_ttl > 0:
            cache_dir = Path("~/.terrapyne/cache").expanduser()
            cache_dir.mkdir(parents=True, exist_ok=True)

            key_content = f"GET:{url}:{json.dumps(params, sort_keys=True)}"
            key = hashlib.md5(key_content.encode()).hexdigest()
            cache_path = cache_dir / f"{key}.json"

            if cache_path.exists():
                mtime = cache_path.stat().st_mtime
                if (time.time() - mtime) < self.cache_ttl:
                    if self.debug:
                        logger.info(f"Cache Hit: GET {url}")
                    with open(cache_path) as f:
                        return json.load(f)

        response = self._request("GET", path, params=params)
        data = response.json()

        # Store in cache
        if cache_path:
            with open(cache_path, "w") as f:
                json.dump(data, f)

        return data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TFCAPIError, TFCServerError)),
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
            TFCAPIError: On TFC API errors
        """
        response = self._request("POST", path, json_data=json_data)
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TFCAPIError, TFCServerError)),
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
            TFCAPIError: On TFC API errors
        """
        response = self._request("PATCH", path, json_data=json_data)
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TFCAPIError, TFCServerError)),
        reraise=True,
    )
    def delete(self, path: str, json_data: dict[str, Any] | None = None) -> None:
        """DELETE request with retry logic.

        Args:
            path: API path
            json_data: Optional JSON payload

        Raises:
            TFCAPIError: On TFC API errors
        """
        self._request("DELETE", path, json_data=json_data)

    def paginate(
        self, path: str, params: dict[str, Any] | None = None, page_size: int = 100
    ) -> Iterator[dict[str, Any]]:
        """Paginate through API results.

        Args:
            path: API path
            params: Query parameters
            page_size: Items per page (max 100)

        Yields:
            Individual resource dicts
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
    ) -> tuple[Any, int | None]:
        """Paginate through API results with metadata.

        Args:
            path: API path
            params: Query parameters
            page_size: Items per page (max 100)

        Returns:
            Tuple of (iterator-like object with .included property, total count)
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
        class ResponseIterator:
            def __init__(self, first_resp: dict[str, Any], client: TFCClient, base_params: dict):
                self.first_resp = first_resp
                self.client = client
                self.params = base_params
                self.included = first_resp.get("included", [])

            def __iter__(self) -> Iterator[dict[str, Any]]:
                # Yield items from first page
                data = self.first_resp.get("data", [])
                yield from data

                # Continue with remaining pages if there are any
                links = self.first_resp.get("links", {})
                if links.get("next"):
                    page = 2
                    while True:
                        self.params["page[number]"] = page
                        response_data = self.client.get(path, params=self.params)
                        self.included = response_data.get("included", [])

                        data = response_data.get("data", [])
                        if not data:
                            break

                        yield from data

                        links = response_data.get("links", {})
                        if not links.get("next"):
                            break

                        page += 1

        return ResponseIterator(first_response, self, params), total_count

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
