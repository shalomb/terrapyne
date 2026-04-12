"""TFC Runs API."""

import builtins
import time
from collections.abc import Callable
from typing import Any

from terrapyne.models.apply import Apply
from terrapyne.models.plan import Plan
from terrapyne.models.run import Run


class RunsAPI:
    """API for TFC runs."""

    def __init__(self, client):
        """Initialize Runs API."""
        self.client = client

    def list(
        self,
        workspace_id: str,
        limit: int = 20,
        status: str | None = None,
    ) -> tuple[builtins.list[Run], int]:
        """List runs for a workspace.

        Args:
            workspace_id: Workspace ID
            limit: Maximum number of runs to return
            status: Filter by status

        Returns:
            Tuple of (list of Run instances, total count)
        """
        params: dict[str, Any] = {
            "page[size]": min(limit, 100),
            "include": "configuration-version,plan",
        }
        if status:
            params["filter[status]"] = status

        path = f"/workspaces/{workspace_id}/runs"
        response = self.client.get(path, params=params)

        runs = []
        data = response.get("data", [])
        included = response.get("included", [])
        total_count = response.get("meta", {}).get("pagination", {}).get("total-count", 0)

        # Use an iterator if we need to fetch more pages (not implemented here for simplicity)
        items_iterator = data

        for item in items_iterator:
            runs.append(Run.from_api_response(item, included=included))
            if len(runs) >= limit:
                break

        return runs, total_count

    def get_latest_cost_estimate(self, workspace_id: str) -> dict[str, Any] | None:
        """Get the latest finished cost estimate for a workspace.

        Walks recent runs until one with a finished cost estimate is found.
        """
        response = self.client.get(
            f"/workspaces/{workspace_id}/runs",
            {"include": "cost_estimate", "page[size]": 10},
        )

        runs = response.get("data", [])
        if not runs:
            return None

        cost_by_id = {
            inc["id"]: inc["attributes"]
            for inc in response.get("included", [])
            if inc.get("type") == "cost-estimates"
        }

        for run in runs:
            ce_rel = run.get("relationships", {}).get("cost-estimate", {}).get("data")
            if not ce_rel:
                continue
            ce = cost_by_id.get(ce_rel["id"], {})
            if ce.get("status") == "finished" and ce.get("proposed-monthly-cost"):
                return ce

        return None

    def get(self, run_id: str, include: str | None = None) -> Run:
        """Get run by ID.

        Args:
            run_id: Run ID
            include: Resources to include (e.g. 'configuration-version')

        Returns:
            Run instance
        """
        params = {}
        if include:
            params["include"] = include

        path = f"/runs/{run_id}"
        response = self.client.get(path, params=params)
        return Run.from_api_response(response["data"], included=response.get("included"))

    def create(
        self,
        workspace_id: str,
        message: str | None = None,
        auto_apply: bool = False,
        is_destroy: bool = False,
        target_addrs: builtins.list[str] | None = None,
        replace_addrs: builtins.list[str] | None = None,
        refresh_only: bool = False,
        debug: bool = False,
    ) -> Run:
        """Create a new run (plan).

        Args:
            workspace_id: Workspace ID
            message: Run message/description
            auto_apply: Auto-apply after plan succeeds
            is_destroy: Create destroy run
            target_addrs: List of resource addresses to target
            replace_addrs: List of resource addresses to replace (force recreation)
            refresh_only: Create refresh-only run
            debug: Enable verbose/debug logging in TFC (debugging-mode)

        Returns:
            Created Run instance

        Raises:
            httpx.HTTPStatusError: If creation fails
        """
        path = "/runs"
        payload: dict[str, Any] = {
            "data": {
                "attributes": {
                    "auto-apply": auto_apply,
                    "is-destroy": is_destroy,
                    "refresh-only": refresh_only,
                },
                "relationships": {
                    "workspace": {"data": {"type": "workspaces", "id": workspace_id}}
                },
            }
        }

        if message:
            payload["data"]["attributes"]["message"] = message

        if target_addrs:
            payload["data"]["attributes"]["target-addrs"] = target_addrs

        if replace_addrs:
            payload["data"]["attributes"]["replace-addrs"] = replace_addrs

        if debug:
            payload["data"]["attributes"]["debugging-mode"] = True

        response = self.client.post(path, json_data=payload)
        return Run.from_api_response(response["data"])

    def apply(self, run_id: str, comment: str | None = None) -> Run:
        """Apply a run.

        Args:
            run_id: Run ID
            comment: Apply comment

        Returns:
            Updated Run instance
        """
        path = f"/runs/{run_id}/actions/apply"
        payload = {"comment": comment} if comment else None

        self.client.post(path, json_data=payload)
        # TFC returns 202 Accepted, sometimes with data, sometimes not
        # If we want the updated run, we usually need to fetch it
        return self.get(run_id)

    def discard(self, run_id: str, comment: str | None = None) -> Run:
        """Discard a run.

        Args:
            run_id: Run ID
            comment: Discard comment

        Returns:
            Updated Run instance
        """
        path = f"/runs/{run_id}/actions/discard"
        payload = {"comment": comment} if comment else None

        self.client.post(path, json_data=payload)
        return self.get(run_id)

    def cancel(self, run_id: str, comment: str | None = None) -> Run:
        """Cancel a run.

        Args:
            run_id: Run ID
            comment: Cancel comment

        Returns:
            Updated Run instance
        """
        path = f"/runs/{run_id}/actions/cancel"
        payload = {"comment": comment} if comment else None

        self.client.post(path, json_data=payload)
        return self.get(run_id)

    def get_plan(self, plan_id: str) -> Plan:
        """Get plan details.

        Args:
            plan_id: Plan ID

        Returns:
            Plan instance

        Raises:
            httpx.HTTPStatusError: If plan not found
        """
        path = f"/plans/{plan_id}"
        response = self.client.get(path)
        return Plan.from_api_response(response["data"])

    def get_plan_logs(self, plan_id: str) -> str:
        """Get plan logs.

        Args:
            plan_id: Plan ID

        Returns:
            Plan log content as string

        Raises:
            httpx.HTTPStatusError: If logs not available
        """
        path = f"/plans/{plan_id}/logs"
        response = self.client.client.get(f"{self.client.base_url}{path}")
        response.raise_for_status()
        return response.text

    def get_apply_logs(self, apply_id: str) -> str:
        """Get apply logs.

        Args:
            apply_id: Apply ID

        Returns:
            Apply log content as string

        Raises:
            httpx.HTTPStatusError: If logs not available
        """
        path = f"/applies/{apply_id}/logs"
        response = self.client.client.get(f"{self.client.base_url}{path}")
        response.raise_for_status()
        return response.text

    def get_apply(self, apply_id: str) -> Apply:
        """Get apply details.

        Args:
            apply_id: Apply ID

        Returns:
            Apply instance

        Raises:
            httpx.HTTPStatusError: If apply not found
        """
        path = f"/applies/{apply_id}"

        response = self.client.get(path)

        return Apply.from_api_response(response["data"])

    def fetch_log_lines(self, url: str) -> builtins.list[str]:
        """Fetch log lines from a read URL.

        Note: TFC log URLs often point to S3.
        This returns all lines as a list of strings.
        A future version will support real-time streaming via httpx.stream().
        """
        response = self.client.client.get(url)
        response.raise_for_status()
        return response.text.splitlines()

    def poll_until_complete(
        self,
        run_id: str,
        callback: Callable[[Run], None] | None = None,
        max_wait: float = 1800.0,  # 30 minutes
    ) -> Run:
        """Poll run status until it reaches a terminal state.

        Args:
            run_id: Run ID to poll
            callback: Optional callback function called on each poll (receives Run)
            max_wait: Maximum time to wait in seconds

        Returns:
            Final Run instance in terminal state

        Raises:
            TimeoutError: If max_wait exceeded
            httpx.HTTPStatusError: If API errors occur
        """
        # Exponential backoff intervals (seconds)
        intervals = [2, 2, 3, 5, 5, 10, 10, 15, 30]
        interval_index = 0

        start_time = time.time()

        while True:
            run = self.get(run_id)

            if callback:
                callback(run)

            if run.status.is_terminal:
                return run

            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                raise TimeoutError(
                    f"Run {run_id} did not complete within {max_wait}s "
                    f"(current status: {run.status.value})"
                )

            # Wait before next poll
            wait_time = intervals[interval_index]
            if interval_index < len(intervals) - 1:
                interval_index += 1

            time.sleep(wait_time)
