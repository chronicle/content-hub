from __future__ import annotations
class CheckpointException(Exception):
    """
    CheckPointFirewall Exception
    """

    pass


class CheckpointManagerError(CheckpointException):
    """
    CheckPointFirewall Manager Exception
    """

    pass


class CheckpointManagerBadRequestException(CheckpointManagerError):
    """
    CheckPointFirewall Logs request 400 status code Exception
    """

    pass


class CheckpointManagerNotFoundException(CheckpointManagerError):
    """
    CheckPointFirewall Logs request 404 status code Exception
    """

    pass


class InvalidGroupException(CheckpointManagerError):
    """
    Invalid group exception
    """

    pass
