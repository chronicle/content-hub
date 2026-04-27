from __future__ import annotations
class McAfeeMvisionEPOV2Exception(Exception):
    """
    Common McAfee Mvision EPO Exception
    """

    pass


class UnableToGetTokenException(McAfeeMvisionEPOV2Exception):
    pass


class TagNotFoundException(McAfeeMvisionEPOV2Exception):
    pass


class DeviceNotFoundException(McAfeeMvisionEPOV2Exception):
    pass
