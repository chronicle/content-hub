from __future__ import annotations
class ArmisException(Exception):
    """
    General Exception for Armis manager
    """

    pass


class ArmisValidationException(Exception):
    """
    Validation Exception for Armis
    """

    pass


class ArmisBadRequestException(Exception):
    """
    Bad Request Exception for Armis
    """

    pass


class ArmisNotFoundException(Exception):
    """
    Not Found Exception for Armis
    """

    pass
