from __future__ import annotations
class PubSubException(Exception):
    """General exception for Google Cloud API."""


class PubSubAuthException(PubSubException):
    """Exception in case of authentication error."""


class PubSubInvalidJsonException(PubSubException):
    """Exception in case of invalid JSON string provided."""


class PubSubCertificateException(PubSubException):
    """Exception in case of certificate error."""


class PubSubHTTPException(PubSubException):
    """Exception in case of HTTP error."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code
