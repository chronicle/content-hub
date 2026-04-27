from __future__ import annotations
class CaseFederationError(Exception):
    """Base Exception for custom exceptions of the integration."""


class MissingParameterError(CaseFederationError):
    """A parameter is missing."""
