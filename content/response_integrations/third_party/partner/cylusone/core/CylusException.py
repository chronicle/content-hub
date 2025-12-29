"""Custom exceptions for Cylus integration."""


class CylusException(Exception):
    """Base exception for Cylus integration."""

    def __init__(self, message="An error occurred in Cylus integration"):
        self.message = message
        super().__init__(self.message)


class CylusConnectionException(CylusException):
    """Exception raised when connection to Cylus fails."""

    def __init__(self, message="Failed to connect to Cylus platform"):
        super().__init__(message)


class CylusAuthenticationException(CylusException):
    """Exception raised when authentication fails."""

    def __init__(self, message="Authentication failed with Cylus platform"):
        super().__init__(message)


class CylusAPIException(CylusException):
    """Exception raised when API request fails."""

    def __init__(self, message="API request failed", status_code=None):
        self.status_code = status_code
        if status_code:
            message = f"{message} (Status Code: {status_code})"
        super().__init__(message)
