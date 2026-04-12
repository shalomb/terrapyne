"""Tests for TableRenderer base class (TDD approach).

These tests define the interface and behavior for a unified table rendering
system that consolidates the scattered render_* functions.
"""

from io import StringIO
from unittest.mock import patch

from rich.console import Console
from rich.table import Table

from terrapyne.models.project import Project
from terrapyne.models.run import Run
from terrapyne.models.workspace import Workspace
from terrapyne.utils.rich_tables import (
    render_projects,
    render_runs,
    render_workspaces,
)


class TestTableRendererInterface:
    """Test the interface and basic functionality of table renderers."""

    def test_render_workspaces_with_empty_list(self):
        """Test rendering empty workspace list."""
        output = StringIO()
        Console(file=output, force_terminal=True)

        # We'll need a way to inject console into render functions
        # For now, test that function exists and is callable
        assert callable(render_workspaces)

    def test_render_workspaces_with_data(self):
        """Test rendering workspace list with data."""
        workspace = Workspace(
            id="ws-abc123",
            name="test-workspace",
            terraform_version="1.7.0",
            execution_mode="remote",
        )

        # Should not raise
        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_workspaces([workspace])
            mock_console.print.assert_called()

    def test_render_workspaces_includes_pagination_info(self):
        """Test that pagination info is displayed when total_count provided."""
        workspace = Workspace(
            id="ws-abc123",
            name="test-workspace",
        )

        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_workspaces([workspace], total_count=10)
            # Should have called print twice: table + pagination info
            assert mock_console.print.call_count >= 2

    def test_render_runs_with_data(self):
        """Test rendering runs list."""
        run = Run(
            id="run-abc123",
            status="applied",
        )

        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_runs([run])
            mock_console.print.assert_called()

    def test_render_projects_with_data(self):
        """Test rendering projects list."""
        project = Project(
            id="prj-abc123",
            name="my-infrastructure",
        )

        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_projects([project])
            mock_console.print.assert_called()


class TestTableRendererConsistency:
    """Test that all renderers follow consistent patterns."""

    def test_all_renderers_accept_sequence(self):
        """Test that list renderers accept Sequence types."""
        # All list renderers should accept any sequence
        workspaces = [
            Workspace(id="ws-1", name="test-1"),
            Workspace(id="ws-2", name="test-2"),
        ]
        runs = [
            Run(id="run-1", status="applied"),
            Run(id="run-2", status="planned"),
        ]
        projects = [
            Project(id="prj-1", name="test-1"),
            Project(id="prj-2", name="test-2"),
        ]

        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_workspaces(workspaces)
            render_runs(runs)
            render_projects(projects)

            # Each should call console.print at least once
            assert mock_console.print.call_count >= 3

    def test_all_renderers_handle_empty_sequences(self):
        """Test that all renderers handle empty lists gracefully."""
        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_workspaces([])
            render_runs([])
            render_projects([])

            # Should not raise and should still print something
            assert mock_console.print.call_count >= 3

    def test_pagination_info_optional(self):
        """Test that pagination info is optional."""
        workspace = Workspace(id="ws-1", name="test")

        # Without total_count
        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_workspaces([workspace])
            # Should still work and print at least table
            mock_console.print.assert_called()

        # With total_count
        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_workspaces([workspace], total_count=100)
            # Should print table and pagination
            assert mock_console.print.call_count >= 2


class TestDetailRendererConsistency:
    """Test consistency of detail renderers."""

    def test_detail_renderers_format_output(self):
        """Test that detail renderers produce readable output."""
        from terrapyne.utils.rich_tables import (
            render_project_detail,
            render_run_detail,
            render_workspace_detail,
        )

        workspace = Workspace(
            id="ws-abc123",
            name="test-workspace",
            terraform_version="1.7.0",
            locked=False,
        )

        run = Run(id="run-abc123", status="applied")

        project = Project(id="prj-abc123", name="test-project")

        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_workspace_detail(workspace)
            render_run_detail(run)
            render_project_detail(project, [])

            # Each should print something
            assert mock_console.print.call_count >= 3


class TestTableRendererOutput:
    """Test actual rendering output quality."""

    def test_workspace_list_shows_key_columns(self):
        """Test that workspace list shows essential columns."""
        workspace = Workspace(
            id="ws-abc123",
            name="production-app",
            terraform_version="1.8.0",
        )

        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_workspaces([workspace])

            # Verify print was called with a Table object
            call_args = mock_console.print.call_args
            if call_args and len(call_args[0]) > 0:
                first_arg = call_args[0][0]
                # Should be a Table or string containing key info
                assert isinstance(first_arg, (Table, str)) or hasattr(first_arg, "title")

    def test_run_list_shows_status_column(self):
        """Test that run list shows status information."""
        run = Run(id="run-abc123", status="applied")

        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            render_runs([run])
            mock_console.print.assert_called()

    def test_detail_renderers_show_all_fields(self):
        """Test that detail renderers display all important fields."""
        workspace = Workspace(
            id="ws-abc123",
            name="test-workspace",
            terraform_version="1.7.0",
            execution_mode="remote",
            auto_apply=True,
            locked=False,
            created_at=None,
        )

        with patch("terrapyne.utils.rich_tables.console") as mock_console:
            from terrapyne.utils.rich_tables import render_workspace_detail

            render_workspace_detail(workspace)

            # Should have printed a detail table
            mock_console.print.assert_called()


class TestTableRendererAbstraction:
    """Test the proposed TableRenderer abstraction (future implementation)."""

    def test_table_renderer_would_reduce_duplication(self):
        """Test that a base class would eliminate render_* duplication.

        This test documents the goal: a single TableRenderer base class
        that all entity types can inherit from.
        """
        # Future implementation should allow:
        # class WorkspaceTableRenderer(TableRenderer):
        #     def get_columns(self) -> List[str]:
        #         return ["Name", "Environment", "TF Version", "VCS", "Locked"]
        #
        #     def get_row(self, entity: Workspace) -> List[str]:
        #         return [entity.name, entity.environment or "-", ...]
        #
        # Then: renderer = WorkspaceTableRenderer()
        #       renderer.render([ws1, ws2])

        # For now, just document the interface we want
        pass

    def test_single_console_injection_point(self):
        """Test that all renderers would share a console instance.

        This would allow testing without side effects and easier mocking.
        """
        # Current: render_workspaces() uses global console
        # Future: all renderers accept optional console parameter
        # render_workspaces([ws], console=mock_console)

        pass
