from __future__ import annotations

class AkamaiManagerError(Exception):
    """General Exception for Akamai manager."""


class AuthenticationError(Exception):
    """Exception in case of authentication failure."""


class AlertNotFoundError(Exception):
    """Exception in case of alert not found."""


class RequestTakeDownError(Exception):
    """Exception in case of request takedown failure."""
