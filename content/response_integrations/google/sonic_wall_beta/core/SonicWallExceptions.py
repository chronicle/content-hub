from __future__ import annotations
class SonicWallException(Exception):
    """
    Common SonicWall Exception
    """

    pass


class UnauthorizedException(Exception):
    """
    Exception if user not authorized in SonicWall
    """

    pass


class NotFoundException(SonicWallException):
    """
    Exception if no matching command found in SonicWall
    """

    pass


class UnableToAddException(SonicWallException):
    """
    Exception if unable to add to group in SonicWall
    """

    pass
