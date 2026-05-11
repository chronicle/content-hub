from __future__ import annotations
class BloodHoundException(Exception):
    """
    General Exception for BloodHound manager
    """

    pass


class BloodHoundValidationException(Exception):
    """
    Validation Exception for BloodHound
    """

    pass


class BloodHoundBadRequestException(Exception):
    """
    Bad Request Exception for BloodHound
    """

    pass


class BloodHoundNotFoundException(Exception):
    """
    Not Found Exception for BloodHound
    """

    pass


class BloodHoundUnauthorizedException(Exception):
    """
    Unauthorized Exception for BloodHound
    """

    pass


class BloodHoundForbiddenException(Exception):
    """
    Forbidden Exception for BloodHound
    """

    pass


class BloodHoundRateLimitException(Exception):
    """
    Rate Limit Exception for BloodHound
    """

    pass