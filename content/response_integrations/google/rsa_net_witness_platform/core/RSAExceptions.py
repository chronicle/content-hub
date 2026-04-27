from __future__ import annotations
class RSAError(Exception):
    pass


class RSAEmptyAPIConfigurationException(RSAError):
    pass


class EndpointServerNotFoundException(RSAError):
    pass


class IncorrectHashTypeException(RSAError):
    pass


class IsolationFailException(RSAError):
    pass


class UpdateFailException(RSAError):
    pass


class RSAAuthenticationException(RSAError):
    pass
