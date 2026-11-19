from __future__ import annotations
class ZohoDeskException(Exception):
    """General exception for Zoho Desk"""


class ZohoDeskNotFound(ZohoDeskException):
    """Not Found Error."""


class MissingRefreshTokenError(ZohoDeskException):
    """No Refresh Token Found"""
