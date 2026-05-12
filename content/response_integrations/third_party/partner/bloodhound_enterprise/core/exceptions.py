from __future__ import annotations


class BloodHoundException(Exception):
    """General Exception for BloodHound manager."""


class BloodHoundValidationException(BloodHoundException):
    """Validation Exception for BloodHound."""


class BloodHoundBadRequestException(BloodHoundException):
    """Bad Request Exception for BloodHound."""


class BloodHoundNotFoundException(BloodHoundException):
    """Not Found Exception for BloodHound."""


class BloodHoundUnauthorizedException(BloodHoundException):
    """Unauthorized Exception for BloodHound."""


class BloodHoundForbiddenException(BloodHoundException):
    """Forbidden Exception for BloodHound."""


class BloodHoundRateLimitException(BloodHoundException):
    """Rate Limit Exception for BloodHound."""
