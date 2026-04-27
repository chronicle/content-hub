from __future__ import annotations
class AnomaliException(Exception):
    """
    General Exception for Anomali manager
    """

    pass


class AnomaliManagerException(AnomaliException):
    pass


class AnomaliUnauthorizedException(AnomaliManagerException):
    pass


class AnomaliBadRequestException(AnomaliManagerException):
    pass


class AnomaliPermissionException(AnomaliManagerException):
    pass


class AnomaliNotFoundException(AnomaliManagerException):
    pass
