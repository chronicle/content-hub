from __future__ import annotations
class McAfeeMvisionEDRException(Exception):
    """
    Common McAfee Mvision EDR Exception
    """

    pass


class CaseNotFoundException(McAfeeMvisionEDRException):
    """
    Exception if case not found in McAfee Mvision EDR
    """

    pass


class TaskFailedException(McAfeeMvisionEDRException):
    """
    Exception if task failed in McAfee Mvision EDR
    """

    pass


class UnknownTaskStatusException(McAfeeMvisionEDRException):
    """
    Exception if Task status unknown for Siemplify
    """

    pass
