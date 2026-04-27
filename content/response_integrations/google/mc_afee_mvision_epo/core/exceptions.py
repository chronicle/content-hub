from __future__ import annotations
class McAfeeMvisionEPOException(Exception):
    """
    Common McAfee Mvision EPO Exception
    """

    pass


class UnableToGetTokenException(McAfeeMvisionEPOException):
    pass


class GroupNotFoundException(McAfeeMvisionEPOException):
    pass


class TagNotFoundException(McAfeeMvisionEPOException):
    pass


class EndpointNotFoundException(McAfeeMvisionEPOException):
    pass
