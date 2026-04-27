from __future__ import annotations
class VectraException(Exception):
    """
    Common Vectra Exception
    """

    pass


class ItemNotFoundException(VectraException):
    """
    Exception if item not found in Vectra
    """

    pass


class TagsUpdateFailException(VectraException):
    """
    Exception if tags were not added in Vectra
    """

    pass


class UnknownTagsUpdateException(VectraException):
    """
    Exception if tags failed to update in Vectra
    """

    pass
