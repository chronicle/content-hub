from __future__ import annotations
class BaseAutomoxException(Exception):
    """Base Automox Exception"""

    pass


class AutomoxManagerException(BaseAutomoxException):
    """Base exception for AutomoxManager."""

    pass


class AutomoxFilterException(BaseAutomoxException):
    """Base exception for AutomoxFilter."""

    pass


class AutomoxAPIError(AutomoxManagerException):
    """Invalid credentials exception."""

    pass
