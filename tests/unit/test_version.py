"""Tests for version consistency."""


class TestVersion:
    """Test version configuration."""

    def test_version_is_0_1_0(self):
        """Verify __version__ is aligned to 0.1.0."""
        import terrapyne
        
        assert terrapyne.__version__ == "0.1.0", f"Expected version 0.1.0, got {terrapyne.__version__}"
