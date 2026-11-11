from __future__ import annotations
class NGFWException(Exception):
    """Exception raised for general Palo Alto NGFW errors."""


class GroupNotExistsException(Exception):
    """Exception raised when a specified group does not exist on the Palo Alto NGFW."""


class AlreadyExistsException(Exception):
    """Exception raised when an entity already exists on the Palo Alto NGFW."""


class CategoryNotExistsException(Exception):
    """
    Exception raised when a specified category does not exist on the Palo Alto NGFW.
    """
