from __future__ import annotations
class ExtrahopException(Exception):
    """General exception for Extrahop"""


class InvalidParameterError(Exception):
    """Invalid parameter error"""


class InvalidDetectionIDError(Exception):
    """Invalid detection ID error"""


class InvalidCredentialsError(Exception):
    """Invalid credentials error"""
