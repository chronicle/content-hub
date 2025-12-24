from __future__ import annotations


class PulsediveException(Exception):
    pass


class ForceRaiseException(PulsediveException):
    pass


class UnauthorizedException(ForceRaiseException):
    pass


class PulsediveNotFoundException(PulsediveException):
    pass


class PulsediveLimitReachedException(PulsediveException):
    pass


class PulsediveBadRequest(PulsediveException):
    pass


class MissingEntitiesException(PulsediveException):
    pass
