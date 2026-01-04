"""
Custom exceptions for Jamf integration
"""


class JamfError(Exception):
    """
    General Exception for Jamf manager
    """

    pass


class JamfManagerError(Exception):
    """Base exception for Jamf Manager errors"""

    pass


class JamfAuthenticationError(JamfManagerError):
    """Raised when authentication with Jamf Pro fails"""

    pass


class JamfConnectionError(JamfManagerError):
    """Raised when connection to Jamf Pro fails"""

    pass


class JamfAPIError(JamfManagerError):
    """Raised when Jamf Pro API returns an error"""

    pass


class JamfTimeoutError(JamfManagerError):
    """Raised when an operation times out"""

    pass


class JamfInvalidParameterError(JamfManagerError):
    """Raised when invalid parameters are provided"""

    pass
