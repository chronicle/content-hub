from __future__ import annotations
class AnomaliException(Exception):
    """
    General Exception for Anomali manager
    """

    pass


class AnomaliManagerException(AnomaliException):
    pass


class AnomaliThreatStreamBadRequestException(AnomaliManagerException):
    pass


class AnomaliThreatStreamInvalidCredentialsException(AnomaliManagerException):
    pass


class AnomaliThreatStreamNotFoundException(AnomaliManagerException):
    pass
