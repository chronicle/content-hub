from __future__ import annotations
class Office365CloudAppSecurityError(Exception):
    """
    General exception for Office 365 Cloud App Security
    """

    pass


class Office365CloudAppSecurityAlreadyExistingError(Office365CloudAppSecurityError):
    """
    Exception for already existing case
    """

    pass


class Office365CloudAppSecurityNotFoundError(Office365CloudAppSecurityError):
    """
    Exception for not found case
    """

    pass


class Office365CloudAppSecurityLastItemError(Office365CloudAppSecurityError):
    """
    Exception for last item
    """

    pass
