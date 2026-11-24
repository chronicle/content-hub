from __future__ import annotations


class ZscalerException(Exception):
    """Base exception for all Zscaler integration errors."""


class ZscalerManagerError(ZscalerException):
    """General Exception for Zscaler manager."""


class ZscalerMissingError(ZscalerException):
    """General Exception for Zscaler missing entity."""


class ZscalerAuthError(ZscalerException):
    """Exception for Zscaler authentication failures."""
