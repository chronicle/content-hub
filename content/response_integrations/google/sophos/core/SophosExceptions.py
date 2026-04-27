from __future__ import annotations
class SophosManagerError(Exception):
    """General Exception for Sophos manager."""


class BadRequestError(SophosManagerError):
    """Exception in case of bad request"""


class HashAlreadyOnBlocklist(SophosManagerError):
    """Exception in case of hash already on blocklist."""


class NoAuthParamsProvided(Exception):
    """Exception in case no authentication parameters provided."""
