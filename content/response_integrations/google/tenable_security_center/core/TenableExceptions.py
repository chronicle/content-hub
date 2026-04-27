from __future__ import annotations
class TenableException(Exception):
    """
    Common Tenable Exception
    """


class AssetNotFoundException(TenableException):
    """
    Asset Not Found Exception
    """


class TenableSecurityCenterException(TenableException):
    """
    Common Tenable Security Center Exception
    """
