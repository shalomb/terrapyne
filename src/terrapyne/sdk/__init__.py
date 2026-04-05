"""Deprecated SDK namespace — use terrapyne directly.

This module is deprecated and will be removed in a future version.
Please import from terrapyne directly instead:

    # Old (deprecated)
    from terrapyne.sdk import TFCClient

    # New (recommended)
    from terrapyne import TFCClient
"""

import warnings

from terrapyne import *  # noqa: F401, F403

warnings.warn(
    "terrapyne.sdk is deprecated, import from terrapyne directly",
    DeprecationWarning,
    stacklevel=2,
)
