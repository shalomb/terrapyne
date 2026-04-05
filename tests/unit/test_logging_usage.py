"""Test that logging.py is properly integrated and not dead code."""

import pytest


def test_logging_module_is_importable():
    """logging.py should be importable and provides expected exports."""
    # GIVEN: the terrapyne.logging module
    import terrapyne.logging
    
    # WHEN: we check for expected exports
    # THEN: they should all be available
    assert hasattr(terrapyne.logging, 'cli_log_config')
    assert hasattr(terrapyne.logging, 'PrettyExceptionFormatter')
    assert hasattr(terrapyne.logging, 'style')
    assert hasattr(terrapyne.logging, '_interpret_color')


def test_cli_log_config_is_context_manager():
    """cli_log_config should work as a context manager."""
    from terrapyne.logging import cli_log_config
    import logging
    
    # GIVEN: cli_log_config from terrapyne.logging
    # WHEN: using it as a context manager
    with cli_log_config(verbose=0):
        logging.debug("test message")
    # THEN: no exceptions should be raised
    # Context manager works properly


def test_pretty_exception_formatter_is_usable():
    """PrettyExceptionFormatter should be instantiable and usable."""
    from terrapyne.logging import PrettyExceptionFormatter
    import sys
    
    # GIVEN: PrettyExceptionFormatter class
    # WHEN: creating an instance and using it
    formatter = PrettyExceptionFormatter(color=False)
    
    try:
        raise ValueError("test error")
    except Exception:
        exc_info = sys.exc_info()
    
    # THEN: it should format exceptions
    output = formatter.format_exception(exc_info)
    assert "ValueError" in output or "test error" in output
