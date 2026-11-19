from __future__ import annotations
class WebRiskException(Exception):
    """General exception for Web Risk."""


class WebRiskValidationException(WebRiskException):
    """General exception for validation errors."""


class WebRiskManagerException(WebRiskException):
    """General exception for Web Risk API Manager."""


class WebRiskAuthException(WebRiskException):
    """Exception in case of authentication error."""


class WebRiskInvalidJsonException(WebRiskException):
    """Exception in case of invalid JSON string provided."""
