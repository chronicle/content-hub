from __future__ import annotations
class MandiantManagerException(Exception):
    """General exception for Mandiant ASM manager"""


class ProjectNotFoundError(Exception):
    """Exception in case of specified project is not found"""


class InvalidParametersException(Exception):
    """Exception in case of  integration parameters not provided"""


class InvalidUnicodeKeyError(Exception):
    """Exception raised when a key contains Unicode characters."""
