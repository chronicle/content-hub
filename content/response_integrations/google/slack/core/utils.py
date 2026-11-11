from __future__ import annotations
import os as os_system

def get_secops_mode() -> str | None:
    """Returns the SECOPS_MODE environment variable.
    """
    return os_system.environ.get('SECOPS_MODE') or os_system.environ.get('SEC_OPS_MODE')
