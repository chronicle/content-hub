from __future__ import annotations
class GSuiteManagerError(Exception):
    """General Exception for GSuite manager."""


class GSuiteValidationException(Exception):
    """Validate Exception for GSuite."""


class GSuiteParameterValidationError(Exception):
    """Validate Parameter Exception for GSuite."""


class GSuiteEntityExistsException(Exception):
    """Entity exists exception for GSuite."""


class GSuiteNotFoundException(Exception):
    """Not Found exception for GSuite."""


class GoogleCloudAuthenticationError(Exception):
    """General Exception for Google Cloud Authentication errors."""


class InvalidJSONFormatException(Exception):
    """Invalid JSON format error."""


class GSuiteAuthError(Exception):
    """Exception for general errors in GSuiteAuthManager."""
