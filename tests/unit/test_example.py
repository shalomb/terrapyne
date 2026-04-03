import pytest


@pytest.mark.fast
@pytest.mark.unit
def test_example() -> None:
    """Example unit test."""
    assert 1 + 1 == 2
