from __future__ import annotations
class TaniumManagerException(Exception):
    pass


class TaniumBadRequestException(TaniumManagerException):
    pass


class TaniumNotFoundException(TaniumManagerException):
    pass


class TaniumResponseSchemaError(TaniumManagerException):
    """Raised when Tanium response data fails schema validation."""


class InvalidTimeException(TaniumManagerException):
    """
    Exception for invalid time
    """

    pass


class InvalidJsonException(TaniumManagerException):
    """
    Exception for invalid JSON string
    """


class FileExistsException(TaniumManagerException):
    pass
