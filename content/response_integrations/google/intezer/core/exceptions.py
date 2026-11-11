from __future__ import annotations
class IntezerManagerError(Exception):
    """General Exception for Intezer manager"""


class IntezerAPILimitError(IntezerManagerError):
    """API Limit Exception for Intezer manager"""


class IntezerBadRequestError(IntezerManagerError):
    """Exception for Bad Request"""


class IntezerUserInputError(IntezerManagerError):
    """When requested entity is not found in Intezer"""


class IntezerNotFoundError(IntezerUserInputError):
    """When requested entity is not found in Intezer"""


class IntezerInvalidFormat(IntezerManagerError):
    """When requested entity is not valid in Intezer"""


class IntezerTimeoutException(IntezerManagerError):
    """When there is timeout in Intezer"""


class IntezerUnexpectedStatusException(IntezerManagerError):
    """When there is an unexpected analysis status in Intezer"""
