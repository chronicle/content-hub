from __future__ import annotations


class GreyNoiseException(Exception):
    """
    General Exception for GreyNoise integration
    """

    pass


class InvalidIntegerException(GreyNoiseException):
    """
    Exception for invalid integer parameters
    """

    pass


class ExpiredAPIKeyException(GreyNoiseException):
    """
    Exception for expired API keys
    """

    pass


class InvalidGranularityException(GreyNoiseException):
    """
    Exception for invalid granularity parameter
    """

    pass
