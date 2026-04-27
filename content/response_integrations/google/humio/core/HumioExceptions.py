from __future__ import annotations
class HumioException(Exception):
    """
    General exception for Humio
    """

    pass


class HumioInvalidTimeExceptionException(HumioException):
    """
    Exception for invalid time
    """

    pass
