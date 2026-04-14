"""Tests for run log streaming functionality."""

from terrapyne.cli.run_cmd import _print_log_delta


class TestPrintLogDelta:
    """Test _print_log_delta helper function."""

    def test_empty_log_returns_zero(self):
        """When log is empty, position remains 0."""
        result = _print_log_delta("", 0)
        assert result == 0

    def test_first_read_returns_full_length(self):
        """First read from position 0 returns full log length."""
        log = "Line 1\nLine 2\nLine 3\n"
        result = _print_log_delta(log, 0)
        assert result == len(log)

    def test_delta_from_middle(self):
        """Reading from middle position returns only new content length."""
        log = "Line 1\nLine 2\nLine 3\n"
        first_read = len("Line 1\n")
        result = _print_log_delta(log, first_read)
        assert result == len(log)

    def test_no_new_content(self):
        """When position equals log length, no new content."""
        log = "Line 1\nLine 2\n"
        result = _print_log_delta(log, len(log))
        assert result == len(log)

    def test_position_tracks_correctly(self, capsys):
        """Position parameter correctly tracks where we left off."""
        log = "ABC\nDEF\n"

        # First read: position 0, returns position len(log)=8
        pos = _print_log_delta(log, 0)
        assert pos == 8
        captured = capsys.readouterr()
        assert captured.out == "ABC\nDEF\n"

        # Second read: position 8 (at end), no new content
        pos = _print_log_delta(log, pos)
        assert pos == 8
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_incremental_reading(self, capsys):
        """Simulate streaming incremental log updates."""
        # Simulate log growing over time
        log1 = "Planning...\n"
        log2 = "Planning...\nFetching modules\n"
        log3 = "Planning...\nFetching modules\nDone\n"

        # First poll: read entire log1
        pos = _print_log_delta(log1, 0)
        captured = capsys.readouterr()
        assert "Planning" in captured.out
        # pos should be len(log1) = 12

        # Second poll: log has grown, read from pos to new length
        # log2 has new content "Fetching modules\n"
        pos = _print_log_delta(log2, pos)
        captured = capsys.readouterr()
        assert "Fetching modules" in captured.out
        assert "Planning" not in captured.out  # Don't repeat first line
        # pos should be len(log2) = 28

        # Third poll: log has grown more
        pos = _print_log_delta(log3, pos)
        captured = capsys.readouterr()
        assert "Done" in captured.out

    def test_position_at_log_boundary(self):
        """Position exactly at log length returns same length."""
        log = "Test line\n"
        result = _print_log_delta(log, len(log))
        assert result == len(log)

    def test_multiline_delta_extraction(self, capsys):
        """Delta extraction preserves multi-line content."""
        log = "Header\nLine A\nLine B\nLine C\n"
        header_len = len("Header\n")

        _print_log_delta(log, header_len)
        captured = capsys.readouterr()
        assert captured.out == "Line A\nLine B\nLine C\n"

    def test_empty_delta_no_output(self, capsys):
        """When delta is empty, no output is printed."""
        log = "No change\n"
        _print_log_delta(log, len(log))
        captured = capsys.readouterr()
        # flush=True but no content written
        assert captured.out == ""
