from __future__ import annotations
class DevoManagerError(Exception):
    """
    General Exception for Devo Manager Error
    """

    pass


class DevoManagerErrorValidationException(Exception):
    """
    Validation Exception for Devo Manager Error
    """

    pass


class DevoManagerErrorUnauthorizedException(Exception):
    """
    Unauthorized Exception for Devo Manager Error
    """

    pass


class DevoManagerErrorBadQueryException(Exception):
    """
    Bad Query Exception for Devo Manager Error
    """

    pass
